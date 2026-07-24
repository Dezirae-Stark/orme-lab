"""Off-gate discriminator + anti-tautology + against-triplet falsification for
``orbital_order_param``.

Mirrors the ``field_response_ratio`` off-gate wiring (tests/test_pairing_acceptance.py):
orbital_order_param is a DIFFERENT contraction of the d-occupations than the gate's
own ``anisotropy`` scalar, so it must sit outside GATE_INPUT_CLOSURE and pass the
anti-tautology gate. It is used only as an against-triplet falsifier (kills
H7-triplet on high orbital order), never as positive SC/pairing evidence.
"""
import pytest

from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, METRIC_RANGES,
)
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.triage import Verdict, triage
from orme_lab.lab_loop.hypotheses import HYPOTHESES


def _av(target, metric, comp, thr, invariants, symmetry="undetermined"):
    return Avenue("a", Tier.TIER1, "d", target,
                  ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                             False, True, None, symmetry),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


def test_orbital_order_is_off_gate():
    from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, GATE_INPUT_CLOSURE, is_independent
    assert "orbital_order_param" in OFF_GATE_INVARIANTS
    assert "orbital_order_param" not in GATE_INPUT_CLOSURE
    assert is_independent(("orbital_order_param",))


def test_metric_and_ranges_present():
    assert METRIC_RANGES["max_orbital_order"] == (0.0, 1.0)


def test_high_orbital_order_kills_triplet():
    # an H7-triplet avenue with falsifier max_orbital_order > 0.5 fires on a high-P run
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    res = AvenueResult(av, (), {"max_orbital_order": 0.8})
    out = triage(res, frozenset(HYPOTHESES))
    assert out.verdict == Verdict.KILLED_HYPOTHESIS
    assert out.killed_hypothesis == "H7-triplet"


def test_low_orbital_order_survives_triplet():
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    res = AvenueResult(av, (), {"max_orbital_order": 0.2})
    out = triage(res, frozenset(HYPOTHESES))
    assert out.verdict == Verdict.SURVIVED


def test_unmeasured_orbital_order_never_fires():
    # None (not measured) must never fire the falsifier -- absent evidence, not
    # evidence of absence -- and reads as INCONCLUSIVE (not SURVIVED, which would
    # overclaim that something was actually tested).
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    res = AvenueResult(av, (), {"max_orbital_order": None})
    out = triage(res, frozenset(HYPOTHESES))
    assert out.verdict == Verdict.INCONCLUSIVE
    assert out.killed_hypothesis is None


def test_anti_tautology_moves_pairing_not_from_gate_inputs():
    # Two candidates with identical gate scalars (anisotropy, etc.) but different
    # orbital_order_param must be decidable by orbital_order_param alone -- i.e. the
    # off-gate predictor set, not the gate's own inputs, drives the verdict.
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    high = AvenueResult(av, (), {"max_orbital_order": 0.9})
    low = AvenueResult(av, (), {"max_orbital_order": 0.1})
    assert triage(high, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(low, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED
    # And a predictor set drawn only from the gate's own closure remains tautological.
    from orme_lab.lab_loop.closure import is_independent
    assert is_independent(("anisotropy",)) is False


def test_eg_t2g_is_off_gate():
    from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, GATE_INPUT_CLOSURE, is_independent
    assert "eg_t2g_imbalance" in OFF_GATE_INVARIANTS
    assert "eg_t2g_imbalance" not in GATE_INPUT_CLOSURE
    assert is_independent(("eg_t2g_imbalance",))


def test_eg_t2g_metric_range_and_guard():
    from orme_lab.lab_loop.avenue import METRIC_RANGES, FalsificationCondition, Comparator
    assert METRIC_RANGES["max_eg_t2g_imbalance"] == (0.0, 1.0)
    assert FalsificationCondition("max_eg_t2g_imbalance", Comparator.GT, 0.5).fireable()


def test_orbital_order_falsifier_requires_compute_flag():
    from orme_lab.lab_loop.runner import validate_runnable
    action_no_flag = ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                                 False, True, None, "undetermined", compute_orbital_order=False)
    av = Avenue("a", Tier.TIER1, "d", "H7-triplet", action_no_flag,
                FalsificationCondition("max_orbital_order", Comparator.GT, 0.5, ),
                ("orbital_order_param",), "test")
    ok, reason = validate_runnable(av)
    assert ok is False
    assert "compute_orbital_order" in reason

    action_flag = ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                              False, True, None, "undetermined", compute_orbital_order=True)
    av2 = Avenue("a", Tier.TIER1, "d", "H7-triplet", action_flag,
                 FalsificationCondition("max_orbital_order", Comparator.GT, 0.5),
                 ("orbital_order_param",), "test")
    ok2, reason2 = validate_runnable(av2)
    assert ok2 is True


def _av(target, metric, comp, thr, invariants):
    from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator
    action = ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                        False, False, None, "undetermined", compute_orbital_order=True)
    return Avenue("a", Tier.TIER1, "d", target, action,
                  FalsificationCondition(metric, comp, thr), invariants, "SPECULATIVE eg-t2g")


def test_high_eg_t2g_kills_triplet():
    from orme_lab.lab_loop.runner import AvenueResult
    from orme_lab.lab_loop.triage import triage, Verdict
    from orme_lab.lab_loop.hypotheses import HYPOTHESES
    from orme_lab.lab_loop.avenue import Comparator
    av = _av("H7-triplet", "max_eg_t2g_imbalance", Comparator.GT, 0.5, ("eg_t2g_imbalance",))
    hi = AvenueResult(av, (), {"max_eg_t2g_imbalance": 0.8})
    lo = AvenueResult(av, (), {"max_eg_t2g_imbalance": 0.2})
    none = AvenueResult(av, (), {"max_eg_t2g_imbalance": None})
    assert triage(hi, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(lo, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED
    assert triage(none, frozenset(HYPOTHESES)).verdict == Verdict.INCONCLUSIVE  # never fires on absent


def test_eg_t2g_anti_tautology_distinct_from_gate():
    # eg-t2g is now OUT of the gate: two occupations with the SAME gate anisotropy (both cubic ->
    # quadrupole 0) but DIFFERENT eg-t2g -> distinct off-gate value not derivable from the gate.
    from orme_lab.orbital_order import quadrupole_anisotropy, eg_t2g_imbalance
    a = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)   # eg > t2g
    b = (1.4823, 1.4823, 1.4823, 1.4823, 1.4823)   # equal fill
    assert quadrupole_anisotropy(a) == pytest.approx(quadrupole_anisotropy(b), abs=1e-9)  # same gate
    assert eg_t2g_imbalance(a) != pytest.approx(eg_t2g_imbalance(b))                        # different off-gate


def test_speculative_disclosure_present():
    import orme_lab.orbital_order as oo
    doc = oo.eg_t2g_imbalance.__doc__
    assert "SPECULATIVE" in doc.upper()
    assert "Cooper" in doc  # the ionic-vs-Cooper disambiguation
