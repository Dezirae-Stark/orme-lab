#!/usr/bin/env python3
"""Write a Gaussian .cube from the analytic harmonic-oscillator eigenstate.

This is the offline half of the lab's **DFT-cube path**: the interactive lab
(``web/cube.js``) loads a Gaussian ``.cube`` and isosurfaces it through the same
pipeline as the analytic eigenstate. A real ab-initio backend would emit that
cube from a computed charge density (see ``DFTBackend.density_cube`` /
``Capability.DENSITY_CUBE`` in ``src/orme_lab/backends.py``). Until one is wired,
this tool emits the cube from the **analytic model** — so the format and the
end-to-end path are exercised with honest, non-fabricated data.

    IMPORTANT: the cube this writes is a MODEL wavefunction (harmonic oscillator),
    NOT a DFT calculation and NOT real experimental data. It stays Level 2.

Usage:
    python tools/eigenstate_to_cube.py --k 0 --l 2 --m 0 -o state.cube
    python tools/eigenstate_to_cube.py --k 1 --l 1 --m -1 --res 48 --density -o rho.cube
"""

from __future__ import annotations

import argparse
import math


def solid_harmonic(l: int, m: int, x: float, y: float, z: float) -> float:
    r2 = x * x + y * y + z * z
    if l == 0:
        return 1.0
    if l == 1:
        return {(-1): y, 0: z, 1: x}[m]
    if l == 2:
        return {(-2): x * y, (-1): y * z, 0: 3 * z * z - r2, 1: x * z, 2: x * x - y * y}[m]
    if l == 3:
        return {
            (-3): y * (3 * x * x - y * y), (-2): x * y * z, (-1): y * (5 * z * z - r2),
            0: z * (5 * z * z - 3 * r2), 1: x * (5 * z * z - r2), 2: z * (x * x - y * y),
            3: x * (x * x - 3 * y * y),
        }[m]
    raise ValueError("l must be 0..3")


def laguerre(k: int, alpha: float, x: float) -> float:
    if k <= 0:
        return 1.0
    l0, l1 = 1.0, 1 + alpha - x
    for i in range(1, k):
        l0, l1 = l1, ((2 * i + 1 + alpha - x) * l1 - (i + alpha) * l0) / (i + 1)
    return l1


def psi(k: int, l: int, m: int, x: float, y: float, z: float) -> float:
    r2 = x * x + y * y + z * z
    return solid_harmonic(l, m, x, y, z) * math.exp(-r2 / 2) * laguerre(k, l + 0.5, r2)


def write_cube(path: str, k: int, l: int, m: int, res: int, density: bool) -> None:
    if not (-l <= m <= l):
        raise ValueError(f"m={m} out of range for l={l}")
    extent = math.sqrt(2 * (2 * k + l) + 3) + 2.6
    step = 2 * extent / (res - 1)
    kind = "density rho = |psi|^2" if density else "orbital psi (signed)"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"ORME Lab -- analytic harmonic-oscillator eigenstate |k={k},l={l},m={m}>\n")
        f.write(f"MODEL POTENTIAL, not DFT, not experimental. {kind}. E=(2k+l+3/2)hw. Load via the lab's DFT-cube path.\n")
        # natoms + origin (Bohr); one dummy atom at the origin
        f.write(f"{1:5d} {-extent:12.6f} {-extent:12.6f} {-extent:12.6f}\n")
        f.write(f"{res:5d} {step:12.6f} {0.0:12.6f} {0.0:12.6f}\n")
        f.write(f"{res:5d} {0.0:12.6f} {step:12.6f} {0.0:12.6f}\n")
        f.write(f"{res:5d} {0.0:12.6f} {0.0:12.6f} {step:12.6f}\n")
        f.write(f"{1:5d} {0.0:12.6f} {0.0:12.6f} {0.0:12.6f} {0.0:12.6f}\n")  # dummy H at origin
        # volumetric data: x outer, y middle, z inner (z fastest); 6 per line
        for ix in range(res):
            x = -extent + ix * step
            for iy in range(res):
                y = -extent + iy * step
                col = 0
                for iz in range(res):
                    z = -extent + iz * step
                    v = psi(k, l, m, x, y, z)
                    if density:
                        v = v * v
                    f.write(f"{v:13.5e}")
                    col += 1
                    if col % 6 == 0:
                        f.write("\n")
                if col % 6 != 0:
                    f.write("\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Emit a Gaussian .cube from the analytic HO eigenstate (a MODEL, not DFT).")
    ap.add_argument("--k", type=int, default=0)
    ap.add_argument("--l", type=int, default=2)
    ap.add_argument("--m", type=int, default=0)
    ap.add_argument("--res", type=int, default=40, help="grid points per axis (default 40)")
    ap.add_argument("--density", action="store_true", help="write |psi|^2 (non-negative density) instead of signed psi")
    ap.add_argument("-o", "--out", default="eigenstate.cube")
    a = ap.parse_args()
    write_cube(a.out, a.k, a.l, a.m, a.res, a.density)
    n2 = 2 * (2 * a.k + a.l) + 3
    print(f"wrote {a.out}: |k={a.k},l={a.l},m={a.m}>  E={n2}/2 hw  {a.res}^3  ({'density' if a.density else 'orbital'})")
    print("  MODEL (harmonic oscillator), not DFT. Load it in the lab: eigenstate mode -> load DFT .cube.")


if __name__ == "__main__":
    main()
