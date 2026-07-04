import json
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, MechanismProposal,
)
from orme_lab.lab_loop.triage import Verdict, TriageOutcome
from orme_lab.lab_loop.ledger import Ledger, HYPOTHESES


def _av(aid="A1", hyp="H5", elements=("Pd",)):
    return Avenue(
        id=aid, tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_all_hypotheses_start_open():
    assert set(Ledger().open_hypotheses) == set(HYPOTHESES)


def test_kill_retires_hypothesis_from_open_set():
    led = Ledger()
    led.record(_av(hyp="H5"),
               TriageOutcome(Verdict.KILLED_HYPOTHESIS, 1.0, "H5"), {"max_coupling": 0.05})
    assert "H5" not in led.open_hypotheses


def test_seen_dedup_blocks_repeat_action():
    led = Ledger()
    av = _av()
    led.record(av, TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9})
    assert led.is_seen(av) is True
    assert led.record(av, TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9}) is None


def test_sequence_index_is_monotonic_no_clock():
    led = Ledger()
    r0 = led.record(_av(aid="A1", elements=("Pd",)),
                    TriageOutcome(Verdict.SURVIVED, 0.0, None), {})
    r1 = led.record(_av(aid="A2", elements=("Ir",)),
                    TriageOutcome(Verdict.SURVIVED, 0.0, None), {})
    assert (r0.seq, r1.seq) == (0, 1)


def test_to_jsonl_roundtrips_and_is_deterministic():
    led = Ledger()
    led.record(_av(), TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9})
    a = led.to_jsonl()
    lines = [ln for ln in a.splitlines() if ln.strip()]
    parsed = json.loads(lines[0])
    assert parsed["verdict"] == "survived"
    assert parsed["seq"] == 0


def test_quarantine_keeps_proposals_out_of_findings():
    led = Ledger()
    led.quarantine(MechanismProposal(id="M1", description="d", rationale="r", provenance="t"))
    assert len(led.proposals) == 1
    assert len(led.records) == 0
