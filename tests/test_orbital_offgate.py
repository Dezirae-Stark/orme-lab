"""Off-gate discriminator + anti-tautology + against-triplet falsification for
``orbital_order_param``.

Mirrors the ``field_response_ratio`` off-gate wiring (tests/test_pairing_acceptance.py):
orbital_order_param is a DIFFERENT contraction of the d-occupations than the gate's
own ``anisotropy`` scalar, so it must sit outside GATE_INPUT_CLOSURE and pass the
anti-tautology gate. It is used only as an against-triplet falsifier (kills
H7-triplet on high orbital order), never as positive SC/pairing evidence.
"""
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
