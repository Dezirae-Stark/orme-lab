"""Acquisition function that ranks candidate avenues BEFORE they run.

A(avenue) = w_decisiveness * decisiveness_prior + w_coverage * coverage

decisiveness_prior : can this avenue kill something? 1.0 if its target is still
                     open (a dead hypothesis can't be re-killed), else 0.0.
coverage           : 1.0 if this action has not been run, else 0.0.

Candidate-strength is intentionally absent: nothing about how 'promising' a
candidate looks can raise an avenue's priority. Tautological avenues score 0.0.
"""

from __future__ import annotations

from .avenue import Avenue
from .closure import is_independent
from .config import ObjectiveWeights


def action_key(avenue: Avenue) -> tuple:
    """Hashable identity of an avenue's action, for the seen-set / coverage term."""
    a = avenue.action
    return (
        a.elements, a.geometry_kinds, a.spin_labels, a.applied_field_t,
        a.temperature_k, a.use_epw, a.use_em, a.coupling_channel,
    )


def score_avenue(
    avenue: Avenue,
    open_hypotheses: frozenset[str],
    seen_actions: frozenset[tuple],
    weights: ObjectiveWeights,
) -> float:
    if not is_independent(avenue.predictor_invariants):
        return 0.0
    decisiveness = 1.0 if avenue.targeted_hypothesis in open_hypotheses else 0.0
    coverage = 0.0 if action_key(avenue) in seen_actions else 1.0
    return weights.w_decisiveness * decisiveness + weights.w_coverage * coverage
