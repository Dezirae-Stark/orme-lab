"""The bounded orchestrator. Each round: the generator PROPOSES avenues; the
deterministic core drops the unfalsifiable and the tautological, ranks the rest,
runs the top, triages, and records — retiring killed hypotheses. Tier-3 avenues
are quarantined, never run. The loop halts and surfaces at any operator-reserved
boundary. It never claims validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..config import DEFAULT_CONFIG, LabConfig
from ..evidence import LAB_CEILING, badge
from ..pipeline import run_screen
from .avenue import Avenue, MechanismProposal, Tier
from .config import DEFAULT_LOOP_CONFIG, LoopConfig
from .ledger import Ledger
from .objective import score_avenue
from .runner import run_avenue
from .triage import Verdict, triage


class AvenueGenerator(Protocol):
    """The creative seam. In production this is the orme-lab-scientist subagent,
    supplied by the harness; the package ships HeuristicGenerator for offline use."""

    def propose(self, open_hypotheses: frozenset[str], seen_actions: frozenset[tuple],
                k: int) -> list[Avenue]:
        ...


def touches_reserved_boundary(avenue: Avenue) -> bool:
    """Operator-reserved boundaries the loop must not auto-act on. Tier-3 is the
    code/mechanism boundary; other boundaries (classification, publication) are
    out of the in-sim action space entirely, so tier is the sole in-band signal."""
    return avenue.tier is Tier.TIER3


@dataclass(frozen=True)
class LoopReport:
    ledger: Ledger
    rounds: int
    stopped_reason: str
    digest: str


def _digest(ledger: Ledger, stopped_reason: str) -> str:
    lines = [
        "# Autonomous lab-loop digest",
        "",
        f"_Stopped: {stopped_reason}. Evidence ceiling: {badge(LAB_CEILING)}._",
        "_Nothing here is confirmed. A surviving lead is a screening/triage signal,_",
        "_not evidence of superconductivity; independent verification requires physical Level 4-6._",
        "",
    ]
    killed = [r for r in ledger.records if r.verdict == Verdict.KILLED_HYPOTHESIS.value]
    if killed:
        lines.append("## Hypotheses retired (killed in-sim)")
        for r in killed:
            lines.append(f"- {r.killed_hypothesis} — by avenue {r.avenue_id}")
    else:
        lines.append("## Hypotheses retired: none this run")
    lines.append("")
    independent = [r for r in ledger.records
                   if r.verdict != Verdict.TAUTOLOGICAL.value]
    if not independent:
        lines.append("No independent avenue found — every proposed avenue was "
                     "tautological (re-derivable from the AND-gate's own inputs). "
                     "No findings.")
    if ledger.proposals:
        lines.append("")
        lines.append("## Tier-3 mechanism proposals (QUARANTINED — pending "
                     "operator + red-team review, NOT findings)")
        for p in ledger.proposals:
            lines.append(f"- {p.id}: {p.description}")
    return "\n".join(lines)


def run_loop(
    generator: AvenueGenerator,
    config: LabConfig = DEFAULT_CONFIG,
    loop_config: LoopConfig = DEFAULT_LOOP_CONFIG,
    backend=None,
    screen_fn=run_screen,
) -> LoopReport:
    ledger = Ledger()
    rounds = 0
    rounds_since_kill = 0
    stopped_reason = "budget reached"

    while len(ledger.records) < loop_config.max_avenues:
        rounds += 1
        proposed = generator.propose(
            ledger.open_hypotheses, ledger.seen_actions, loop_config.proposals_per_round,
        )
        if not proposed:
            stopped_reason = "generator exhausted"
            break

        # Quarantine tier-3 (reserved boundary); never run.
        runnable: list[Avenue] = []
        for av in proposed:
            if touches_reserved_boundary(av):
                ledger.quarantine(MechanismProposal(
                    id=av.id, description=av.description,
                    rationale=f"tier-{int(av.tier)} avenue targeting {av.targeted_hypothesis}",
                    provenance=av.provenance,
                ))
            else:
                runnable.append(av)

        # Drop unfalsifiable and already-seen; rank the rest.
        candidates = [
            av for av in runnable
            if av.falsification.fireable() and not ledger.is_seen(av)
        ]
        if not candidates:
            rounds_since_kill += 1
            if rounds_since_kill >= loop_config.convergence_rounds:
                stopped_reason = "converged (no runnable avenues)"
                break
            continue

        candidates.sort(
            key=lambda av: (
                -score_avenue(av, ledger.open_hypotheses, ledger.seen_actions,
                              loop_config.weights),
                av.id,
            )
        )
        best = candidates[0]

        result = run_avenue(best, config=config, backend=backend, screen_fn=screen_fn)
        outcome = triage(result, ledger.open_hypotheses)
        ledger.record(best, outcome, result.metrics)

        if outcome.verdict is Verdict.KILLED_HYPOTHESIS:
            rounds_since_kill = 0
        else:
            rounds_since_kill += 1
        if rounds_since_kill >= loop_config.convergence_rounds:
            stopped_reason = "converged (no new kill)"
            break

    return LoopReport(ledger=ledger, rounds=rounds, stopped_reason=stopped_reason,
                      digest=_digest(ledger, stopped_reason))
