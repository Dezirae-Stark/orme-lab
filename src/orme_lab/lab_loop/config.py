"""Loop budget and objective weights. Frozen so a run cannot mutate its own
knobs mid-loop (determinism)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ObjectiveWeights:
    """Weights for the avenue-selection acquisition function.

    ``w_decisiveness`` dominates: the loop pursues what would settle a question,
    with coverage only as a tiebreaker. Candidate-strength is deliberately NOT a
    weight — it can never raise an avenue's priority.
    """

    w_decisiveness: float = 1.0
    w_coverage: float = 0.15


@dataclass(frozen=True)
class LoopConfig:
    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)
    max_avenues: int = 20
    """Hard budget: stop after this many avenues are RUN (tier-3 quarantines and
    dropped tautologies do not count against it)."""
    proposals_per_round: int = 4
    convergence_rounds: int = 3
    """Stop early after this many consecutive rounds with no new hypothesis kill."""
    ledger_dir: str = "experiments/ledger"


DEFAULT_LOOP_CONFIG = LoopConfig()
