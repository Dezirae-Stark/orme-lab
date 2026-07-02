"""Central configuration for the ORME/PGM virtual lab.

This module holds *physical constants* (fixed) and *model thresholds* (tunable
assumptions). Keeping every magic number here — rather than scattering it across
the scoring modules — makes the model's assumptions auditable in one place. When
a reviewer asks "why did you decide coupling below 0.2 counts as isolated?", the
answer lives here and nowhere else.

Nothing in this file claims to be experimentally calibrated. These are *toy*
thresholds chosen to make the screening pipeline produce interpretable, ordered
output. Replacing them with values fit against real measurements is future work
(see the TODO markers throughout ``src/orme_lab``).
"""

from __future__ import annotations

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Physical constants (SI, CODATA-style values). These are FIXED, not tunable.
# ---------------------------------------------------------------------------
BOHR_MAGNETON = 9.2740100783e-24        # J / T
BOLTZMANN = 1.380649e-23                # J / K
ELEMENTARY_CHARGE = 1.602176634e-19     # C
HBAR = 1.054571817e-34                  # J s
VACUUM_PERMEABILITY = 1.25663706212e-6  # N / A^2
BOHR_RADIUS = 5.29177210903e-11         # m

ROOM_TEMPERATURE_K = 298.15             # ambient reference temperature


@dataclass(frozen=True)
class ModelThresholds:
    """Tunable decision boundaries for the toy scoring models.

    Every field is an *assumption*, deliberately conservative. Frozen so a run
    cannot silently mutate its own thresholds mid-screen (determinism matters:
    two screens with the same config must produce the same ranking).
    """

    # --- superconductivity plausibility gates (all must pass) ---------------
    min_coupling_for_bulk: float = 0.20
    """Below this inter-unit coupling score, units are treated as electronically
    isolated and bulk superconductivity is ruled out (hypothesis 5)."""

    min_carrier_proxy: float = 0.15
    """Minimum coherence/carrier proxy. A superconductor needs mobile paired
    carriers; a state with no delocalized density fails regardless of coupling."""

    min_field_tolerance: float = 0.10
    """Minimum tolerance to an applied magnetic field. A candidate destroyed by
    an infinitesimal field is not a robust superconducting phase (hypothesis 7)."""

    min_structural_stability: float = 0.25
    """Minimum structural-stability proxy. A metastable state that relaxes away
    instantly cannot host a measurable phase."""

    min_observable_signal: float = 0.10
    """Minimum predicted-observable magnitude. If the model predicts nothing
    measurable, the claim is unfalsifiable and we decline to score it high."""

    # --- geometry / density heuristics -------------------------------------
    anisotropy_ricebean_low: float = 0.30
    """Lower edge of the 'rice-bean' (prolate) anisotropy band."""

    anisotropy_ricebean_high: float = 0.75
    """Upper edge of the 'rice-bean' band. Above this the density is a needle,
    not a bean; below it is roughly spherical."""

    coupling_distance_scale_ang: float = 3.0
    """Nearest-neighbour distance (angstrom) at which coupling falls to ~1/e.
    Rough proxy for orbital-overlap decay length in a PGM cluster."""


@dataclass(frozen=True)
class LabConfig:
    """Top-level run configuration passed through the pipeline."""

    thresholds: ModelThresholds = field(default_factory=ModelThresholds)
    temperature_k: float = ROOM_TEMPERATURE_K
    applied_field_t: float = 0.0
    """Applied external magnetic field in tesla for the screen (0 = zero-field)."""

    random_seed: int = 1729
    """Seed for any stochastic geometry perturbation. Fixed by default so runs
    are reproducible — see the operator's determinism commitment."""

    output_dir: str = "outputs"


DEFAULT_CONFIG = LabConfig()
