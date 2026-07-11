"""Two-branch verdict: Branch A (conventional superconductivity) and Branch B
(Hudson optical coherence) reported as INDEPENDENT results.

The branches must not be merged prematurely. A material can be a room-temperature
polariton condensate (Branch B) without being an electrical superconductor (Branch A),
and vice versa. This object reports each branch's verdict separately; the full
"Hudson-type optical superconductive phase" is the conjunction at the TOP only, and
is emitted as a PREDICTION (``hudson_phase_predicted``), never as a crediting verdict
and never as a blended numeric score. Branch B never sets Branch A's crediting and
vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hudson_optical import HudsonClaim, HudsonOpticalResult
from .pipeline import CandidateRecord


@dataclass(frozen=True)
class BranchVerdict:
    element: str
    branch_a_credited: bool               # SC lead credited (identity ∧ gate ∧ mechanism)
    branch_b_levels: frozenset            # frozenset[HudsonClaim] independently supported
    hudson_phase_predicted: bool          # claim level 8 — a top-level PREDICTION only

    def explain(self) -> str:
        b = ", ".join(str(int(c)) for c in sorted(self.branch_b_levels)) or "none"
        return (
            f"{self.element}: Branch A (superconductivity) credited={self.branch_a_credited}; "
            f"Branch B (Hudson optical) supported levels {{{b}}}. The two branches are "
            f"INDEPENDENT — neither rescues the other. Full Hudson optical superconductive "
            f"phase (level 8) predicted={self.hudson_phase_predicted} (a laboratory "
            f"prediction, not a crediting verdict)."
        )


def combine_branches(record: CandidateRecord, hudson: HudsonOpticalResult) -> BranchVerdict:
    """Assemble the independent two-branch verdict. Reads each branch's own verdict;
    performs no cross-branch arithmetic."""
    return BranchVerdict(
        element=record.element,
        branch_a_credited=record.credited_sc_lead,
        branch_b_levels=hudson.supported,
        hudson_phase_predicted=HudsonClaim.HUDSON_PHASE in hudson.supported,
    )
