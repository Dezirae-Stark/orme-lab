"""Predicted experimental observables.

The whole project is only meaningful if it predicts things an experimentalist
could measure and use to *falsify* the claim. This module turns internal scores
into predicted signatures:

* magnetic susceptibility (chi)      -- Curie-law estimate from the spin state
* resistance behaviour (qualitative) -- metallic / activated / candidate-SC
* field sensitivity                  -- how strongly a field perturbs the state
* Meissner / diamagnetic screening   -- the observable that separates a real
                                        superconductor from a mere zero-resistance
                                        artifact (see docs/validation_tests.md)

Why zero resistance is not enough: a superconductor must ALSO expel magnetic
flux (the Meissner effect), giving strong diamagnetic screening (chi -> -1 in SI
volume units for a perfect bulk superconductor). A short, a percolation path, or
a measurement artifact can mimic zero resistance without any screening. So the
screening metric is treated as a first-class observable, not an afterthought.

    TODO(dft/epw): replace the Curie-law and heuristic screening estimates with
    computed susceptibilities and, for the SC channel, an Eliashberg/EPW-derived
    electron-phonon coupling and gap. Only then does 'screening' become ab-initio.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import BOHR_MAGNETON, BOLTZMANN, VACUUM_PERMEABILITY
from .magnetic_field import magnetic_field_suppression_factor
from .spin_states import SpinState


@dataclass(frozen=True)
class ObservableSet:
    """Bundle of predicted observables for one candidate.

    All values are toy predictions; ``notes`` records qualitative caveats.
    """

    molar_susceptibility: float          # Curie-law chi_molar proxy (SI-ish, relative)
    resistance_regime: str               # 'metallic' | 'activated' | 'candidate-sc'
    field_sensitivity: float             # [0,1], how much a field perturbs the state
    meissner_screening: float            # [0,1], diamagnetic flux-expulsion proxy
    notes: str = ""

    @property
    def has_measurable_signal(self) -> bool:
        """True if at least one observable is above the noise-floor threshold
        used by the pipeline (kept simple: any nonzero screening or a non-trivial
        susceptibility)."""
        return self.meissner_screening > 0.0 or abs(self.molar_susceptibility) > 1e-9


def curie_susceptibility(state: SpinState, temperature_k: float, number_density_m3: float = 6.0e28) -> float:
    """Curie-law molar-ish magnetic susceptibility proxy.

    chi = (n * mu_0 * mu_eff^2) / (3 k_B T), with mu_eff the spin-only moment.
    Returns a relative dimensionless-ish figure suitable for ranking, not an
    absolute lab value. Zero for a spinless state. Larger for high-spin / low T.

    ``number_density_m3`` defaults to a metal-like ~6e28 atoms/m^3.
    """
    if temperature_k <= 0:
        return 0.0
    mu_eff = state.spin_only_moment_bohr * BOHR_MAGNETON
    return (number_density_m3 * VACUUM_PERMEABILITY * mu_eff * mu_eff) / (3.0 * BOLTZMANN * temperature_k)


def predict_resistance_regime(coupling_score: float, carrier_proxy: float) -> str:
    """Qualitative resistance behaviour from coupling and carrier availability.

    * high coupling + high carriers -> 'candidate-sc' (worth Meissner testing)
    * high coupling, low carriers   -> 'metallic'
    * low coupling                  -> 'activated' (hopping / insulating-like)

    Deliberately coarse: this is a routing label for *which experiment to run*,
    not a transport calculation.
    """
    if coupling_score >= 0.5 and carrier_proxy >= 0.4:
        return "candidate-sc"
    if coupling_score >= 0.3:
        return "metallic"
    return "activated"


def meissner_screening_proxy(coupling_score: float, carrier_proxy: float, field_suppression: float) -> float:
    """Diamagnetic-screening proxy in [0, 1].

    Real flux expulsion needs a coherent condensate (coupling), enough paired
    carriers, and survival of the applied field. We take the product so that any
    missing ingredient collapses screening to ~0 — matching the physics that
    partial/percolative systems show weak, incomplete screening.

    A value near 1 corresponds to strong Meissner-like expulsion; near 0 means
    no screening (and hence any observed 'zero resistance' would be suspect).
    """
    return coupling_score * carrier_proxy * field_suppression


def field_sensitivity_score(field_suppression: float) -> float:
    """How sensitive the candidate is to the applied field, in [0, 1].

    Defined as 1 - suppression: a candidate barely affected by the field
    (suppression ~1) has low sensitivity; one destroyed by it (suppression ~0)
    has high sensitivity."""
    return 1.0 - field_suppression


def predict_observables(
    state: SpinState,
    coupling_score: float,
    carrier_proxy: float,
    temperature_k: float,
    applied_field_t: float,
    critical_field_t: float,
) -> ObservableSet:
    """Assemble the full observable set for a candidate."""
    chi = curie_susceptibility(state, temperature_k)
    suppression = magnetic_field_suppression_factor(applied_field_t, critical_field_t)
    regime = predict_resistance_regime(coupling_score, carrier_proxy)
    screening = meissner_screening_proxy(coupling_score, carrier_proxy, suppression)
    sensitivity = field_sensitivity_score(suppression)

    notes = []
    if regime == "candidate-sc" and screening < 0.1:
        notes.append("zero-R plausible but weak screening: check for artifact/percolation")
    if state.unpaired_electrons > 0 and chi > 0:
        notes.append("paramagnetic Curie response expected")

    return ObservableSet(
        molar_susceptibility=chi,
        resistance_regime=regime,
        field_sensitivity=sensitivity,
        meissner_screening=screening,
        notes="; ".join(notes),
    )
