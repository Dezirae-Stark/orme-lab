"""Hudson Claim Ledger — falsify-first assessment of Hudson's eight ORME claims.

A REPORTING layer above the per-candidate pipeline (not a gate inside the SC AND-gate or its
closure oracle; distinct from lab_loop/ledger.py, the experiment ledger). Objective: determine
whether a reproducible material state exists that satisfies Hudson's stated properties —
attacking the ordinary explanation of each claim first. Extraordinary claims are default-blocked;
the ledger never self-asserts the Hudson mechanism from simulation and never emits "VALIDATED".
See docs/hudson_claim_ledger.md and the design spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class HudsonClaimId(str, Enum):
    HC_01 = "HC-01"; HC_02 = "HC-02"; HC_03 = "HC-03"; HC_04 = "HC-04"
    HC_05 = "HC-05"; HC_06 = "HC-06"; HC_07 = "HC-07"; HC_08 = "HC-08"


class ClaimStatus(IntEnum):
    """Per-claim evidentiary status. Ordered so max/min roll-ups are numeric. A 'lead' is
    promising evidence, NOT support; simulation caps at LEAD."""
    CANDIDATE = 0
    LEAD = 1
    ANOMALOUS = 2
    PROVISIONALLY_SUPPORTED = 3
    SUPPORTED = 4
    INDEPENDENTLY_REPLICATED = 5


class Route(str, Enum):
    CONVENTIONAL = "conventional"   # Branch A: R->0, Meissner flux exclusion
    OPTICAL = "optical"             # Branch B: persistent ring-down, dM/dP tracking resonance
    NONE = "none"


@dataclass(frozen=True)
class ClaimRecord:
    id: HudsonClaimId
    claim_text: str
    required_observation: str
    mundane_alternative: str
    status: ClaimStatus
    evidence_level: int
    route: Route = Route.NONE
    computable: bool = True
    decisive_experiment: object = None   # validator.ValidationSuite | None (procedural claims)
    note: str = ""


@dataclass(frozen=True)
class ReplicationEvidence:
    """External replication metadata. Default-blocked: absent this record, G_replication is False."""
    n_batches: int
    n_labs: int
    preregistered_thresholds: bool
    raw_data_retained: bool
    blinded_controls_correct: bool


@dataclass(frozen=True)
class MeasuredEvidence:
    """Researcher-supplied measured results for ONE lineage. All default False/None -> the
    default-blocked simulation path (gates cannot climb past LEAD)."""
    # conventional superconductivity route
    zero_resistance: bool = False
    flux_exclusion: bool = False
    critical_behavior: bool = False
    artifact_excluded: bool = False
    # optical route: a HudsonOpticalResult computed WITH the researcher's measured inputs
    optical_result: object = None       # hudson_optical.HudsonOpticalResult | None
    # claim-specific measured confirmations (mundane alternative excluded)
    hc01_nonmetallic_confirmed: bool = False
    hc03_orbital_confirmed: bool = False
    hc04_isotope_confirmed: bool = False
    hc05_recovery_confirmed: bool = False
    hc08_mass_confirmed: bool = False
    replication: ReplicationEvidence | None = None
