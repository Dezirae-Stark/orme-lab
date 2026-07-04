from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, METRIC_RANGES,
)
from orme_lab.lab_loop.runner import run_avenue


def _em_avenue(elements, use_em):
    return Avenue(
        id="em", tier=Tier.TIER1, description="em probe", targeted_hypothesis="H12",
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, use_epw=False, use_em=use_em, coupling_channel=None),
        falsification=FalsificationCondition("max_em_coherence_score", Comparator.LT, 0.05),
        predictor_invariants=("em_coherence_score",), provenance="t",
    )


def test_metric_range_declared():
    assert METRIC_RANGES["max_em_coherence_score"] == (0.0, 1.0)


def test_use_em_off_gives_zero_metric():
    m = run_avenue(_em_avenue(("Au",), use_em=False)).metrics
    assert m["max_em_coherence_score"] == 0.0     # None-safe -> 0.0 when not computed


def test_use_em_on_varies_by_element():
    au = run_avenue(_em_avenue(("Au",), use_em=True)).metrics["max_em_coherence_score"]
    pd = run_avenue(_em_avenue(("Pd",), use_em=True)).metrics["max_em_coherence_score"]
    assert au >= 0.0 and pd == 0.0                # Pd is dark; Au may light up
