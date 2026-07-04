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
          "ph": qe_input.ph_input, "epw": qe_input.epw_input}


def _resolve(element: str, pseudo_dir: str, upf: str, n_semicore: int | None):
    """Return (prefix, approximant-builder-args, cfg) for an element. n_semicore
    defaults to Ir's 4 (no file read) or is computed from the pseudo for others."""
    if n_semicore is None:
        n_semicore = ir.IR_SEMICORE_BANDS if element == "Ir" \
            else pgm.semicore_for_pseudo(element, pseudo_dir, upf)
    cfg = pgm.pgm_config(element, pseudo_dir, upf, n_semicore=n_semicore)
    return element.lower(), cfg


def write_decks(spin: str, workdir: str, pseudo_dir: str, upf: str,
                fermi_ev: float | None = None, element: str = "Ir",
                n_semicore: int | None = None) -> dict[str, str]:
    """Write the four QE/EPW decks; return {name: path}."""
    os.makedirs(workdir, exist_ok=True)
    prefix, cfg = _resolve(element, pseudo_dir, upf, n_semicore)
    approx = pgm.pgm_approximant(element, spin)
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
    prefix, cfg = _resolve(element, pseudo_dir, upf, n_semicore)
    approx = pgm.pgm_approximant(element, spin)
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
