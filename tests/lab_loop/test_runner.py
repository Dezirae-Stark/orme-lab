from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import run_avenue, AvenueResult


def _avenue():
    return Avenue(
        id="A1", tier=Tier.TIER1, description="Pd cluster vs dimer",
        targeted_hypothesis="H5",
        action=ActionSpec(
            elements=("Pd",), geometry_kinds=("dimer", "compact_cluster"),
            spin_labels=("high_spin",), applied_field_t=0.0, temperature_k=298.15,
            use_epw=False, use_em=False, coupling_channel=None,
        ),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="unit-test",
    )


def test_run_avenue_returns_records_and_metrics():
    res = run_avenue(_avenue())
    assert isinstance(res, AvenueResult)
    assert len(res.records) == 2  # 1 element x 2 geometries x 1 spin
    for m in ("max_sc_plausibility", "max_coupling", "n_survivors"):
        assert m in res.metrics


def test_run_avenue_is_deterministic():
    a = run_avenue(_avenue())
    b = run_avenue(_avenue())
    assert a.metrics == b.metrics


def test_metrics_reflect_screen_output():
    res = run_avenue(_avenue())
    couplings = [r.coupling for r in res.records]
    assert res.metrics["max_coupling"] == max(couplings)
    assert res.metrics["n_survivors"] == float(sum(1 for r in res.records if not r.ruled_out))


def test_exposed_screen_metrics_present_and_faithful():
    # The real screen quantities are exposed so falsifiers can test the
    # anisotropy/stability/carrier/isolation hypotheses faithfully.
    res = run_avenue(_avenue())
    for k in ("max_anisotropy", "max_structural_stability",
              "max_carrier_proxy", "n_isolated"):
        assert k in res.metrics
    assert res.metrics["max_anisotropy"] == max(r.anisotropy for r in res.records)
    assert res.metrics["max_structural_stability"] == max(
        r.structural_stability for r in res.records)
    assert res.metrics["max_carrier_proxy"] == max(r.carrier_proxy for r in res.records)
    assert res.metrics["n_isolated"] == float(sum(1 for r in res.records if r.isolated))


def test_every_metric_key_is_a_valid_falsification_metric():
    # Every metric the runner emits must be a declared, fireable-checkable range,
    # so a generator can falsify against any of them without a KeyError.
    from orme_lab.lab_loop.avenue import METRIC_RANGES
    res = run_avenue(_avenue())
    for k in res.metrics:
        assert k in METRIC_RANGES
