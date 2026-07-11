"""Tests for the two-branch (A: SC / B: Hudson optical) verdict."""
from __future__ import annotations

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.branch_verdict import BranchVerdict, combine_branches
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.hudson_optical import HudsonClaim, evaluate_hudson_optical
from orme_lab.identity import IdentityWitness
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state

TH = DEFAULT_CONFIG.thresholds


def _record(sym, identity=None):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG, identity=identity)


def _hudson(**kw):
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4,
                                   thresholds=TH, matter_ev=9.0, coupling_fraction=0.3,
                                   cavity_loss_ev=0.02, matter_loss_ev=0.02, **kw)


def test_branches_are_reported_independently():
    w = IdentityWitness("Au", "metallic", "sub-nm-cluster", 0.0, ("XRD",))
    rec = _record("Au", identity=w)
    hud = _hudson()                                  # strong coupling, no lab inputs
    v = combine_branches(rec, hud)
    assert isinstance(v, BranchVerdict)
    assert v.branch_a_credited == rec.credited_sc_lead
    assert HudsonClaim.STRONG_COUPLING in v.branch_b_levels
    # Branch B (no persistence, no magnetism) cannot predict the full Hudson phase
    assert v.hudson_phase_predicted is False


def test_hudson_phase_predicted_only_with_full_branch_b_stack():
    rec = _record("Au", identity=IdentityWitness("Au", "metallic", "sub-nm-cluster", 0.0, ("XRD",)))
    hud = _hudson(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    v = combine_branches(rec, hud)
    assert HudsonClaim.HUDSON_PHASE in hud.supported
    assert v.hudson_phase_predicted is True


def test_branch_b_does_not_set_branch_a():
    # A candidate with NO identity witness is not credited in Branch A regardless of a
    # strong Branch B — the optical branch never rescues the SC gate.
    rec = _record("Au")                              # no identity -> not credited
    hud = _hudson(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    v = combine_branches(rec, hud)
    assert v.branch_a_credited is False
    assert HudsonClaim.HUDSON_PHASE in v.branch_b_levels
    assert "independent" in v.explain().lower()
