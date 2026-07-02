#!/usr/bin/env python3
"""Mock screen for PLATINUM plus the full six-element PGM suite.

This example does two things:

1. A focused platinum geometry sweep (Pt is a strong candidate: d9, one d-shell
   vacancy, high spin-orbit coupling).
2. The full spec screen over Au, Pt, Pd, Ir, Rh, Os using the pipeline default
   geometries, writing a single ranked CSV -- the deliverable requested in the
   project spec.

Run:
    python examples/run_platinum_cluster_screen.py
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orme_lab.config import DEFAULT_CONFIG  # noqa: E402
from orme_lab.elements import core_screen_elements, get_element  # noqa: E402
from orme_lab.geometry import (  # noqa: E402
    make_compact_cluster,
    make_dimer,
    make_monomer,
)
from orme_lab.pipeline import run_screen, write_csv  # noqa: E402


def platinum_geometry_sweep(element):
    return [
        make_monomer(element),
        make_dimer(element),
        make_compact_cluster(element, 6),
        make_compact_cluster(element, 13),
        make_compact_cluster(element, 19),
    ]


def _print_table(records, limit=None):
    rows = records if limit is None else records[:limit]
    print(f"{'el':3}{'geom':10} {'spin':10} {'coup':>6} {'aniso':>6} {'plaus':>7} ruled_out")
    print("-" * 62)
    for r in rows:
        print(
            f"{r.element:3}{r.geometry:10} {r.spin_label:10} {r.coupling:6.3f} "
            f"{r.anisotropy:6.3f} {r.sc_plausibility:7.4f} {r.ruled_out}"
        )


def main() -> None:
    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)

    # 1) Focused platinum sweep
    pt = get_element("Pt")
    pt_records = run_screen([pt], DEFAULT_CONFIG, platinum_geometry_sweep)
    pt_csv = os.path.abspath(os.path.join(out_dir, "platinum_cluster_screen.csv"))
    write_csv(pt_records, pt_csv)
    print(f"== Platinum sweep ({len(pt_records)} candidates) -> {pt_csv} ==")
    _print_table(pt_records)

    # 2) Full six-element PGM suite (the spec deliverable)
    suite = run_screen(core_screen_elements(), DEFAULT_CONFIG)
    suite_csv = os.path.abspath(os.path.join(out_dir, "pgm_suite_ranked.csv"))
    write_csv(suite, suite_csv)
    survivors = sum(1 for r in suite if not r.ruled_out)
    print(f"\n== Full PGM suite: {len(suite)} candidates, {survivors} not ruled out ==")
    print(f"Ranked CSV -> {suite_csv}\n")
    _print_table(suite, limit=10)
    print("\n(showing top 10; full ranking in the CSV)")


if __name__ == "__main__":
    main()
