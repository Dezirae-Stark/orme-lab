"""Autonomous lab-scientist loop (see docs/superpowers/specs/2026-07-04-autonomous-lab-loop-design.md)."""

from .avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, MechanismProposal
from .ledger import Ledger, HYPOTHESES
from .loop import AvenueGenerator, HeuristicGenerator, LoopReport, run_loop

__all__ = [
    "Avenue", "ActionSpec", "Tier", "FalsificationCondition", "Comparator",
    "MechanismProposal", "Ledger", "HYPOTHESES", "AvenueGenerator",
    "HeuristicGenerator", "LoopReport", "run_loop",
]
