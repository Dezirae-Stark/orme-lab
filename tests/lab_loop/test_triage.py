from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.triage import Verdict, triage


def _avenue(predictors, metric="max_coupling", comp=Comparator.LT, thr=0.2, hyp="H5"):
    return Avenue(
        id="A1", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(("Pd",), ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


def _result(avenue, metrics):
    return AvenueResult(avenue=avenue, records=(), metrics=metrics)


def test_tautological_when_predictors_only_in_closure():
    av = _avenue(predictors=("coupling", "carrier_proxy"))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.TAUTOLOGICAL


def test_killed_hypothesis_is_success_when_condition_fires():
    # coupling stays below 0.2 -> falsification fires -> H5 killed.
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.KILLED_HYPOTHESIS
    assert out.killed_hypothesis == "H5"
    assert out.decisiveness > 0.0


def test_survived_when_condition_does_not_fire():
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.9}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.SURVIVED


def test_inconclusive_when_targeted_hypothesis_already_closed():
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset())
    assert out.verdict is Verdict.INCONCLUSIVE


def test_verdict_vocabulary_has_no_validated_member():
    names = {v.name for v in Verdict}
    assert names == {"KILLED_HYPOTHESIS", "SURVIVED", "TAUTOLOGICAL", "INCONCLUSIVE"}
    for forbidden in ("VALIDATED", "CONFIRMED", "SUPERCONDUCTING", "PROVEN"):
        assert forbidden not in names
