"""Build the periodic reference lattice EPW runs on.

COUNTERFACTUAL: an imposed close-packed crystal, inferred from the cluster's
nearest-neighbour distance and carrying the candidate's spin state. NOT the
ORME motif, NOT the finite cluster, NOT any observed phase. The NN->crystal map
is under-determined (fcc/hcp, c/a are conventions); see the spec's O2. Level 2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..elements import Element
from ..geometry import ClusterGeometry
from ..spin_states import SpinState

ANGSTROM_TO_BOHR = 1.8897259886
IDEAL_C_OVER_A = 1.6329931619          # sqrt(8/3)
_HCP = frozenset({"Os", "Ru"})         # ambient hcp; everything else in the screen is fcc


class ApproximantUndefined(Exception):
    """Raised when a geometry has no well-defined nearest-neighbour distance
    (e.g. a monomer), so no periodic approximant can be built."""


@dataclass(frozen=True)
class PeriodicApproximant:
    element_symbol: str
    bravais: str            # "fcc" | "hcp"
    a_angstrom: float
    c_over_a: float | None  # None for fcc
    spin_polarized: bool
    starting_magnetization: float
    label: str

    @property
    def ibrav(self) -> int:
        return 2 if self.bravais == "fcc" else 4

    @property
    def a_bohr(self) -> float:
        return self.a_angstrom * ANGSTROM_TO_BOHR


def build_approximant(element: Element, geometry: ClusterGeometry,
                      spin_state: SpinState) -> PeriodicApproximant:
    d = geometry.nearest_neighbor_distance
    if not math.isfinite(d):
        raise ApproximantUndefined(
            f"{element.symbol}/{geometry.label or 'geometry'} has no finite "
            f"nearest-neighbour distance (n_atoms={geometry.n_atoms}); "
            f"no periodic approximant is defined."
        )
    hcp = element.symbol in _HCP
    bravais = "hcp" if hcp else "fcc"
    a = d if hcp else d * math.sqrt(2.0)          # fcc nn = a/sqrt(2)
    c_over_a = IDEAL_C_OVER_A if hcp else None
    unpaired = spin_state.unpaired_electrons
    return PeriodicApproximant(
        element_symbol=element.symbol,
        bravais=bravais,
        a_angstrom=a,
        c_over_a=c_over_a,
        spin_polarized=unpaired > 0,
        starting_magnetization=min(1.0, unpaired / 10.0),
        label=f"{element.symbol}-{bravais}-{geometry.label or 'cluster'}",
    )
