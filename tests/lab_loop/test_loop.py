from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop, LoopReport


def _av(aid, tier=Tier.TIER1, predictors=("sc_lambda",), hyp="H5",
        metric="max_coupling", comp=Comparator.LT, thr=0.2, elements=("Pd",)):
    return Avenue(
        id=aid, tier=tier, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


class ScriptedGenerator:
    """Emits a fixed avenue list, then nothing (drives deterministic tests)."""

    def __init__(self, avenues):
        self._avenues = list(avenues)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avenues = self._avenues[:k], self._avenues[k:]
        return batch


def _stub_screen(**kwargs):
    # A minimal fake screen: one record whose coupling is low (kills H5).
    from orme_lab.pipeline import run_screen
    return run_screen(**kwargs)  # real screen is fine & deterministic for these tests


def test_loop_terminates_at_budget():
    gen = ScriptedGenerator([_av(f"A{i}", elements=(e,))
                             for i, e in enumerate(("Pd", "Ir", "Rh", "Os", "Pt"))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=5,
                                               convergence_rounds=99))
    assert isinstance(rep, LoopReport)
    assert len(rep.ledger.records) <= 3


def test_tier3_avenue_is_quarantined_not_run():
    gen = ScriptedGenerator([_av("T3", tier=Tier.TIER3)])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=5, proposals_per_round=5,
                                               convergence_rounds=1))
    assert len(rep.ledger.proposals) == 1
    assert all(r.tier != 3 for r in rep.ledger.records)


def test_tautological_only_generator_yields_zero_findings():
    # Adversarial whole-loop null: every avenue is tautological -> no records, honest digest.
    gen = ScriptedGenerator([_av(f"C{i}", predictors=("coupling",), elements=(e,))
                             for i, e in enumerate(("Pd", "Ir", "Rh"))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=1))
    kills = [r for r in rep.ledger.records if r.verdict == Verdict.KILLED_HYPOTHESIS.value]
    assert kills == []
    assert "no independent avenue" in rep.digest.lower()


def test_unfalsifiable_avenue_is_dropped_before_running():
    # threshold 0.0 for max_coupling can never fire -> not fireable -> dropped.
    gen = ScriptedGenerator([_av("U1", thr=0.0)])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=5, proposals_per_round=5,
                                               convergence_rounds=1))
    assert len(rep.ledger.records) == 0


def test_digest_never_claims_validation():
    gen = ScriptedGenerator([_av("A1")])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=1, proposals_per_round=1,
                                               convergence_rounds=1))
    low = rep.digest.lower()
    for word in ("validated", "confirmed superconductor", "proven superconductor"):
        assert word not in low
