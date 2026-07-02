#!/usr/bin/env python3
"""Mock screen for GOLD clusters across a geometry sweep.

Runs the toy pipeline over Au in monomer / dimer / chain / compact-cluster
geometries and several sizes, writes a ranked CSV to ``outputs/``, and prints
the ranking. Gold is the canonical Hudson-ORME example, so it is a useful
sanity case: the monomer must be ruled out (isolation), and only connected
geometries can even be considered.

Run:
    python examples/run_gold_cluster_screen.py
"""

from __future__ import annotations

import os
import sys

# Allow running straight from the repo without installing the package.
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orme_lab.config import DEFAULT_CONFIG  # noqa: E402
from orme_lab.elements import get_element  # noqa: E402
from orme_lab.geometry import (  # noqa: E402
    make_compact_cluster,
    make_dimer,
    make_linear_chain,
    make_monomer,
)
from orme_lab.pipeline import run_screen, write_csv  # noqa: E402


def gold_geometry_sweep(element):
    """A richer geometry sweep than the pipeline default, for one element."""
    return [
        make_monomer(element),
        make_dimer(element),
        make_linear_chain(element, 4),
        make_linear_chain(element, 8),
        make_compact_cluster(element, 4),
        make_compact_cluster(element, 13),
        make_compact_cluster(element, 19),
    ]


def main() -> None:
    au = get_element("Au")
    records = run_screen(
        elements=[au],
        config=DEFAULT_CONFIG,
        geometry_factory=gold_geometry_sweep,
    )

    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    csv_path = os.path.abspath(os.path.join(out_dir, "gold_cluster_screen.csv"))
    write_csv(records, csv_path)

    print(f"Gold cluster screen: {len(records)} candidates")
    print(f"Ranked CSV written to: {csv_path}\n")
    print(f"{'geom':10} {'spin':10} {'coup':>6} {'plaus':>7} {'ruled_out':>9}  regime")
    print("-" * 60)
    for r in records:
        print(
            f"{r.geometry:10} {r.spin_label:10} {r.coupling:6.3f} "
            f"{r.sc_plausibility:7.4f} {str(r.ruled_out):>9}  {r.resistance_regime}"
        )
    print(
        "\nReminder: a positive plausibility means 'not ruled out by this toy "
        "screen', NOT evidence of superconductivity."
    )


if __name__ == "__main__":
    main()
