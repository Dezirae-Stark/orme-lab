"""Judge an avenue result. Honesty is enforced by the closed ``Verdict`` enum:
there is no VALIDATED member, so no code path can claim validation. A killed
hypothesis is a SUCCESS, not a failure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .closure import is_independent
from .runner import AvenueResult


class Verdict(Enum):
    """The only verdicts the loop can reach. Deliberately no VALIDATED/CONFIRMED."""

    KILLED_HYPOTHESIS = "killed_hypothesis"  # falsification fired — progress
    SURVIVED = "survived"                    # not killed this round
    TAUTOLOGICAL = "tautological"            # predictors re-derivable from the gate
    INCONCLUSIVE = "inconclusive"            # nothing decidable (e.g. target closed)


@dataclass(frozen=True)
class TriageOutcome:
    verdict: Verdict
    decisiveness: float
    killed_hypothesis: str | None


def triage(result: AvenueResult, open_hypotheses: frozenset[str]) -> TriageOutcome:
    av = result.avenue

    # 1. Tautology gate — before anything else.
    if not is_independent(av.predictor_invariants):
        return TriageOutcome(Verdict.TAUTOLOGICAL, 0.0, None)

    # 2. Can this avenue decide anything? Its target must still be open.
    if av.targeted_hypothesis not in open_hypotheses:
        return TriageOutcome(Verdict.INCONCLUSIVE, 0.0, None)

    # 3. Did the falsification condition fire? A fire kills the hypothesis.
    if av.falsification.evaluate(result.metrics):
        return TriageOutcome(Verdict.KILLED_HYPOTHESIS, 1.0, av.targeted_hypothesis)

    return TriageOutcome(Verdict.SURVIVED, 0.0, None)
