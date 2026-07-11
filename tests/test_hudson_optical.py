"""Tests for the Hudson optical-coherence branch (Branch B)."""
from __future__ import annotations

import math

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.hudson_optical import (
    is_anticrossing,
    mode_composition,
    polariton_branches,
)

TH = DEFAULT_CONFIG.thresholds


def test_polariton_branches_split_by_rabi_at_resonance():
    # On resonance (matter == photon), the branches are separated by 2g (the Rabi
    # splitting), symmetric about the shared bare energy.
    lower, upper = polariton_branches(2.0, 2.0, 0.3)
    assert math.isclose(upper - lower, 0.6, rel_tol=1e-9)   # 2g
    assert math.isclose((upper + lower) / 2, 2.0, rel_tol=1e-9)


def test_mode_composition_is_5050_on_resonance():
    f_ph, f_el = mode_composition(2.0, 2.0, 0.3)
    assert math.isclose(f_ph, 0.5, rel_tol=1e-9)
    assert math.isclose(f_el, 0.5, rel_tol=1e-9)
    assert math.isclose(f_ph + f_el, 1.0, rel_tol=1e-12)


def test_lower_polariton_is_photon_like_when_photon_below_matter():
    # matter well ABOVE photon -> the lower polariton tracks the photon -> photon-like.
    f_ph, f_el = mode_composition(3.0, 1.0, 0.05)
    assert f_ph > 0.9
    assert f_el < 0.1


def test_anticrossing_requires_splitting_above_linewidth():
    assert is_anticrossing(0.30, linewidth_ev=0.10) is True    # 2g=0.6 > 0.10
    assert is_anticrossing(0.02, linewidth_ev=0.10) is False   # 2g=0.04 < 0.10


from orme_lab.electromagnetic_coherence import ElectromagneticMode
from orme_lab.hudson_optical import OpticalOrderParameter, order_parameter_from_mode


def _resonant_mode(mode_ev=2.0, g=0.3, kappa=0.05, gamma=0.05):
    return ElectromagneticMode(mode_energy_ev=mode_ev, coupling_energy_ev=g,
                               cavity_loss_ev=kappa, matter_loss_ev=gamma)


def test_order_parameter_bundles_the_seven_quantities():
    m = _resonant_mode()
    oh = order_parameter_from_mode(m, matter_ev=2.0, thresholds=TH)
    assert isinstance(oh, OpticalOrderParameter)
    assert oh.omega0_ev == 2.0
    assert oh.coupling_ev == 0.3
    assert oh.quality_factor == m.quality_factor
    assert oh.tau_coh_fs == m.coherence_lifetime_fs
    # on resonance the composition is 50/50
    assert math.isclose(oh.f_photon, 0.5, rel_tol=1e-9)
    assert math.isclose(oh.f_electron, 0.5, rel_tol=1e-9)
    # spatial coherence length is a positive surrogate = frac * c * tau
    assert oh.l_coh_nm > 0.0


def test_order_parameter_is_frozen():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    try:
        oh.omega0_ev = 1.0  # type: ignore[misc]
        assert False, "OpticalOrderParameter must be immutable"
    except Exception:
        pass


from orme_lab.evidence import EvidenceLevel
from orme_lab.hudson_optical import Persistence, classify_persistence


def test_persistence_defaults_to_driven_dissipative_without_measurement():
    # The simulation CANNOT assert persistence. With no measured ring-down, the
    # conservative null is driven-dissipative.
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=None, thresholds=TH)
    assert r.persistence is Persistence.DRIVEN_DISSIPATIVE
    assert r.measured_fs is None
    assert "requires an external" in r.note


def test_measured_ringdown_below_metastable_is_driven_dissipative():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 2, thresholds=TH)
    assert r.persistence is Persistence.DRIVEN_DISSIPATIVE     # ratio 2 < 10


def test_measured_ringdown_metastable_band():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 100, thresholds=TH)
    assert r.persistence is Persistence.METASTABLE            # 10 <= 100 < 1e6


def test_measured_ringdown_persistent_reaches_observation_if_confirmed():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 1e7, thresholds=TH)
    assert r.persistence is Persistence.PERSISTENT
    # a MEASURED persistent ring-down is an observation, not a simulation output
    assert r.evidence_level_if_confirmed == int(EvidenceLevel.INITIAL_OBSERVATION)
