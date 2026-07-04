"""Append-only deterministic memory of the loop: what was run, what it decided,
which hypotheses are still open, and the tier-3 quarantine queue. Ordering is by
a monotonic sequence index — never a wall clock — so a fixed avenue stream yields
byte-identical JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .avenue import Avenue, MechanismProposal
from .hypotheses import HYPOTHESES
from .objective import action_key
from .triage import TriageOutcome, Verdict


@dataclass(frozen=True)
class LedgerRecord:
    seq: int
    avenue_id: str
    tier: int
    targeted_hypothesis: str
    verdict: str
    decisiveness: float
    killed_hypothesis: str | None
    metrics: dict
    predictor_invariants: tuple[str, ...]

    def to_json(self) -> dict:
        d = dict(self.__dict__)
        d["predictor_invariants"] = list(self.predictor_invariants)
        return d


class Ledger:
    def __init__(self) -> None:
        self.records: list[LedgerRecord] = []
        self.proposals: list[MechanismProposal] = []
        self._seen: set[tuple] = set()
        self._killed: set[str] = set()
        self._seq = 0

    @property
    def open_hypotheses(self) -> frozenset[str]:
        return frozenset(h for h in HYPOTHESES if h not in self._killed)

    @property
    def seen_actions(self) -> frozenset[tuple]:
        return frozenset(self._seen)

    def is_seen(self, avenue: Avenue) -> bool:
        return action_key(avenue) in self._seen

    def record(self, avenue: Avenue, outcome: TriageOutcome, metrics: dict) -> LedgerRecord | None:
        """Append one avenue's outcome. Returns None (no-op) if the action was
        already seen (dedup). Retires a hypothesis on a KILLED verdict."""
        if self.is_seen(avenue):
            return None
        self._seen.add(action_key(avenue))
        rec = LedgerRecord(
            seq=self._seq, avenue_id=avenue.id, tier=int(avenue.tier),
            targeted_hypothesis=avenue.targeted_hypothesis, verdict=outcome.verdict.value,
            decisiveness=outcome.decisiveness, killed_hypothesis=outcome.killed_hypothesis,
            metrics=dict(metrics), predictor_invariants=tuple(avenue.predictor_invariants),
        )
        self._seq += 1
        self.records.append(rec)
        if outcome.verdict is Verdict.KILLED_HYPOTHESIS and outcome.killed_hypothesis:
            self._killed.add(outcome.killed_hypothesis)
        return rec

    def quarantine(self, proposal: MechanismProposal) -> None:
        self.proposals.append(proposal)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(r.to_json(), sort_keys=True) for r in self.records)
