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


from orme_lab.hudson_optical import (
    SURVEY_BANDS,
    resonance_survey,
    strongest_band,
)


def test_survey_covers_rf_through_near_uv_in_fixed_order():
    names = [b[0] for b in SURVEY_BANDS]
    assert names == ["RF", "microwave", "THz", "IR", "visible", "near-UV"]
    # "light" is not restricted to visible: RF is the lowest band (Hudson tuned with RF)
    assert SURVEY_BANDS[0][1] < SURVEY_BANDS[-1][1]


def test_survey_is_deterministic_and_ordered():
    a = resonance_survey(0.05, 0.10, 0.05, TH)
    b = resonance_survey(0.05, 0.10, 0.05, TH)
    assert a == b
    assert [r.band for r in a] == [b[0] for b in SURVEY_BANDS]


def test_strongest_band_picks_max_cooperativity_among_non_weak():
    results = resonance_survey(0.05, 0.10, 0.05, TH)
    best = strongest_band(results)
    if best is not None:
        assert best.regime != "weak"
        assert all(best.cooperativity >= r.cooperativity for r in results if r.regime != "weak")


def test_strongest_band_is_none_when_all_weak():
    # crush coupling so no band reaches strong coupling
    results = resonance_survey(1e-6, 1.0, 1.0, TH)
    assert all(r.regime == "weak" for r in results)
    assert strongest_band(results) is None


from orme_lab.hudson_optical import CausalLink, magnetism_tracks_resonance


def test_causal_link_defaults_to_unestablished_without_measurement():
    # Hudson linked the circulating mode to the Meissner response. Without a measured
    # dM/dP at resonance, the model cannot assert the causal link.
    link = magnetism_tracks_resonance(measured_dM_dP=None, on_resonance=None)
    assert link.tracks is False
    assert "requires" in link.note


def test_causal_link_requires_response_on_resonance():
    # a real dM/dP but measured OFF resonance does not support the causal claim
    off = magnetism_tracks_resonance(measured_dM_dP=1.0, on_resonance=False)
    assert off.tracks is False
    on = magnetism_tracks_resonance(measured_dM_dP=1.0, on_resonance=True)
    assert on.tracks is True
    assert on.evidence_level_if_confirmed == int(EvidenceLevel.INITIAL_OBSERVATION)


def test_causal_link_rejects_negligible_response():
    link = magnetism_tracks_resonance(measured_dM_dP=1e-15, on_resonance=True)
    assert link.tracks is False    # below min_response -> no anomaly


from orme_lab.evidence import LAB_CEILING
from orme_lab.hudson_optical import (
    HudsonClaim,
    HudsonOpticalResult,
    evaluate_hudson_optical,
)


def _strong_coherent(**kw):
    # a strongly-coupled, coherent candidate (high density -> real plasmon, strong g)
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4,
                                   thresholds=TH, matter_ev=9.0, coupling_fraction=0.3,
                                   cavity_loss_ev=0.02, matter_loss_ev=0.02, **kw)


def test_levels_are_independent_none_implies_the_next():
    # Strong coupling (L3) supported by SIMULATION, but transport (L5, needs persistence)
    # and magnetism (L7, needs dM/dP) are NOT — because both are default-blocked.
    r = _strong_coherent()
    assert HudsonClaim.STRONG_COUPLING in r.supported
    assert HudsonClaim.LOW_LOSS_TRANSPORT not in r.supported     # no measured ring-down
    assert HudsonClaim.MAGNETISM_COUPLED not in r.supported      # no measured dM/dP
    assert HudsonClaim.HUDSON_PHASE not in r.supported           # conjunction at the top


def test_full_stack_supported_only_with_both_lab_inputs():
    r = _strong_coherent(measured_ringdown_fs=1e30,             # persistent
                         measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert HudsonClaim.LOW_LOSS_TRANSPORT in r.supported
    assert HudsonClaim.MAGNETISM_COUPLED in r.supported
    assert HudsonClaim.HUDSON_PHASE in r.supported


def test_result_evidence_level_is_clamped_to_lab_ceiling():
    # What the SIMULATION produces never exceeds Level 2, even with lab inputs folded in.
    r = _strong_coherent(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert r.evidence_level <= int(LAB_CEILING)


def test_weak_candidate_supports_at_most_resonance_detection():
    r = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.0,
                                thresholds=TH, matter_ev=9.0, coupling_fraction=1e-6,
                                cavity_loss_ev=1.0, matter_loss_ev=1.0)
    assert HudsonClaim.STRONG_COUPLING not in r.supported
    assert r.explain()   # non-empty, mentions the branch is not superconductivity evidence
