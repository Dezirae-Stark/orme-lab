#!/usr/bin/env python3
"""Reproducible per-element PGM EPW run driver (Ir, Pt, Os, ...).

Element-generic: pass --element (default Ir) + --n-semicore (default: Ir=4, else
computed from the pseudo's Z_valence). The deck prefix is the element symbol,
lowercased. Modes, each a pure testable step the persistent supervisor composes:

  --deck-only  write scf/nscf/ph/epw.in for a spin state, exit 0 (never runs a binary).
  --epw-deck   regenerate ONLY epw.in with E_F-referenced windows (after nscf).
  --parse      read <workdir>/<sym>.a2f.<smear>.<temp>, print JSON lambda/omega/Tc.
  --gate       build a ConvergenceReport from supplied numbers; exit 0 iff trustworthy.

Heavy orchestration (mpirun, -npool, checkpointing, resource caps) lives in the
supervisor; this module stays deterministic and unit-testable without QE.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orme_lab.epw import qe_input                       # noqa: E402
from orme_lab.epw.allen_dynes import allen_dynes_tc     # noqa: E402
from orme_lab.epw.convergence import ConvergenceReport  # noqa: E402
from orme_lab.epw.parse import parse_a2f                # noqa: E402
from orme_lab.epw.runs import ir, pgm                   # noqa: E402

_DECKS = {"scf": qe_input.scf_input, "nscf": qe_input.nscf_input,
          "ph": qe_input.ph_input, "q2r": qe_input.q2r_input,
          "epw": qe_input.epw_input}


def _resolve(element: str, spin: str, pseudo_dir: str, upf: str,
             n_semicore: int | None):
    """Build the approximant and its EPW config. ``n_semicore`` is PER-ATOM (Ir=4,
    else computed from the pseudo); nbndsub and exclude_bands scale with n_atoms
    inside pgm_config, so hcp (2-atom) cells get 12 / 1:(2*per-atom) automatically."""
    approx = pgm.pgm_approximant(element, spin)
    if n_semicore is None:
        n_semicore = ir.IR_SEMICORE_BANDS if element == "Ir" \
            else pgm.semicore_for_pseudo(element, pseudo_dir, upf)
    cfg = pgm.pgm_config(element, pseudo_dir, upf,
                         n_semicore_per_atom=n_semicore, n_atoms=approx.n_atoms)
    return approx, element.lower(), cfg


def write_decks(spin: str, workdir: str, pseudo_dir: str, upf: str,
                fermi_ev: float | None = None, element: str = "Ir",
                n_semicore: int | None = None) -> dict[str, str]:
    """Write the four QE/EPW decks; return {name: path}."""
    os.makedirs(workdir, exist_ok=True)
    approx, prefix, cfg = _resolve(element, spin, pseudo_dir, upf, n_semicore)
    paths: dict[str, str] = {}
    for name, writer in _DECKS.items():
        path = os.path.join(workdir, f"{name}.in")
        kw = {"fermi_ev": fermi_ev} if name == "epw" else {}
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(writer(approx, cfg, prefix, **kw))
        paths[name] = path
    return paths


def write_epw_deck(spin: str, workdir: str, pseudo_dir: str, upf: str,
                   fermi_ev: float, element: str = "Ir",
                   n_semicore: int | None = None) -> str:
    """Regenerate ONLY epw.in with E_F-referenced windows (called after nscf)."""
    os.makedirs(workdir, exist_ok=True)
    approx, prefix, cfg = _resolve(element, spin, pseudo_dir, upf, n_semicore)
    path = os.path.join(workdir, "epw.in")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(qe_input.epw_input(approx, cfg, prefix, fermi_ev=fermi_ev))
    return path


def _find_a2f(workdir: str, element: str = "Ir") -> str:
    """EPW names the a2f <sym>.a2f.<smear>.<temp> (not bare <sym>.a2f); match the
    standard (non-transport) file -- the glob excludes <sym>.a2f_tr.*."""
    prefix = element.lower()
    hits = sorted(glob.glob(os.path.join(workdir, f"{prefix}.a2f.*")))
    return hits[0] if hits else os.path.join(workdir, f"{prefix}.a2f")


def parse_min_phonon_freq(workdir: str, ph_out: str = "ph.out") -> float | None:
    """Minimum phonon frequency (cm-1) for the dynamical-stability gate, EXCLUDING
    the 3 acoustic modes at Gamma (they are 0 by symmetry and carry a +-few cm-1
    acoustic-sum-rule artifact in the raw ph.out). Works for any cell: at Gamma it
    drops up to 3 near-zero (|f|<30) modes as acoustic and keeps everything else --
    so an hcp cell's Gamma OPTICAL modes (real stability indicators) are retained.
    Per-mode 'freq' lines are matched by their [THz]=[cm-1] form (the grouped
    summary lines carry only [cm-1] and are skipped to avoid double counting)."""
    import re
    path = os.path.join(workdir, ph_out)
    if not os.path.exists(path):
        return None
    q_re = re.compile(r"q\s*=\s*\(\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)")
    f_re = re.compile(r"\[THz\].*=\s*(-?\d+\.\d+)\s*\[cm-1\]")
    gamma: list[float] = []
    other: list[float] = []
    at_gamma = False
    for line in open(path, encoding="utf-8"):
        qm = q_re.search(line)
        if qm:
            at_gamma = all(abs(float(qm.group(i))) < 1e-6 for i in (1, 2, 3))
            continue
        fm = f_re.search(line)
        if fm:
            (gamma if at_gamma else other).append(float(fm.group(1)))
    gamma.sort()
    dropped = 0
    for v in gamma:                       # drop up to 3 near-zero acoustic modes
        if dropped < 3 and abs(v) < 30.0:
            dropped += 1
        else:
            other.append(v)
    return min(other) if other else None


def parse_lambda(workdir: str, smearing_column: int = 5,
                 element: str = "Ir") -> dict[str, float]:
    with open(_find_a2f(workdir, element), encoding="utf-8") as fh:
        ef = parse_a2f(fh.read(), column=smearing_column)
    lam, wlog, w2 = ef.moments()
    tc = allen_dynes_tc(lam, wlog, w2, mu_star=0.10)
    return {"lambda": lam, "omega_log_k": wlog, "omega_2_k": w2, "tc_kelvin": tc}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spin", choices=("none", "low", "high"))
    p.add_argument("--element", default="Ir")
    p.add_argument("--n-semicore", type=int, default=None)
    p.add_argument("--workdir")
    p.add_argument("--pseudo-dir", default="")
    p.add_argument("--upf", default="Ir.upf")
    p.add_argument("--deck-only", action="store_true")
    p.add_argument("--epw-deck", action="store_true")
    p.add_argument("--parse", action="store_true")
    p.add_argument("--min-freq-mode", action="store_true",
                   help="print min phonon freq (cm-1) excluding acoustic-Gamma modes")
    p.add_argument("--gate", action="store_true")
    p.add_argument("--fermi", type=float, help="E_F (eV) to reference EPW dis windows")
    # gate inputs
    p.add_argument("--wannier-dev", type=float)
    p.add_argument("--lambda-delta", type=float)
    p.add_argument("--min-freq", type=float)
    p.add_argument("--lambda", dest="lam", type=float)
    p.add_argument("--tc", type=float)
    args = p.parse_args(argv)

    if args.deck_only:
        paths = write_decks(args.spin, args.workdir, args.pseudo_dir, args.upf,
                            args.fermi, args.element, args.n_semicore)
        print(json.dumps({k: os.path.basename(v) for k, v in paths.items()}))
        return 0
    if args.epw_deck:
        if args.fermi is None:
            p.error("--epw-deck requires --fermi")
        path = write_epw_deck(args.spin, args.workdir, args.pseudo_dir, args.upf,
                              args.fermi, args.element, args.n_semicore)
        print(json.dumps({"epw": os.path.basename(path)}))
        return 0
    if args.parse:
        print(json.dumps(parse_lambda(args.workdir, element=args.element)))
        return 0
    if args.min_freq_mode:
        v = parse_min_phonon_freq(args.workdir)
        print("NA" if v is None else f"{v:.4f}")
        return 0
    if args.gate:
        rep = ConvergenceReport(
            wannier_band_max_dev_mev=args.wannier_dev,
            lambda_grid_delta_frac=args.lambda_delta,
            min_phonon_freq_cm=args.min_freq,
            lambda_value=args.lam,
            tc_kelvin=args.tc,
        )
        print(json.dumps({"gates": rep.gates(), "trustworthy": rep.trustworthy(),
                          "failing": rep.failing_gates()}))
        return 0 if rep.trustworthy() else 1
    p.error("one of --deck-only / --epw-deck / --parse / --gate is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
