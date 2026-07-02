"""Inter-unit coupling — the make-or-break channel for bulk behaviour.

Hypotheses 4 & 5 are the crux of the whole project:

    4. Bulk superconductivity REQUIRES an inter-unit coupling channel.
    5. If units are truly electronically isolated, superconductivity should FAIL.

Superconductivity is a *collective, phase-coherent* state. A single isolated
atom (however exotic its internal spin state) cannot host a macroscopic coherent
condensate on its own — there is nowhere for the phase to propagate. So bulk
behaviour demands some channel connecting units: direct orbital overlap,
exchange, an intervening lattice/oxide, or Josephson tunnelling between grains
(hypothesis 6).

This module reduces "how strongly are neighbouring units coupled?" to a score in
[0, 1] built from geometry (distance, coordination) and an orbital-overlap
proxy. A monomer scores ~0 by construction, which is exactly the isolated-unit
limit that should fail the superconductivity gate.

    TODO(dft/tb): replace the exponential-overlap proxy with real transfer
    integrals (t_ij) from a tight-binding fit to a DFT band structure, or with
    a computed exchange coupling J for the magnetic-network scenario.
"""

from __future__ import annotations

import math

from .config import ModelThresholds
from .geometry import ClusterGeometry


def orbital_overlap_proxy(nn_distance_ang: float, thresholds: ModelThresholds) -> float:
    """Exponentially decaying overlap vs nearest-neighbour distance.

    exp(-(d - d0)/lambda) style decay, clamped to [0, 1], with lambda set by
    ``coupling_distance_scale_ang``. At the contact distance the proxy is ~1;
    beyond a few angstrom it vanishes. An infinite distance (monomer) -> 0.
    """
    if math.isinf(nn_distance_ang):
        return 0.0
    lam = thresholds.coupling_distance_scale_ang
    # Reference contact distance ~ lam; closer than that saturates near 1.
    val = math.exp(-(nn_distance_ang - lam) / lam)
    return min(max(val, 0.0), 1.0)


def inter_unit_coupling_score(
    geometry: ClusterGeometry,
    thresholds: ModelThresholds,
) -> float:
    """Toy inter-unit coupling score in [0, 1].

    Combines two geometric factors:

    * orbital-overlap proxy from the nearest-neighbour distance, and
    * a connectivity factor from mean coordination (more neighbours -> more
      pathways for phase coherence), saturating around a bulk-like coordination.

    A monomer has infinite nn-distance and zero coordination, giving a score of
    0 -> it will fail the bulk-superconductivity gate, honouring hypothesis 5.
    """
    if geometry.n_atoms < 2:
        return 0.0

    overlap = orbital_overlap_proxy(geometry.nearest_neighbor_distance, thresholds)

    # Coordination factor: 0 neighbours -> 0, saturating toward bulk (~12 for
    # close-packed). tanh gives a smooth, bounded ramp.
    coord = geometry.mean_coordination
    connectivity = math.tanh(coord / 6.0)

    # Geometric mean keeps the score honest: BOTH overlap AND connectivity must
    # be nonzero. A well-connected but too-distant network still scores low.
    return (overlap * connectivity) ** 0.5


def is_electronically_isolated(coupling_score: float, thresholds: ModelThresholds) -> bool:
    """Whether a unit is below the coupling floor for bulk behaviour.

    Returns True when the coupling score is under ``min_coupling_for_bulk`` —
    the operational definition of "electronically isolated" (hypothesis 5)."""
    return coupling_score < thresholds.min_coupling_for_bulk
