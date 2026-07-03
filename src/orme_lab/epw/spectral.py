"""Eliashberg spectral function alpha^2 F(omega) and its moments.

lambda   = 2 * int alpha2F/omega d omega
omega_log = exp[(2/lambda) int (alpha2F/omega) ln omega d omega]
omega_2   = [(2/lambda) int alpha2F * omega d omega]^(1/2)

Moments are returned in the SAME unit as the omega grid. Guards (G-SPEC): the
full non-negative grid (including omega=0) is retained; only the divergent
1/omega factor and 0*ln0 term at omega<=omega_min are zeroed in the integrand,
not the grid points themselves; alpha2F is clipped to >= 0; a null positive
spectrum returns (0,0,0), never NaN; negative (unstable) phonon frequencies set
.unstable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _trapz(y: list[float], x: list[float]) -> float:
    total = 0.0
    for i in range(1, len(x)):
        total += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1])
    return total


@dataclass(frozen=True)
class EliashbergFunction:
    omega: tuple[float, ...]
    a2f: tuple[float, ...]
    omega_min: float = 1e-6
    unstable_tol: float = 0.05

    def _grid(self) -> tuple[list[float], list[float]]:
        # Keep the full non-negative grid (INCLUDING omega=0) so trapezoidal
        # geometry near omega=0 is preserved; a spike adjacent to omega=0 keeps
        # its full weight. Clip a2f to >= 0. Strictly-negative frequencies
        # (unstable modes) are excluded here and reported by .unstable instead.
        xs: list[float] = []
        ys: list[float] = []
        for w, a in zip(self.omega, self.a2f):
            if w >= 0.0:
                xs.append(w)
                ys.append(max(0.0, a))
        return xs, ys

    @property
    def unstable(self) -> bool:
        neg = _trapz([abs(a) for w, a in zip(self.omega, self.a2f) if w < -self.omega_min],
                     [w for w in self.omega if w < -self.omega_min])
        pos = _trapz([max(0.0, a) for w, a in zip(self.omega, self.a2f) if w > self.omega_min],
                     [w for w in self.omega if w > self.omega_min])
        total = neg + pos
        return total > 0.0 and neg > self.unstable_tol * total

    @property
    def lam(self) -> float:
        xs, ys = self._grid()
        if len(xs) < 2:
            return 0.0
        integrand = [(a / w) if w > self.omega_min else 0.0 for w, a in zip(xs, ys)]
        return 2.0 * _trapz(integrand, xs)

    @property
    def omega_log(self) -> float:
        lam = self.lam
        if lam <= 0.0:
            return 0.0
        xs, ys = self._grid()
        integrand = [((a / w) * math.log(w)) if w > self.omega_min else 0.0
                     for w, a in zip(xs, ys)]
        return math.exp((2.0 / lam) * _trapz(integrand, xs))

    @property
    def omega_2(self) -> float:
        lam = self.lam
        if lam <= 0.0:
            return 0.0
        xs, ys = self._grid()
        integrand = [a * w for w, a in zip(xs, ys)]   # a2f*omega is 0 at omega=0
        return math.sqrt((2.0 / lam) * _trapz(integrand, xs))

    def moments(self) -> tuple[float, float, float]:
        return (self.lam, self.omega_log, self.omega_2)
