import pytest
from orme_lab.lab_loop.avenue import (
    Tier, Comparator, FalsificationCondition, ActionSpec, Avenue,
    MechanismProposal, METRIC_RANGES,
)


def _action():
    return ActionSpec(
        elements=("Pd",), geometry_kinds=("compact_cluster",), spin_labels=("high_spin",),
        applied_field_t=0.0, temperature_k=298.15, use_epw=False, use_em=False,
        coupling_channel=None,
    )


def test_fireable_true_when_threshold_inside_metric_range():
    # max_sc_plausibility ranges [0,1]; threshold 0.5 can be crossed both ways.
    fc = FalsificationCondition("max_sc_plausibility", Comparator.LT, 0.5)
    assert fc.fireable() is True


def test_fireable_false_when_threshold_outside_metric_range():
    # Nothing can be < 0.0, so "max_sc_plausibility < 0.0" can never fire.
    fc = FalsificationCondition("max_sc_plausibility", Comparator.LT, 0.0)
    assert fc.fireable() is False


def test_unknown_metric_rejected():
    with pytest.raises(ValueError):
        FalsificationCondition("no_such_metric", Comparator.LT, 0.5).fireable()


def test_avenue_is_frozen():
    av = Avenue(
        id="A1", tier=Tier.TIER1, description="probe Pd cluster",
        targeted_hypothesis="H5", action=_action(),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="unit-test",
    )
    with pytest.raises(Exception):
        av.id = "A2"  # type: ignore[misc]


def test_mechanism_proposal_default_status_is_pending_review():
    mp = MechanismProposal(id="M1", description="new granular network model",
                           rationale="tier-3", provenance="unit-test")
    assert mp.status == "pending operator + red-team review"


def test_metric_ranges_cover_expected_metrics():
    for m in ("max_sc_plausibility", "n_survivors", "max_coupling", "max_sc_tc_kelvin"):
        assert m in METRIC_RANGES
