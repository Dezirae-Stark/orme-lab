from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.loop import run_loop


def _av(aid, hyp, elements):
    return Avenue(
        id=aid, tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("dimer",), ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_scope_mismatched_avenue_is_skipped_not_run():
    # H1-closed-shell mislabeled onto Ir (open-shell) -> skipped, never run, surfaced.
    gen = OneShot([_av("BAD", "H1-closed-shell", ("Ir",))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                               convergence_rounds=1))
    assert "BAD" not in {r.avenue_id for r in rep.ledger.records}
    assert "BAD" in rep.digest
    assert "scope mismatch" in rep.digest.lower()


def test_correctly_scoped_avenue_still_runs():
    # H1-closed-shell on Pd (closed-shell) -> passes scope -> runs.
    gen = OneShot([_av("GOOD", "H1-closed-shell", ("Pd",))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                               convergence_rounds=1))
    assert "GOOD" in {r.avenue_id for r in rep.ledger.records}
