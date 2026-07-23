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
VACUUM_PERMITTIVITY = 8.8541878128e-12  # F / m (epsilon_0)
BOHR_RADIUS = 5.29177210903e-11         # m
ELECTRON_MASS = 9.1093837015e-31        # kg
SPEED_OF_LIGHT = 2.99792458e8           # m / s
PLANCK_H = 6.62607015e-34               # J s
EV_IN_JOULES = 1.602176634e-19          # J per eV

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

    # --- electromagnetic-coherence (polariton/plasmon) heuristics ----------
    ultrastrong_coupling_ratio: float = 0.10
    """Rabi-splitting / mode-energy ratio above which coupling is 'ultrastrong'.
    The ~10% figure is the conventional (if soft) boundary in cavity QED."""

    min_cooperativity_for_coherence: float = 1.0
    """Cooperativity C = 4g^2/(kappa*gamma) must exceed this for the coherent
    (strong-coupling) regime to be considered established. C>1 is the standard
    strong-coupling threshold."""

    # --- Branch B (Hudson optical-coherence) -----------------------------------
    #: Minimum photonic (Hopfield) fraction of the lower polariton for the mode to
    #: count as a genuine light-matter HYBRID rather than a bare matter excitation.
    hudson_min_photon_fraction: float = 0.20
    #: measured/predicted ring-down ratio at/above which a decayed mode is
    #: "metastable" (long-lived but not self-sustaining).
    hudson_metastable_ratio: float = 10.0
    #: measured/predicted ring-down ratio at/above which the mode is treated as
    #: effectively self-sustaining ("persistent") — Hudson's extraordinary claim.
    hudson_persistent_ratio: float = 1.0e6
    #: group velocity as a fraction of c, for the toy spatial-coherence-length
    #: surrogate L_coh = frac * c * tau_coh. Flagged toy; TODO(dft): compute v_g.
    hudson_group_velocity_fraction: float = 0.01

    # --- Hudson Claim Ledger (HC-02 dispersion policy + replication minima) -----
    hudson_hc02_min_isolated_fraction: float = 0.85   # f_single floor for "atomically dispersed"
    hudson_hc02_max_clustered_fraction: float = 0.20  # upper-bound cap on the clustered fraction
    hudson_hc02_cluster_margin: float = 0.05          # uncertainty margin added to clustered fraction
    hudson_hc02_pgm_pgm_tolerance: float = 0.15       # max fraction with a real PGM-PGM bond
    hudson_hc02_bond_length_ang: float = 3.2          # nn distance at/below this = a PGM-PGM bond
    hudson_replication_min_batches: int = 3           # G_replication: >= 3 independent batches
    hudson_replication_min_labs: int = 2              # G_replication: > 1 lab


@dataclass(frozen=True)
class LabConfig:
    """Top-level run configuration passed through the pipeline."""

    thresholds: ModelThresholds = field(default_factory=ModelThresholds)
    temperature_k: float = ROOM_TEMPERATURE_K
    applied_field_t: float = 0.0
    """Applied external magnetic field in tesla for the screen (0 = zero-field)."""

    pairing_symmetry: str = "undetermined"  # PairingSymmetry value; "singlet"/"triplet" branch the field response

    random_seed: int = 1729
    """Seed for any stochastic geometry perturbation. Fixed by default so runs
    are reproducible — see the operator's determinism commitment."""

    compute_em_coherence: bool = False
    """When True, the screen also computes the electromagnetic-coherence channel
    (plasmon/polariton) per candidate and records em_* observables. Off by
    default so the toy path's values stay byte-identical."""

    #: Compute Branch B (Hudson optical-coherence) for each candidate. ON by default:
    #: Branch B is central to the Hudson investigation (the resonantly-accessible hybrid
    #: light-matter mechanism), so the base screen carries it as a first-class,
    #: independent verdict beside the SC gate — not an optional add-on. Set False to
    #: recover the lightweight SC-only path.
    compute_hudson_optical: bool = True

    compute_orbital_order: bool = False
    """When True, the screen also computes the orbital-order descriptor (QE
    projwfc.x Löwdin d-occupations) per candidate and overrides the toy
    density-anisotropy value with the computed one, recording the off-gate
    orbital_order_param. Off by default so the toy path's values stay
    byte-identical -- with the flag off, or the backend absent, the field
    is None and the toy anisotropy is untouched."""

    output_dir: str = "outputs"


DEFAULT_CONFIG = LabConfig()
