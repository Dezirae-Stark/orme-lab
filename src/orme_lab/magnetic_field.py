"""Magnetic-field response of candidate states.

Hypothesis 7: a magnetic field may stabilize, perturb, suppress, or destroy a
candidate state depending on the phase. This cuts both ways and the sign matters:

* A *superconductor* is DESTROYED by a sufficiently strong field (it exceeds the
  critical field Hc / Hc2). Field tolerance is therefore a necessary property —
  a phase killed by an infinitesimal field is not a robust superconductor — but
  a phase with unbounded field tolerance is not a superconductor either.
* A *high-spin magnetic* state is often STABILIZED by a field (Zeeman lowering of
  the aligned-spin configuration).

So "field sensitivity" is not a single good/bad axis; the interpretation depends
on which phase you are testing. This module provides:

* a Zeeman energy scale for a spin state, and
* a bounded "field suppression factor" in [0, 1] used by the superconductivity
  gate, where 1 means "survives the applied field" and 0 means "destroyed".

    TODO(physics): distinguish orbital (Hc2) and paramagnetic (Pauli/
    Chandrasekhar-Clogston) pair-breaking limits explicitly once a real gap
    scale is available. The single factor here conflates them.
"""

from __future__ import annotations

import math
from enum import Enum

from .config import BOLTZMANN
from .spin_states import SpinState

PAULI_SLOPE_T_PER_K = 1.86   # Chandrasekhar-Clogston / Pauli limit: Bc_pauli ~ 1.86 * Tc (weak-coupling BCS).
                             # Clogston, PRL 9, 266 (1962); Chandrasekhar, APL 1, 7 (1962).


class PairingSymmetry(Enum):
    """Assumed Cooper-pair symmetry for a candidate's field response.

    UNDETERMINED reproduces the legacy toy critical field (default; no assumption).
    SINGLET: a static moment pair-breaks -> field suppressed, capped at the Pauli limit.
    TRIPLET: equal-spin pairs carry the moment -> field-robust, may exceed the Pauli limit.
    """
    UNDETERMINED = "undetermined"
    SINGLET = "singlet"
    TRIPLET = "triplet"


def _legacy_critical_field(spin_score: float, coupling_score: float) -> float:
    """The pairing-agnostic toy critical field: a stronger, better-coupled candidate tolerates a
    larger field. Scaled to a few tesla so typical screening fields probe the transition. An
    assumption for ranking, not a computed Hc2. This module is the single source of this formula
    (used for the PairingSymmetry.UNDETERMINED branch below)."""
    return 5.0 * coupling_score * (0.5 + 0.5 * spin_score)


#: Public alias so callers/tests reference the pairing-agnostic legacy proxy by its familiar name.
critical_field_proxy = _legacy_critical_field


def pauli_limit_tesla(tc_kelvin: float) -> float:
    """Chandrasekhar-Clogston paramagnetic limit Bc_pauli (tesla) for a singlet gap ~ Tc."""
    return PAULI_SLOPE_T_PER_K * tc_kelvin


def pairing_critical_field(spin_score: float, coupling_score: float,
                           symmetry: "PairingSymmetry",
                           tc_kelvin: float | None = None) -> float:
    """Toy critical field (tesla), pairing-symmetry-conditional. Triage only.

    - UNDETERMINED: the legacy proxy (spin raises Hc); default, byte-identical.
    - TRIPLET: field-robust; spin raises Hc (equal-spin pairs carry the moment).
    - SINGLET: spin SUPPRESSES Hc (pair-breaking); when Tc is known, capped at the Pauli limit.
    """
    base = _legacy_critical_field(spin_score, coupling_score)
    if symmetry is PairingSymmetry.UNDETERMINED:
        return base
    if symmetry is PairingSymmetry.TRIPLET:
        return base
    # SINGLET: invert the spin dependence (moment pair-breaks), then cap at Pauli if Tc known.
    singlet = 5.0 * coupling_score * (1.0 - 0.5 * spin_score)
    if tc_kelvin is not None and tc_kelvin > 0.0:
        singlet = min(singlet, pauli_limit_tesla(tc_kelvin))
    return max(0.0, singlet)


def field_response_ratio(critical_field_t: float, tc_kelvin: float | None) -> float | None:
    """Bc / Bc_pauli — the singlet-vs-triplet discriminator. None when Tc is unknown
    (toy path): the ratio is a decisive-measurement PREDICTION, computable only with a
    pairing energy scale. > 1 => exceeds the Pauli limit => only a triplet can host it."""
    if tc_kelvin is None or tc_kelvin <= 0.0:
        return None
    return critical_field_t / pauli_limit_tesla(tc_kelvin)


def zeeman_energy_j(state: SpinState, field_t: float) -> float:
    """Zeeman interaction energy magnitude |mu . B| in joules (g approx 2)."""
    return abs(state.moment_si * field_t)


def zeeman_temperature_k(state: SpinState, field_t: float) -> float:
    """Zeeman energy expressed as an equivalent temperature (E/k_B), in kelvin.

    Handy for asking 'is the field effect large or small compared to thermal
    energy at the run temperature?'."""
    return zeeman_energy_j(state, field_t) / BOLTZMANN


def magnetic_field_suppression_factor(
    field_t: float,
    critical_field_t: float,
) -> float:
    """Superconducting field-survival factor in [0, 1].

    Models the order parameter's survival against an applied field using the
    standard empirical form 1 - (H/Hc)^2 for H < Hc, and 0 at/above Hc
    (mirroring the parabolic Hc(T) relation of type-I superconductors).

    Parameters
    ----------
    field_t:
        Applied field magnitude (tesla).
    critical_field_t:
        Toy critical field for the candidate phase (tesla). Must be > 0.

    Returns
    -------
    float
        1.0 at zero field, decreasing to 0.0 at the critical field. A candidate
        with a tiny critical field is suppressed by almost any real field.
    """
    if critical_field_t <= 0:
        return 0.0
    if field_t <= 0:
        return 1.0
    if field_t >= critical_field_t:
        return 0.0
    ratio = field_t / critical_field_t
    return 1.0 - ratio * ratio


def high_spin_field_stabilization(state: SpinState, field_t: float, temperature_k: float) -> float:
    """Toy stabilization score in [0, 1] for a *magnetic* (non-SC) candidate.

    Opposite sense to superconducting suppression: a field lowers the energy of
    an aligned high-spin state, so larger Zeeman-to-thermal ratio -> closer to 1.
    Uses tanh of the Zeeman energy over thermal energy. Returns 0 for a spinless
    state (nothing for the field to grab)."""
    if state.unpaired_electrons == 0 or temperature_k <= 0:
        return 0.0
    ratio = zeeman_energy_j(state, field_t) / (BOLTZMANN * temperature_k)
    return math.tanh(ratio)
