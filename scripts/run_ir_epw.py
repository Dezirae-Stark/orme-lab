#!/usr/bin/env python3
"""Reproducible Ir EPW run driver.

Three modes, each a pure, testable step the persistent supervisor composes:

  --deck-only  write scf.in / nscf.in / ph.in / epw.in for a spin state, exit 0
               (NEVER invokes a binary -- this is what the unit test exercises).
  --parse      read <workdir>/ir.a2f, print JSON {lambda, omega_log_k, omega_2_k, tc_kelvin}.
  --gate       build a ConvergenceReport from supplied numbers, print gates JSON,
               exit 0 iff trustworthy() (so bash can `if python3 ... --gate`).

The heavy orchestration (mpirun -np N, -npool N, per-stage checkpointing, resource
safeguards) lives in the supervisor, NOT here -- this module stays deterministic and
side-effect-light so it is unit-testable without QE.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orme_lab.epw import qe_input                       # noqa: E402
from orme_lab.epw.allen_dynes import allen_dynes_tc     # noqa: E402
from orme_lab.epw.convergence import ConvergenceReport  # noqa: E402
from orme_lab.epw.parse import parse_a2f                # noqa: E402
from orme_lab.epw.runs import ir                        # noqa: E402

PREFIX = "ir"
_DECKS = {"scf": qe_input.scf_input, "nscf": qe_input.nscf_input,
          "ph": qe_input.ph_input, "epw": qe_input.epw_input}


def write_decks(spin: str, workdir: str, pseudo_dir: str, upf: str,
                fermi_ev: float | None = None) -> dict[str, str]:
    """Write the four QE/EPW decks; return {name: path}. ``fermi_ev`` shifts the
    EPW disentanglement windows to bracket E_F (see qe_input.epw_input)."""
    os.makedirs(workdir, exist_ok=True)
    approx = ir.ir_approximant(spin)
    cfg = ir.ir_config(pseudo_dir=pseudo_dir, upf=upf)
    paths: dict[str, str] = {}
    for name, writer in _DECKS.items():
        path = os.path.join(workdir, f"{name}.in")
        kw = {"fermi_ev": fermi_ev} if name == "epw" else {}
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(writer(approx, cfg, PREFIX, **kw))
        paths[name] = path
    return paths


def write_epw_deck(spin: str, workdir: str, pseudo_dir: str, upf: str,
                   fermi_ev: float) -> str:
    """Regenerate ONLY epw.in with E_F-referenced windows (called after nscf)."""
    os.makedirs(workdir, exist_ok=True)
    approx = ir.ir_approximant(spin)
    cfg = ir.ir_config(pseudo_dir=pseudo_dir, upf=upf)
    path = os.path.join(workdir, "epw.in")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(qe_input.epw_input(approx, cfg, PREFIX, fermi_ev=fermi_ev))
    return path


def parse_lambda(workdir: str, smearing_column: int = 5) -> dict[str, float]:
    a2f_path = os.path.join(workdir, f"{PREFIX}.a2f")
    with open(a2f_path, encoding="utf-8") as fh:
        ef = parse_a2f(fh.read(), column=smearing_column)
    lam, wlog, w2 = ef.moments()
    tc = allen_dynes_tc(lam, wlog, w2, mu_star=0.10)
    return {"lambda": lam, "omega_log_k": wlog, "omega_2_k": w2, "tc_kelvin": tc}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--spin", choices=("none", "low", "high"))
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
        paths = write_decks(args.spin, args.workdir, args.pseudo_dir, args.upf, args.fermi)
        print(json.dumps({k: os.path.basename(v) for k, v in paths.items()}))
        return 0
    if args.epw_deck:
        if args.fermi is None:
            p.error("--epw-deck requires --fermi")
        path = write_epw_deck(args.spin, args.workdir, args.pseudo_dir, args.upf, args.fermi)
        print(json.dumps({"epw": os.path.basename(path)}))
        return 0
    if args.parse:
        print(json.dumps(parse_lambda(args.workdir)))
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
    p.error("one of --deck-only / --parse / --gate is required")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
