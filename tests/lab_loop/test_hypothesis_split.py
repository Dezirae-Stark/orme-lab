from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _h1(aid, hyp, elements):
    # Falsifier fires when anisotropy is absent (< 0.05): closed-shell fires, open-shell does not.
    return Avenue(
        id=aid, tier=Tier.TIER1, description="H1 anisotropy probe", targeted_hypothesis=hyp,
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


def test_scoped_variants_retire_independently():
    # THE FIX: closed-shell H1 is killed (Pd/Au/Ag anisotropy 0) while open-shell H1
    # SURVIVES (Ir/Os anisotropy > 0) in the SAME run -- neither reads inconclusive.
    gen = OneShot([
        _h1("closed", "H1-closed-shell", ("Pd", "Au", "Ag")),
        _h1("open", "H1-open-shell", ("Ir", "Os")),
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts["closed"] == Verdict.KILLED_HYPOTHESIS.value
    assert verdicts["open"] == Verdict.SURVIVED.value        # NOT inconclusive
    assert "H1-closed-shell" not in rep.ledger.open_hypotheses
    assert "H1-open-shell" in rep.ledger.open_hypotheses      # untouched by the other kill


def test_open_shell_not_globally_killed_by_closed_shell():
    # Order-independent: even if the closed-shell kill is processed first, the
    # open-shell claim stays open (they are separate registry entries).
    gen = OneShot([
        _h1("closed", "H1-closed-shell", ("Pd",)),
        _h1("open", "H1-open-shell", ("Ir",)),
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts["open"] == Verdict.SURVIVED.value
