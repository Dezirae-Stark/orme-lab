# tests/lab_loop/test_integration.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _av(aid, tier=Tier.TIER1, predictors=("sc_lambda",), hyp="H5",
        metric="max_coupling", comp=Comparator.LT, thr=0.2, elements=("Pd",), geom="monomer"):
    return Avenue(
        id=aid, tier=tier, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, (geom,), ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


class ScriptedGenerator:
    def __init__(self, avenues):
        self._avenues = list(avenues)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avenues = self._avenues[:k], self._avenues[k:]
        return batch


def test_end_to_end_kill_quarantine_and_honest_digest():
    # A monomer (coupling ~0) kills H5; a tier-3 proposal is quarantined; a
    # tautological avenue produces no finding.
    gen = ScriptedGenerator([
        _av("KILL", elements=("Pd",), geom="monomer"),          # coupling < 0.2 -> kills H5
        _av("T3", tier=Tier.TIER3, elements=("Ir",)),           # quarantined
        _av("TAUT", predictors=("coupling",), elements=("Rh",)),# tautological
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))

    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts.get("KILL") == Verdict.KILLED_HYPOTHESIS.value
    assert "H5" not in rep.ledger.open_hypotheses
    assert any(p.id == "T3" for p in rep.ledger.proposals)
    assert verdicts.get("TAUT") == Verdict.TAUTOLOGICAL.value

    low = rep.digest.lower()
    assert "validated" not in low
    assert "h5" in low  # retired hypothesis surfaced


def test_full_suite_determinism_two_identical_runs():
    avenues = lambda: [_av(f"A{i}", elements=(e,), geom=g)
                       for i, (e, g) in enumerate(
                           [("Pd", "monomer"), ("Ir", "dimer"), ("Rh", "compact_cluster")])]
    r1 = run_loop(ScriptedGenerator(avenues()),
                  loop_config=LoopConfig(max_avenues=9, proposals_per_round=9, convergence_rounds=99))
    r2 = run_loop(ScriptedGenerator(avenues()),
                  loop_config=LoopConfig(max_avenues=9, proposals_per_round=9, convergence_rounds=99))
    assert r1.ledger.to_jsonl() == r2.ledger.to_jsonl()
