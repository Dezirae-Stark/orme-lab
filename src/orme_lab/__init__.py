"""orme_lab -- a virtual lab for testing ORME/PGM high-spin superconductivity claims.

This package translates fringe "Orbitally Rearranged Monoatomic Element" (ORME)
and platinum-group-metal (PGM) superconductivity *claims* into explicit, testable
toy models. It is a hypothesis-testing scaffold, NOT a demonstration that any
such effect is real. Every score is bounded, documented, and falsifiable, and the
superconductivity gate can only ever report "not ruled out", never "proven".

Public API
----------
Elements & geometry:   :mod:`orme_lab.elements`, :mod:`orme_lab.geometry`
Physics toy models:    :mod:`orme_lab.spin_states`, :mod:`orme_lab.electron_density`,
                       :mod:`orme_lab.coupling`, :mod:`orme_lab.magnetic_field`
Scoring & output:      :mod:`orme_lab.superconductivity`, :mod:`orme_lab.observables`,
                       :mod:`orme_lab.pipeline`
"""

from __future__ import annotations

from .config import DEFAULT_CONFIG, LabConfig, ModelThresholds
from .coupling import inter_unit_coupling_score, is_electronically_isolated
from .electromagnetic_coherence import (
    CoherenceResult,
    ElectromagneticMode,
    coupling_regime,
    evaluate_em_coherence,
    plasmon_energy_ev,
    polariton_coherence_score,
)
from .electron_density import electron_density_anisotropy_score, ricebean_score
from .elements import Element, all_elements, core_screen_elements, get_element
from .magnetic_field import magnetic_field_suppression_factor
from .observables import ObservableSet, predict_observables
from .pipeline import CandidateRecord, run_screen, write_csv
from .spin_states import (
    SpinState,
    high_spin_state,
    low_spin_state,
    spin_polarization_score,
)
from .superconductivity import (
    PlausibilityResult,
    carrier_coherence_proxy,
    superconductivity_plausibility_score,
)

__version__ = "0.1.0"

__all__ = [
    "LabConfig",
    "ModelThresholds",
    "DEFAULT_CONFIG",
    "Element",
    "get_element",
    "all_elements",
    "core_screen_elements",
    "SpinState",
    "high_spin_state",
    "low_spin_state",
    "spin_polarization_score",
    "electron_density_anisotropy_score",
    "ricebean_score",
    "ElectromagneticMode",
    "CoherenceResult",
    "evaluate_em_coherence",
    "plasmon_energy_ev",
    "polariton_coherence_score",
    "coupling_regime",
    "inter_unit_coupling_score",
    "is_electronically_isolated",
    "magnetic_field_suppression_factor",
    "carrier_coherence_proxy",
    "superconductivity_plausibility_score",
    "PlausibilityResult",
    "ObservableSet",
    "predict_observables",
    "CandidateRecord",
    "run_screen",
    "write_csv",
    "__version__",
]
