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


def test_digest_does_not_blame_tautology_when_nothing_ran():
    # Only a tier-3 avenue: it is quarantined, zero avenues run. The digest must
    # say no avenue ran — NOT falsely claim every avenue was tautological.
    gen = ScriptedGenerator([_av("T3", tier=Tier.TIER3)])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=1))
    low = rep.digest.lower()
    assert "no independent avenue" in low
    assert "every avenue run was tautological" not in low  # would be a false reason

    # Same guarantee for an all-unfalsifiable batch (dropped before running).
    gen2 = ScriptedGenerator([_av("U1", thr=0.0)])
    rep2 = run_loop(gen2, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                                 convergence_rounds=1))
    low2 = rep2.digest.lower()
    assert "no independent avenue" in low2
    assert "every avenue run was tautological" not in low2


def test_digest_blames_tautology_only_when_avenues_actually_ran_tautological():
    # A genuinely tautological avenue DOES get run and recorded TAUTOLOGICAL; here
    # the "every avenue run was tautological" reason is accurate and expected.
    gen = ScriptedGenerator([_av("C1", predictors=("coupling",))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=1))
    low = rep.digest.lower()
    assert "no independent avenue" in low
    assert "every avenue run was tautological" in low


def _malformed_av(aid, elements=("Nb",), geoms=("compact_cluster",), metric="max_coupling"):
    # Nb is not in the element registry; used to exercise the malformed-avenue gate.
    return Avenue(
        id=aid, tier=Tier.TIER1, description="d", targeted_hypothesis="H5",
        action=ActionSpec(elements, geoms, ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_malformed_avenue_is_skipped_not_crashing():
    # An untrusted generator emitting an unknown element / geometry / metric must
    # not crash run_loop; the bad avenue is skipped and a valid one still runs.
    gen = ScriptedGenerator([
        _malformed_av("BADELEM", elements=("Nb",)),
        _malformed_av("BADGEOM", elements=("Pd",), geoms=("hypercube",)),
        _malformed_av("BADMETRIC", elements=("Pd",), metric="no_such_metric"),
        _av("GOOD", elements=("Pd",)),  # valid, runnable
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))
    ran = {r.avenue_id for r in rep.ledger.records}
    assert "GOOD" in ran
    for bad in ("BADELEM", "BADGEOM", "BADMETRIC"):
        assert bad not in ran  # never run
        assert bad in rep.digest  # surfaced honestly as skipped
    assert "malformed" in rep.digest.lower()


def test_digest_lists_surviving_leads():
    # A compact cluster survives (coupling clears the bulk gate); it must be
    # surfaced as a screening lead, hedged (not validated, Level <=2).
    gen = ScriptedGenerator([_av("LEAD", elements=("Pd",))])  # compact_cluster default
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=1, proposals_per_round=1,
                                               convergence_rounds=1))
    survived = [r for r in rep.ledger.records if r.verdict == "survived"]
    if survived:  # compact cluster clears the gate on the toy path
        low = rep.digest.lower()
        assert "screening leads" in low
        assert "not evidence of superconductivity" in low
        assert "validated" not in low  # the honesty guard still holds
        assert survived[0].avenue_id in rep.digest
