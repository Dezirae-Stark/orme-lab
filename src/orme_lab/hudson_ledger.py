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

from .config import ModelThresholds
from .identity import IdentityWitness


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


#: Hudson's claimed novel phase: elemental composition, zero oxidation, but NOT the metallic
#: lattice — distinct from both "metallic" and the compound phases (oxide/salt/...).
NONMETALLIC_ELEMENTAL = "nonmetallic-elemental"
_OX_TOL = 0.5   # |oxidation| above this implies a compound, not an elemental phase


class HudsonIdentity(str, Enum):
    ESTABLISHED = "established"              # characterization complete (phase-agnostic)
    HUDSON_SATISFIED = "hudson-satisfied"   # established AND nonmetallic AND atomically dispersed
    HUDSON_FAILED = "hudson-failed"         # identified but metallic / clustered / compound
    HUDSON_UNRESOLVED = "hudson-unresolved" # cannot distinguish isolated atoms from clusters/phases


def g_identity_established(witness: IdentityWitness) -> bool:
    """Phase-AGNOSTIC: every descriptor is known within stated uncertainty. 'We know what it
    physically is' — whether metal, compound, or the novel phase. (This is NOT identity.py's
    metallic-target gate, which is Branch-A-specific.)"""
    return (witness.composition is not None and witness.phase is not None
            and witness.morphology is not None and witness.oxidation_state is not None)


def assess_hc01(witness: IdentityWitness, target: str, th: ModelThresholds) -> ClaimRecord:
    """HC-01: a stable NONMETALLIC ELEMENTAL PGM form (composition = target, |oxidation| <= tol,
    phase = nonmetallic-elemental). The oxide/hydroxide/salt/complex phases are the ruled-out
    mundane alternative. Simulation caps at PROVISIONALLY_SUPPORTED via witness; a MEASURED
    confirmation (loaded separately) is what reaches SUPPORTED."""
    text = "stable nonmetallic PGM form"
    mundane = "oxide / hydroxide / salt / ligand complex"
    if not g_identity_established(witness):
        return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                           mundane, ClaimStatus.CANDIDATE, 2, Route.NONE, True, None,
                           "identity not established")
    is_elemental = (witness.composition == target and abs(witness.oxidation_state) <= _OX_TOL)
    if witness.phase == NONMETALLIC_ELEMENTAL and is_elemental:
        return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                           mundane, ClaimStatus.PROVISIONALLY_SUPPORTED, 2, Route.NONE, True, None,
                           "witness: nonmetallic-elemental phase")
    return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                       mundane, ClaimStatus.CANDIDATE, 2, Route.NONE, True, None,
                       f"phase '{witness.phase}' is not nonmetallic-elemental "
                       f"(mundane alternative: {mundane})")
