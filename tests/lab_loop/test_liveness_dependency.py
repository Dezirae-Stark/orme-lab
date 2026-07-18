import pytest
from orme_lab.lab_loop.hypotheses import HYPOTHESES, LIVENESS_DEPENDENCIES, validate_liveness
from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, is_independent
from orme_lab.lab_loop.avenue import METRIC_RANGES, FalsificationCondition, Comparator


def test_h7_split_present_and_h7_gone():
    assert "H7-singlet" in HYPOTHESES and "H7-triplet" in HYPOTHESES
    assert "H16-drive-triplet" in HYPOTHESES
    assert "H7" not in HYPOTHESES


def test_drive_depends_on_h7_triplet():
    assert LIVENESS_DEPENDENCIES["H16-drive-triplet"] == "H7-triplet"


def test_liveness_dead_parent_blocks():
    open_h = frozenset(HYPOTHESES) - {"H7-triplet"}
    ok, reason = validate_liveness("H16-drive-triplet", open_h)
    assert not ok and "H7-triplet" in reason
    # a hypothesis with no dependency always passes
    assert validate_liveness("H7-singlet", open_h)[0]


def test_new_offgate_and_metrics_exist():
    assert "field_response_ratio" in OFF_GATE_INVARIANTS
    assert "em_drive_response" in OFF_GATE_INVARIANTS
    assert "max_field_response_ratio" in METRIC_RANGES
    assert "max_em_drive_response" in METRIC_RANGES
    # both new signals are off-gate (pass the anti-tautology gate)
    assert is_independent(("field_response_ratio",))
    assert is_independent(("em_drive_response",))
    # the opposite falsifiers are fireable
    assert FalsificationCondition("max_field_response_ratio", Comparator.GT, 1.0).fireable()
    assert FalsificationCondition("max_em_drive_response", Comparator.LT, 0.1).fireable()


# tests/test_liveness_dependency.py (continued) — build a minimal AvenueResult
from orme_lab.lab_loop.triage import triage, Verdict
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier


def _drive_avenue():
    return Avenue(
        id="a1", tier=Tier.TIER1, description="drive", targeted_hypothesis="H16-drive-triplet",
        action=ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, False, True, None, "triplet"),
        falsification=FalsificationCondition("max_em_drive_response", Comparator.LT, 0.1),
        predictor_invariants=("em_drive_response",), provenance="test")


def test_triage_inconclusive_when_parent_dead():
    res = AvenueResult(avenue=_drive_avenue(), records=(), metrics={"max_em_drive_response": 0.5})
    open_h = frozenset(HYPOTHESES) - {"H7-triplet"}   # parent killed
    assert triage(res, open_h).verdict == Verdict.INCONCLUSIVE
