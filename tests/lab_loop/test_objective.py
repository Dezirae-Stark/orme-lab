from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import ObjectiveWeights
from orme_lab.lab_loop.objective import score_avenue, action_key


def _av(hyp="H5", predictors=("sc_lambda",), elements=("Pd",)):
    return Avenue(
        id="A", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=predictors, provenance="t",
    )


W = ObjectiveWeights()


def test_open_target_outscores_closed_target():
    open_hi = score_avenue(_av(hyp="H5"), frozenset({"H5"}), frozenset(), W)
    closed = score_avenue(_av(hyp="H5"), frozenset(), frozenset(), W)
    assert open_hi > closed


def test_tautological_avenue_scores_zero():
    taut = _av(predictors=("coupling",))
    assert score_avenue(taut, frozenset({"H5"}), frozenset(), W) == 0.0


def test_unseen_action_outscores_seen_action():
    av = _av(elements=("Pd",))
    seen = frozenset({action_key(av)})
    fresh = score_avenue(_av(elements=("Ir",)), frozenset({"H5"}), seen, W)
    stale = score_avenue(av, frozenset({"H5"}), seen, W)
    assert fresh > stale


def test_score_ignores_candidate_strength_tag():
    # score_avenue takes no candidate-strength input at all; two identical avenues
    # score identically regardless of any (absent) strength notion.
    a = score_avenue(_av(), frozenset({"H5"}), frozenset(), W)
    b = score_avenue(_av(), frozenset({"H5"}), frozenset(), W)
    assert a == b
