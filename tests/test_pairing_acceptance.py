import pytest
from dataclasses import replace
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.lab_loop.triage import Verdict, triage
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator


def _av(target, metric, comp, thr, invariants, symmetry="undetermined"):
    return Avenue("a", Tier.TIER1, "d", target,
                  ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, False, True, None, symmetry),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


def test_1_independent_retirement():
    # killing H7-singlet leaves H7-triplet standing
    open_all = frozenset(HYPOTHESES)
    res = AvenueResult(_av("H7-singlet", "max_field_response_ratio", Comparator.GT, 1.0,
                           ("field_response_ratio",)), (), {"max_field_response_ratio": 1.5})
    out = triage(res, open_all)
    assert out.verdict == Verdict.KILLED_HYPOTHESIS and out.killed_hypothesis == "H7-singlet"
    assert "H7-triplet" in (open_all - {"H7-singlet"})


def test_2_drive_gated_on_triplet():
    res = AvenueResult(_av("H16-drive-triplet", "max_em_drive_response", Comparator.LT, 0.1,
                           ("em_drive_response",), "triplet"), (), {"max_em_drive_response": 0.5})
    assert triage(res, frozenset(HYPOTHESES) - {"H7-triplet"}).verdict == Verdict.INCONCLUSIVE
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED


def test_4_both_signals_off_gate():
    from orme_lab.lab_loop.closure import is_independent
    assert is_independent(("field_response_ratio",))
    assert is_independent(("em_drive_response",))


def test_5_hypotheses_diverge_same_ratio():
    # same field_response_ratio kills singlet (>1) and, mirrored, kills triplet (<=1)
    sing = _av("H7-singlet", "max_field_response_ratio", Comparator.GT, 1.0, ("field_response_ratio",))
    trip = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",))
    open_all = frozenset(HYPOTHESES)
    hi = {"max_field_response_ratio": 1.4}   # enhancement
    lo = {"max_field_response_ratio": 0.7}   # suppression
    assert triage(AvenueResult(sing, (), hi), open_all).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(AvenueResult(trip, (), hi), open_all).verdict == Verdict.SURVIVED
    assert triage(AvenueResult(trip, (), lo), open_all).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(AvenueResult(sing, (), lo), open_all).verdict == Verdict.SURVIVED


def _rec(symmetry, field_t=3.0, tc=None):
    el = get_element("Ir"); geo = make_compact_cluster(el, 13)
    cfg = replace(DEFAULT_CONFIG, pairing_symmetry=symmetry, applied_field_t=field_t)
    r = evaluate_candidate(el, geo, "high_spin", high_spin_state(el), cfg)
    return r


def test_6_stricter_under_singlet_than_undetermined():
    # a high-spin candidate is credited/field-tolerant less readily under the singlet assumption
    u = _rec("undetermined"); s = _rec("singlet")
    assert s.field_suppression <= u.field_suppression
    # and its surviving-mechanism set under singlet excludes the spin-positive triplet track
    assert "M_triplet" not in s.surviving_mechanisms


def test_3_no_double_count_clean_sign():
    # Under one symmetry, spin does not both credit a triplet mechanism AND carry a singlet penalty.
    s = _rec("singlet"); t = _rec("triplet")
    # singlet: no triplet credit; triplet: no phonon credit (the singlet pair-breaker)
    assert "M_triplet" not in s.surviving_mechanisms
    assert "M_phonon" not in t.surviving_mechanisms


def test_7_no_validated_and_level2():
    assert not hasattr(Verdict, "VALIDATED")
    r = _rec("singlet")
    assert r.evidence_level <= 2
