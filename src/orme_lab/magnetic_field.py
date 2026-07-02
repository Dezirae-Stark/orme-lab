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

from .config import BOHR_MAGNETON, BOLTZMANN
from .spin_states import SpinState


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
