#!/usr/bin/env python3
"""Visualize the toy electron-density ellipsoid ('rice-bean' shape).

For a chosen element and spin state, this plots the 2D cross-section of the
density ellipsoid produced by :mod:`orme_lab.electron_density`, annotated with
its anisotropy score and whether it falls in the 'rice-bean' band.

matplotlib is OPTIONAL. If it is not installed, the script falls back to an
ASCII sketch so the example still runs on a bare stdlib environment.

Run:
    python examples/plot_candidate_density.py Pt high_spin
    python examples/plot_candidate_density.py Os
"""

from __future__ import annotations

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from orme_lab.config import ModelThresholds  # noqa: E402
from orme_lab.electron_density import (  # noqa: E402
    electron_density_anisotropy_score,
    estimate_density_ellipsoid,
    is_ricebean,
)
from orme_lab.elements import get_element  # noqa: E402
from orme_lab.spin_states import high_spin_state, low_spin_state  # noqa: E402


def _ascii_ellipse(a: float, c: float, width: int = 41) -> str:
    """Crude ASCII rendering of an a-by-c ellipse cross-section."""
    scale = (width // 2) / a
    ha = int(a * scale)
    hc = int(c * scale)
    lines = []
    for y in range(-hc, hc + 1):
        row = []
        for x in range(-ha, ha + 1):
            inside = (x / (a * scale)) ** 2 + (y / (c * scale)) ** 2 <= 1.0
            row.append("#" if inside else " ")
        lines.append("".join(row))
    return "\n".join(lines)


def main() -> None:
    symbol = sys.argv[1] if len(sys.argv) > 1 else "Pt"
    spin = sys.argv[2] if len(sys.argv) > 2 else "high_spin"

    el = get_element(symbol)
    state = high_spin_state(el) if spin == "high_spin" else low_spin_state(el)
    th = ModelThresholds()

    ellipsoid = estimate_density_ellipsoid(state)
    score = electron_density_anisotropy_score(ellipsoid)
    bean = is_ricebean(score, th)

    print(f"{el.name} ({el.symbol}), {spin}: unpaired={state.unpaired_electrons}")
    print(f"  ellipsoid semi-axes (a>=b>=c): "
          f"{ellipsoid.a:.3f}, {ellipsoid.b:.3f}, {ellipsoid.c:.3f}")
    print(f"  elongation a/c = {ellipsoid.elongation:.3f}  "
          f"({'prolate/bean-like' if ellipsoid.is_prolate else 'oblate/disc-like'})")
    print(f"  anisotropy score = {score:.3f}  rice-bean band? {bean}")

    try:
        import matplotlib.pyplot as plt  # noqa: WPS433 (optional dependency)
    except ImportError:
        print("\n[matplotlib not installed -> ASCII cross-section (a-c plane)]\n")
        print(_ascii_ellipse(ellipsoid.a, ellipsoid.c))
        return

    theta = [i * 2 * math.pi / 200 for i in range(201)]
    xs = [ellipsoid.a * math.cos(t) for t in theta]
    ys = [ellipsoid.c * math.sin(t) for t in theta]

    fig, ax = plt.subplots(figsize=(5, 5))
    ax.plot(xs, ys, linewidth=2)
    ax.fill(xs, ys, alpha=0.2)
    ax.set_aspect("equal")
    ax.set_title(
        f"{el.symbol} {spin} density cross-section\n"
        f"anisotropy={score:.2f}  rice-bean={bean}"
    )
    ax.set_xlabel("long axis (a)")
    ax.set_ylabel("short axis (c)")

    out_dir = os.path.join(os.path.dirname(__file__), "..", "outputs")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.abspath(os.path.join(out_dir, f"density_{el.symbol}_{spin}.png"))
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    print(f"\nSaved figure -> {out_path}")


if __name__ == "__main__":
    main()
