"""The bounded orchestrator. Each round: the generator PROPOSES avenues; the
deterministic core drops the unfalsifiable and the already-seen, ranks the rest,
runs the top, triages, and records — retiring killed hypotheses. Tautological
avenues are NOT dropped pre-run: they rank last (score 0.0) and, if run, are
recorded as TAUTOLOGICAL by triage and never counted as a kill. Tier-3 avenues
are quarantined, never run. The loop halts and surfaces at any operator-reserved
boundary. It never claims validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..config import DEFAULT_CONFIG, LabConfig
from ..evidence import LAB_CEILING, badge
from ..pipeline import run_screen
from .avenue import Avenue, ActionSpec, Comparator, FalsificationCondition, MechanismProposal, Tier
from .config import DEFAULT_LOOP_CONFIG, LoopConfig
from .ledger import Ledger
from .objective import action_key, score_avenue
from .hypotheses import validate_scope
from .runner import run_avenue, validate_runnable
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


def _digest(ledger: Ledger, stopped_reason: str,
            skipped: list[tuple[str, str]] | None = None,
            epw_unavailable: list[str] | None = None,
            epw_failed: list[str] | None = None) -> str:
    skipped = skipped or []
    epw_unavailable = epw_unavailable or []
    epw_failed = epw_failed or []
    lines = [
        "# Autonomous lab-loop digest",
        "",
        f"_Stopped: {stopped_reason}. Evidence ceiling: {badge(LAB_CEILING)}._",
        "_Nothing here is confirmed. A surviving lead is a screening/triage signal,_",
        "_not evidence of superconductivity; independent verification requires physical Level 4-6._",
        "",
        "_H7 is split into H7-singlet/H7-triplet (opposite Pauli-limit field predictions);_",
        "_H16-drive-triplet (spin/magnetic AC-drive channel) is live only while H7-triplet is_",
        "_open. Decisive measurements: critical field vs the Pauli limit (1.86*Tc), and_",
        "_magnetic-drive response vs baseline._",
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

    # Screening leads: avenues NOT ruled out this run. A lead is Level <= 2 (a
    # simulation candidate), NOT a superconductor — it names what to measure next.
    survived = [r for r in ledger.records if r.verdict == Verdict.SURVIVED.value]
    if survived:
        lines.append("## Screening leads (NOT RULED OUT — Level <=2 triage signal, "
                     "not evidence of superconductivity)")
        for r in survived:
            lines.append(f"- {r.avenue_id} (targeted {r.targeted_hypothesis}) — "
                         f"worth real computation/measurement, not evidence of SC")
        lines.append("")
    tautological = [r for r in ledger.records
                    if r.verdict == Verdict.TAUTOLOGICAL.value]
    independent = [r for r in ledger.records
                   if r.verdict != Verdict.TAUTOLOGICAL.value]
    if not independent:
        if tautological:
            # Avenues were run, but every one was tautological.
            lines.append("No independent avenue found — every avenue run was "
                         "tautological (re-derivable from the AND-gate's own "
                         "inputs). No findings.")
        else:
            # No avenue was ever run (all quarantined, dropped as unfalsifiable,
            # or the generator proposed nothing). Do NOT blame tautology.
            lines.append("No independent avenue found — no avenue was run this "
                         "session (all proposals were quarantined, dropped as "
                         "unfalsifiable, or none were offered). No findings.")
    if ledger.proposals:
        lines.append("")
        lines.append("## Tier-3 mechanism proposals (QUARANTINED — pending "
                     "operator + red-team review, NOT findings)")
        for p in ledger.proposals:
            lines.append(f"- {p.id}: {p.description}")
    if skipped:
        lines.append("")
        lines.append("## Skipped (not run, not findings — malformed or scope-mismatched)")
        for aid, reason in skipped:
            lines.append(f"- {aid}: {reason}")
    if epw_unavailable:
        lines.append("")
        lines.append("## EPW requested but binaries unavailable (sc_* NOT computed)")
        for aid in epw_unavailable:
            lines.append(f"- {aid}: pw.x/ph.x/epw.x not present; no electron-phonon Tc")
    if epw_failed:
        lines.append("")
        lines.append("## EPW run FAILED (sc_* NOT computed)")
        for aid in epw_failed:
            lines.append(f"- {aid}: EPW attempted but errored; no electron-phonon Tc")
    return "\n".join(lines)


def run_loop(
    generator: AvenueGenerator,
    config: LabConfig = DEFAULT_CONFIG,
    loop_config: LoopConfig = DEFAULT_LOOP_CONFIG,
    backend=None,
    screen_fn=run_screen,
    epw_backend=None,
) -> LoopReport:
    ledger = Ledger()
    rounds = 0
    rounds_since_kill = 0
    stopped_reason = "budget reached"
    # Proposed-but-unrun runnable avenues persist across rounds so a generator
    # that emits a fixed batch once (ScriptedGenerator, HeuristicGenerator) still
    # gets every avenue processed, not just the top of round one.
    candidates_buffer: list[Avenue] = []
    # Dedup at the proposal boundary: a runnable avenue is buffered at most once
    # (by action identity), and a tier-3 avenue is quarantined at most once (by
    # id). Without this, a generator that re-proposes each round bloats the buffer
    # with duplicates (→ redundant screen runs) and re-quarantines the same
    # proposal repeatedly.
    buffered_keys: set = set()
    quarantined_ids: set = set()
    # Malformed avenues (unknown element/geometry/metric from an untrusted
    # generator) are skipped, never run, and surfaced in the digest — a bad
    # proposal can't crash the loop or discard the in-progress ledger.
    skipped: list[tuple[str, str]] = []
    skipped_ids: set = set()
    # EPW status tracking: avenues where EPW was requested but binaries unavailable,
    # and avenues where EPW run failed.
    epw_unavailable: list[str] = []
    epw_failed: list[str] = []

    while len(ledger.records) < loop_config.max_avenues:
        rounds += 1
        proposed = generator.propose(
            ledger.open_hypotheses, ledger.seen_actions, loop_config.proposals_per_round,
        )

        # Process newly proposed avenues even if the generator is now exhausted.
        if proposed:
            for av in proposed:
                if touches_reserved_boundary(av):
                    # Quarantine tier-3 (reserved boundary); never run. Dedup by id.
                    if av.id not in quarantined_ids:
                        quarantined_ids.add(av.id)
                        ledger.quarantine(MechanismProposal(
                            id=av.id, description=av.description,
                            rationale=f"tier-{int(av.tier)} avenue targeting {av.targeted_hypothesis}",
                            provenance=av.provenance,
                        ))
                    continue
                # Reject malformed avenues before they can raise deep in the run.
                ok, reason = validate_runnable(av)
                if not ok:
                    if av.id not in skipped_ids:
                        skipped_ids.add(av.id)
                        skipped.append((av.id, reason))
                    continue
                # Reject scope-mismatched avenues (mislabeled scoped hypothesis).
                ok_scope, scope_reason = validate_scope(av)
                if not ok_scope:
                    if av.id not in skipped_ids:
                        skipped_ids.add(av.id)
                        skipped.append((av.id, scope_reason))
                    continue
                # Drop unfalsifiable / already-run / already-buffered; buffer the rest.
                key = action_key(av)
                if (av.falsification.fireable() and not ledger.is_seen(av)
                        and key not in buffered_keys):
                    buffered_keys.add(key)
                    candidates_buffer.append(av)

        # If nothing is buffered, stop with the honest reason.
        if not candidates_buffer:
            if not proposed:
                stopped_reason = "generator exhausted"
            else:
                stopped_reason = "converged (no runnable avenues)"
            break

        # Rank and pick the best from the persistent buffer.
        candidates_buffer.sort(
            key=lambda av: (
                -score_avenue(av, ledger.open_hypotheses, ledger.seen_actions,
                              loop_config.weights),
                av.id,
            )
        )
        best = candidates_buffer.pop(0)

        result = run_avenue(best, config=config, backend=backend, screen_fn=screen_fn,
                            epw_backend=epw_backend)
        if result.epw_status == "unavailable" and best.id not in epw_unavailable:
            epw_unavailable.append(best.id)
        if result.epw_status == "failed" and best.id not in epw_failed:
            epw_failed.append(best.id)
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
                      digest=_digest(ledger, stopped_reason, skipped, epw_unavailable,
                                     epw_failed))


class HeuristicGenerator:
    """Deterministic offline generator: enumerates tier-1 coverage avenues over
    (element x geometry-kind), each targeting H5 with an off-gate predictor and a
    fireable falsification. Not creative — a floor so the loop runs with no LLM.
    The production generator is the orme-lab-scientist subagent."""

    _GEOMS = ("monomer", "dimer", "linear_chain", "compact_cluster")

    def __init__(self, elements: tuple[str, ...] = ("Pd", "Ir", "Rh", "Os", "Pt", "Au")):
        self._elements = elements

    def propose(self, open_hypotheses, seen_actions, k):
        from ..config import ModelThresholds
        thr = ModelThresholds().min_coupling_for_bulk
        out: list[Avenue] = []
        for el in self._elements:
            for geom in self._GEOMS:
                av = Avenue(
                    id=f"H-{el}-{geom}", tier=Tier.TIER1,
                    description=f"{el} {geom}: does coupling clear the bulk gate?",
                    targeted_hypothesis="H5",
                    action=ActionSpec(
                        elements=(el,), geometry_kinds=(geom,), spin_labels=("high_spin",),
                        applied_field_t=0.0, temperature_k=298.15,
                        use_epw=False, use_em=False, coupling_channel=None,
                    ),
                    falsification=FalsificationCondition(
                        "max_coupling",
                        Comparator.LT,
                        thr,
                    ),
                    predictor_invariants=("sc_lambda",), provenance="HeuristicGenerator",
                )
                # Skip avenues already run (seen_actions holds action_key tuples).
                # The loop dedups the rest; across rounds this advances through the
                # full (element x geometry) universe as run avenues become seen.
                if action_key(av) not in seen_actions:
                    out.append(av)
                if len(out) >= k:
                    return out
        return out
