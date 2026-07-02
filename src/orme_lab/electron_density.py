"""Electron-density anisotropy and the 'rice-bean' shape hypothesis.

Hypotheses 2 & 3: high-spin states may deform electron density into anisotropic
shapes, and the reported "rice-bean" shape may correspond to electron-density
anisotropy (a prolate / bean-like density distribution) rather than anything
exotic.

We model the valence density crudely as an ellipsoid with three semi-axes
(a >= b >= c) and reduce it to a single anisotropy scalar. A sphere is isotropic
(score 0). A cigar/bean (prolate, a >> b ~ c) and a disc (oblate) both score
higher. The 'rice-bean' band is a middle range of prolate anisotropy — strongly
elongated but not a thin needle.

This is a *shape parameterization*, not a computed density. The point is to give
the vague visual claim ("rice-bean") a quantitative, falsifiable handle.

    TODO(dft): replace the heuristic axis estimate with the eigenvalues of the
    second-moment tensor of a real charge density (cube file from PySCF/ORCA/
    GPAW). Then the anisotropy score becomes a genuine observable.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ModelThresholds
from .elements import Element
from .spin_states import SpinState


@dataclass(frozen=True)
class DensityEllipsoid:
    """Ellipsoidal approximation of a valence electron-density cloud.

    Semi-axes in arbitrary (relative) units; only their ratios matter here.
    Stored sorted so ``a >= b >= c`` always holds.
    """

    a: float
    b: float
    c: float

    def __post_init__(self) -> None:
        a, b, c = sorted((self.a, self.b, self.c), reverse=True)
        object.__setattr__(self, "a", a)
        object.__setattr__(self, "b", b)
        object.__setattr__(self, "c", c)

    @property
    def elongation(self) -> float:
        """a/c ratio: 1 = sphere, large = strongly elongated."""
        return self.a / self.c if self.c else float("inf")

    @property
    def is_prolate(self) -> bool:
        """Cigar/bean-like (long axis dominates) vs disc-like (oblate)."""
        # prolate if the gap a-b exceeds the gap b-c
        return (self.a - self.b) >= (self.b - self.c)


def estimate_density_ellipsoid(state: SpinState) -> DensityEllipsoid:
    """Heuristic: map unpaired-electron count to a prolate density ellipsoid.

    More unpaired spins in directional d-orbitals -> more elongation. We map
    0 unpaired -> sphere (1,1,1) and scale the long axis up with spin. Purely
    illustrative; the functional form is an assumption, flagged as such.
    """
    n = state.unpaired_electrons
    long_axis = 1.0 + 0.35 * n          # grows with spin polarization
    mid_axis = 1.0 + 0.05 * n           # slight secondary deformation
    short_axis = 1.0
    return DensityEllipsoid(long_axis, mid_axis, short_axis)


def electron_density_anisotropy_score(ellipsoid: DensityEllipsoid) -> float:
    """Toy anisotropy score in [0, 1].

    Uses a normalized fractional anisotropy of the three semi-axes (same idea as
    fractional anisotropy in diffusion imaging): 0 for a perfect sphere, ->1 as
    one axis dominates. Bounded and rotation-invariant.
    """
    a, b, c = ellipsoid.a, ellipsoid.b, ellipsoid.c
    mean = (a + b + c) / 3.0
    if mean == 0:
        return 0.0
    num = ((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2) ** 0.5
    den = (a * a + b * b + c * c) ** 0.5
    if den == 0:
        return 0.0
    # fractional anisotropy in [0,1]; sqrt(3/2) normalizes the max to 1
    fa = (1.5 ** 0.5) * num / den
    return min(max(fa, 0.0), 1.0)


def is_ricebean(score: float, thresholds: ModelThresholds) -> bool:
    """Does an anisotropy score fall in the 'rice-bean' band?

    The band is defined in :class:`~orme_lab.config.ModelThresholds`. Below it
    the density is ~spherical; above it, a thin needle. The bean is in between.
    """
    return thresholds.anisotropy_ricebean_low <= score <= thresholds.anisotropy_ricebean_high


def ricebean_score(state: SpinState, thresholds: ModelThresholds) -> tuple[float, bool]:
    """Convenience: full anisotropy pipeline for a spin state.

    Returns ``(anisotropy_score, is_ricebean_flag)``.
    """
    ellipsoid = estimate_density_ellipsoid(state)
    score = electron_density_anisotropy_score(ellipsoid)
    return score, is_ricebean(score, thresholds)
