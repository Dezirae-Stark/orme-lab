"""Regression tests for the PR #25 review findings (Codex):
1. avenue de-dup must include pairing_symmetry (else singlet/triplet collide).
2. an unmeasured discriminator (None) must not fire a falsifier / must read INCONCLUSIVE,
   never collapse to 0.0 and kill a hypothesis having measured nothing.
3. (observables recompute after the Pauli cap is covered in test_pairing_symmetry via plaus.)
"""
import pytest

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.lab_loop.objective import action_key
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator
from orme_lab.lab_loop.runner import _metrics, validate_runnable, AvenueResult
from orme_lab.lab_loop.triage import triage, Verdict
from orme_lab.lab_loop.hypotheses import HYPOTHESES


def _action(sym, use_epw=True, use_em=True):
    return ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, use_epw, use_em, None, sym)


def _av(target, metric, comp, thr, invariants, sym="triplet", use_epw=True, use_em=True):
    return Avenue("a", Tier.TIER1, "d", target, _action(sym, use_epw, use_em),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


def test_action_key_includes_pairing_symmetry():
    s = _av("H7-singlet", "max_field_response_ratio", Comparator.GT, 1.0, ("field_response_ratio",), "singlet")
    t = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",), "triplet")
    # singlet and triplet over the same grid MUST be distinct actions (independently testable)
    assert action_key(s) != action_key(t)


def test_unmeasured_discriminator_is_none_not_zero():
    el = get_element("Ir")
    rec = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin", high_spin_state(el), DEFAULT_CONFIG)
    assert rec.field_response_ratio is None and rec.em_drive_response is None
    m = _metrics((rec,))
    assert m["max_field_response_ratio"] is None
    assert m["max_em_drive_response"] is None


def test_triage_inconclusive_when_discriminator_unmeasured():
    av = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",), "triplet")
    res = AvenueResult(av, (), {"max_field_response_ratio": None})
    # old bug: 0.0 <= 1.0 fires -> KILLED with no measurement. Now: INCONCLUSIVE.
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.INCONCLUSIVE


def test_falsification_none_value_does_not_fire():
    fc = FalsificationCondition("max_field_response_ratio", Comparator.LE, 1.0)
    assert fc.evaluate({"max_field_response_ratio": None}) is False


def test_validate_runnable_requires_data_source():
    no_epw = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0,
                 ("field_response_ratio",), "triplet", use_epw=False)
    ok, reason = validate_runnable(no_epw)
    assert not ok and "use_epw" in reason
    no_em = _av("H16-drive-triplet", "max_em_drive_response", Comparator.LT, 0.1,
                ("em_drive_response",), "triplet", use_em=False)
    ok2, reason2 = validate_runnable(no_em)
    assert not ok2 and "use_em" in reason2


def test_measured_discriminator_still_fires():
    # sanity: a genuine measurement still kills as before
    av = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",), "triplet")
    res = AvenueResult(av, (), {"max_field_response_ratio": 0.7})   # measured suppression
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS
