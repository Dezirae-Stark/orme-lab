from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _h12(aid, elements):
    # H12 avenue: predictor is the off-gate EM signal -> non-tautological.
    # Falsifier fires (max_em_coherence_score < 0.05) when the EM channel is dark.
    return Avenue(
        id=aid, tier=Tier.TIER1, description="H12 EM coherence probe",
        targeted_hypothesis="H12",
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, use_epw=False, use_em=True, coupling_channel=None),
        falsification=FalsificationCondition("max_em_coherence_score", Comparator.LT, 0.05),
        predictor_invariants=("em_coherence_score",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_h12_predictor_is_not_tautological():
    # A Pd-only (dark) H12 avenue is judged on the merits, not dropped as tautological.
    rep = run_loop(OneShot([_h12("H12-pd", ("Pd",))]),
                   loop_config=LoopConfig(max_avenues=2, proposals_per_round=2,
                                          convergence_rounds=1))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts.get("H12-pd") != Verdict.TAUTOLOGICAL.value


def test_h12_kills_on_dark_panel_and_the_signal_is_real():
    # Pd is EM-dark -> max_em_coherence_score = 0.0 < 0.05 -> falsifier FIRES -> H12 killed.
    rep = run_loop(OneShot([_h12("H12-pd", ("Pd",))]),
                   loop_config=LoopConfig(max_avenues=2, proposals_per_round=2,
                                          convergence_rounds=1))
    rec = {r.avenue_id: r for r in rep.ledger.records}["H12-pd"]
    assert rec.verdict == Verdict.KILLED_HYPOTHESIS.value
    assert rec.metrics["max_em_coherence_score"] == 0.0
