"""Hudson Claim Ledger — falsify-first assessment of Hudson's eight ORME claims.

A REPORTING layer above the per-candidate pipeline (not a gate inside the SC AND-gate or its
closure oracle; distinct from lab_loop/ledger.py, the experiment ledger). Objective: determine
whether a reproducible material state exists that satisfies Hudson's stated properties —
attacking the ordinary explanation of each claim first. Extraordinary claims are default-blocked;
the ledger never self-asserts the Hudson mechanism from simulation and never emits "VALIDATED".
See docs/hudson_claim_ledger.md and the design spec.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, IntEnum

from .config import ModelThresholds
from .hudson_optical import HudsonClaim, Persistence
from .identity import IdentityWitness
from .ir_contaminant import screen_contaminants
from .lineage import MaterialLineage, singleton_lineage, lineage_key
from .meissner_field import screen_meissner
from .pipeline import CandidateRecord
from .structure import StructuralDistribution


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
    hc02_dispersion_confirmed: bool = False   # measured EXAFS/STEM/PDF dispersion, controls classified
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


def assess_hc02(distribution: StructuralDistribution, th: ModelThresholds) -> ClaimRecord:
    """HC-02 is a POLICY over measurements, not a Boolean. Clears when: isolated fraction is
    above the floor AND the upper-bounded clustered fraction is under the cap AND no PGM-PGM
    coordination signal exceeds tolerance. A monomer has nn distance +inf (no bond)."""
    f_single = distribution.f1()
    clustered_ub = min(1.0, (1.0 - f_single) + th.hudson_hc02_cluster_margin)
    coordinated = sum(frac for dist, frac in distribution.nn_distances()
                      if math.isfinite(dist) and dist <= th.hudson_hc02_bond_length_ang)
    text, mundane = "atomically dispersed ('monoatomic')", "undetected clusters / nanoparticles"
    req = "predominantly isolated atoms (EXAFS/STEM/PDF)"
    clears = (f_single >= th.hudson_hc02_min_isolated_fraction
              and clustered_ub <= th.hudson_hc02_max_clustered_fraction
              and coordinated <= th.hudson_hc02_pgm_pgm_tolerance)
    if clears:
        return ClaimRecord(HudsonClaimId.HC_02, text, req, mundane,
                           ClaimStatus.PROVISIONALLY_SUPPORTED, 2, Route.NONE, True, None,
                           f"f_single={f_single:.2f}, clustered_ub={clustered_ub:.2f}, "
                           f"pgm-pgm={coordinated:.2f}")
    return ClaimRecord(HudsonClaimId.HC_02, text, req, mundane, ClaimStatus.CANDIDATE, 2,
                       Route.NONE, True, None,
                       f"dispersion policy not met (f_single={f_single:.2f}, "
                       f"clustered_ub={clustered_ub:.2f}, pgm-pgm={coordinated:.2f})")


def g_hudson_material_state(witness: IdentityWitness, distribution: StructuralDistribution,
                            target: str, th: ModelThresholds) -> tuple[bool, "HudsonIdentity"]:
    """G_hudson_material_state = HC-01 (nonmetallic-elemental) AND HC-02 (atomically dispersed).
    Returns (passed, HudsonIdentity outcome)."""
    if not g_identity_established(witness):
        return False, HudsonIdentity.HUDSON_UNRESOLVED
    hc01 = assess_hc01(witness, target, th).status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    hc02 = assess_hc02(distribution, th).status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    if hc01 and hc02:
        return True, HudsonIdentity.HUDSON_SATISFIED
    return False, HudsonIdentity.HUDSON_FAILED


def g_conventional_superconductivity(measured: MeasuredEvidence) -> bool:
    """Branch A, measured: zero_resistance AND flux_exclusion AND critical_behavior AND
    artifact_excluded. Default-blocked (all False by default)."""
    return (measured.zero_resistance and measured.flux_exclusion
            and measured.critical_behavior and measured.artifact_excluded)


def g_candidate_optical(optical_result) -> bool:
    """Branch B: coherent-mode (L3+L4) AND material-coupling (L6) AND energy-transport (L5).

    The Hudson mechanism's energy-transport gate requires a genuinely SELF-SUSTAINING mode, so
    it demands Persistence.PERSISTENT — NOT merely LOW_LOSS_TRANSPORT, which Branch B also grants
    for a METASTABLE (long-lived but not self-sustaining) ring-down. A metastable mode supports
    the weaker Branch-B transport level but must not credit the Hudson optical mechanism."""
    if optical_result is None:
        return False
    s = optical_result.supported
    coherent_transport = {HudsonClaim.STRONG_COUPLING, HudsonClaim.MACRO_COHERENCE,
                          HudsonClaim.ELECTRONIC_COUPLING, HudsonClaim.LOW_LOSS_TRANSPORT}.issubset(s)
    return coherent_transport and optical_result.persistence.persistence is Persistence.PERSISTENT


def optical_magnetic_causality(optical_result) -> bool:
    """Branch B level-7: magnetic response tracks the optical resonance (measured dM/dP)."""
    return optical_result is not None and HudsonClaim.MAGNETISM_COUPLED in optical_result.supported


def replication_gate(rep: "ReplicationEvidence | None", th: ModelThresholds) -> bool:
    """Default-blocked: >= min_batches, > 1 lab (>= min_labs), preregistered thresholds, raw data
    retained, blinded controls correctly classified."""
    if rep is None:
        return False
    return (rep.n_batches >= th.hudson_replication_min_batches
            and rep.n_labs >= th.hudson_replication_min_labs
            and rep.preregistered_thresholds and rep.raw_data_retained
            and rep.blinded_controls_correct)


def assess_hc04(observed_doublet, th: ModelThresholds) -> ClaimRecord:
    """HC-04: the 1400-1600 cm^-1 doublet. Attacks the contaminant alternative first via the
    IR contaminant screen. A plausible match to a mundane species keeps HC-04 at LEAD/CANDIDATE
    (the doublet is explained by contamination); intrinsic assignment needs measured isotope/
    atmosphere sensitivity (loaded separately)."""
    text = "1400-1600 cm^-1 doublet"
    mundane = "water / carbonate / nitrate / ligand / instrument bkg (carboxylate contaminant)"
    match = screen_contaminants(tuple(observed_doublet))
    note = getattr(match, "explain", lambda: "")()
    return ClaimRecord(HudsonClaimId.HC_04, text, "reproducible isotope- & atmosphere-sensitive assignment",
                       mundane, ClaimStatus.LEAD, 2, Route.NONE, True, None,
                       f"IR contaminant screen: {note}")


def assess_hc06(candidate: CandidateRecord, measured: MeasuredEvidence,
                th: ModelThresholds) -> ClaimRecord:
    """HC-06: flux exclusion > 200 K. Either route, labelled. Conventional = Meissner screen
    (LEAD) / measured flux exclusion (SUPPORTED); optical = Branch-B level-7 (measured dM/dP)."""
    text, mundane = "flux exclusion > 200 K", "magnetic artifact / ordinary diamagnetism"
    req = "geometry-corrected diamagnetic shielding"
    if measured.flux_exclusion:
        return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.CONVENTIONAL, True, None, "measured diamagnetic flux exclusion")
    if optical_magnetic_causality(measured.optical_result):
        return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.OPTICAL, True, None, "measured dM/dP tracks the optical resonance")
    screen = screen_meissner(isolated_premise=True)
    return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.LEAD, 2,
                       Route.CONVENTIONAL, True, None, f"Meissner screen: {screen.verdict}")


def assess_hc07(candidate: CandidateRecord, measured: MeasuredEvidence,
                th: ModelThresholds) -> ClaimRecord:
    """HC-07: superconductivity. credited_sc_lead -> LEAD (never SUPPORTED from a sim lead).
    Measured conventional evidence -> SUPPORTED route=conventional; measured optical phase
    (Branch-B transport) -> SUPPORTED route=optical."""
    text, mundane = "superconductivity", "ionic conduction / percolation / contact artifact"
    req = "R->0 + magnetic + thermodynamic evidence"
    if g_conventional_superconductivity(measured):
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.CONVENTIONAL, True, None, "measured R->0 + magnetic + thermodynamic")
    if g_candidate_optical(measured.optical_result):
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.OPTICAL, True, None, "measured persistent optical transport (Branch B)")
    if candidate.credited_sc_lead:
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.LEAD, 2,
                           Route.NONE, True, None, "credited_sc_lead (simulation lead, not support)")
    return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.CANDIDATE, 2,
                       Route.NONE, True, None, "no SC lead")


def _procedural(hc, text, required, mundane, confirmed) -> ClaimRecord:
    status = ClaimStatus.SUPPORTED if confirmed else ClaimStatus.CANDIDATE
    ev = 4 if confirmed else 3   # a measured confirmation is an observation (L4); the design is L3
    note = ("measured confirmation loaded" if confirmed
            else f"Level-3 decisive-experiment design; attack the mundane alternative first: {mundane}")
    return ClaimRecord(hc, text, required, mundane, status, ev, Route.NONE, False, None, note)


def assess_hc03(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_03, "orbital rearrangement",
                       "reproducible electronic structure distinct from known compounds (XPS/XAS/EELS)",
                       "ordinary crystal-field / oxidation-state change", measured.hc03_orbital_confirmed)


def assess_hc05(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_05, "conversion back to metal",
                       "mass-balanced recovery of the original PGM",
                       "contamination / reduction of an ordinary salt", measured.hc05_recovery_confirmed)


def assess_hc08(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_08, "anomalous apparent mass",
                       "replication on independent balances under controlled gas flow",
                       "buoyancy / convection / magnetic force / balance coupling", measured.hc08_mass_confirmed)


_CORE = (HudsonClaimId.HC_01, HudsonClaimId.HC_02, HudsonClaimId.HC_04,
         HudsonClaimId.HC_06, HudsonClaimId.HC_07)


@dataclass(frozen=True)
class HudsonGateResult:
    g_identity_established: bool
    g_hudson_material_state: bool
    g_conventional_superconductivity: bool
    g_candidate_optical: bool
    optical_magnetic_causality: bool
    replication: bool
    g_hudson_mechanism: bool
    interim_verdict: str


@dataclass(frozen=True)
class HudsonLedger:
    claims: tuple[ClaimRecord, ...]                 # portfolio best-of, fixed HC order
    gate: HudsonGateResult
    integrated_status: ClaimStatus
    integrated_lineage_id: str | None
    per_lineage: tuple[tuple[str, ClaimStatus], ...]

    def claim_status(self, hc: HudsonClaimId) -> ClaimStatus:
        return next(c.status for c in self.claims if c.id == hc)

    def explain(self) -> str:
        return (f"Hudson ledger: integrated_status={self.integrated_status.name} "
                f"(lineage {self.integrated_lineage_id}); {self.gate.interim_verdict}. "
                f"Conventional SC gate={self.gate.g_conventional_superconductivity}; "
                f"Hudson mechanism gate={self.gate.g_hudson_mechanism}. Portfolio best-of and the "
                f"integrated weakest-link roll-up are reported separately; the lab never asserts "
                f"an affirmative validated verdict.")


def _interim_verdict(gate_bits: dict) -> str:
    """Deterministic priority ladder. NEVER returns an affirmative 'validated' verdict (the
    strongest terminal label is 'independent-replication-achieved')."""
    if gate_bits["g_hudson_mechanism"] and gate_bits["replication"]:
        return "independent-replication-achieved (Hudson mechanism supported on one replicated lineage)"
    if gate_bits["g_conventional_superconductivity"]:
        return "bulk-SC-supported (conventional route; distinct from the Hudson optical mechanism)"
    if gate_bits["g_candidate_optical"]:
        return "SC-like-response (optical coherent transport; mechanism not yet fully closed)"
    if gate_bits["g_hudson_material_state"]:
        return "novel-phase-candidate (Hudson material state; no transport/magnetism established)"
    if gate_bits["g_identity_established"]:
        return "identity-established (not Hudson-conformant)"
    return "identity-unresolved"


def _candidate_claim_records(cand, witness, dist, measured, observed_doublet, target, th):
    """All eight ClaimRecords for ONE candidate/lineage."""
    m = measured if measured is not None else MeasuredEvidence()
    hc01 = assess_hc01(witness, target, th) if witness is not None else \
        ClaimRecord(HudsonClaimId.HC_01, "stable nonmetallic PGM form", "", "", ClaimStatus.CANDIDATE, 2)
    if m.hc01_nonmetallic_confirmed and hc01.status >= ClaimStatus.PROVISIONALLY_SUPPORTED:
        hc01 = ClaimRecord(hc01.id, hc01.claim_text, hc01.required_observation, hc01.mundane_alternative,
                           ClaimStatus.SUPPORTED, 4, hc01.route, True, None, "measured nonmetallic confirmation")
    hc02 = assess_hc02(dist, th) if dist is not None else \
        ClaimRecord(HudsonClaimId.HC_02, "atomically dispersed", "", "", ClaimStatus.CANDIDATE, 2)
    if m.hc02_dispersion_confirmed and hc02.status >= ClaimStatus.PROVISIONALLY_SUPPORTED:
        hc02 = ClaimRecord(hc02.id, hc02.claim_text, hc02.required_observation, hc02.mundane_alternative,
                           ClaimStatus.SUPPORTED, 4, hc02.route, True, None, "measured dispersion confirmation")
    hc03 = assess_hc03(m)
    hc04 = assess_hc04(observed_doublet, th) if observed_doublet is not None else \
        ClaimRecord(HudsonClaimId.HC_04, "1400-1600 cm^-1 doublet", "", "carboxylate contaminant",
                    ClaimStatus.CANDIDATE, 2)
    if m.hc04_isotope_confirmed:
        hc04 = ClaimRecord(hc04.id, hc04.claim_text, hc04.required_observation, hc04.mundane_alternative,
                           ClaimStatus.SUPPORTED, 4, hc04.route, True, None, "measured isotope/atmosphere sensitivity")
    hc05 = assess_hc05(m)
    hc06 = assess_hc06(cand, m, th)
    hc07 = assess_hc07(cand, m, th)
    hc08 = assess_hc08(m)
    return (hc01, hc02, hc03, hc04, hc05, hc06, hc07, hc08)


def evaluate_hudson_ledger(candidates, *, witnesses=None, distributions=None, lineages=None,
                           measured=None, observed_doublet=None, thresholds):
    """Two-layer roll-up. Portfolio best-of over all candidates (per claim); integrated
    weakest-link within one lineage, then best across (never min_j[max_c])."""
    th = thresholds
    n = len(candidates)
    witnesses = witnesses if witnesses is not None else [None] * n
    distributions = distributions if distributions is not None else [None] * n
    lineages = lineages if lineages is not None else [singleton_lineage(
        f"{c.element}/{c.geometry}/{c.spin_label}") for c in candidates]
    measured = measured or {}

    # per-candidate records (fixed order)
    per_candidate = []
    for i, cand in enumerate(candidates):
        lin = lineages[i]
        recs = _candidate_claim_records(cand, witnesses[i], distributions[i],
                                        measured.get(lineage_key(lin)), observed_doublet,
                                        cand.element, th)
        per_candidate.append((lin, recs))

    # Layer 1: portfolio best-of per claim (max status across candidates); pick a representative record
    portfolio = []
    for j, hc in enumerate(HudsonClaimId):
        best = max((recs[j] for _, recs in per_candidate), key=lambda r: r.status)
        portfolio.append(best)

    # Layer 2: integrated weakest-link WITHIN one lineage over CORE, then best across lineages.
    core_idx = [list(HudsonClaimId).index(hc) for hc in _CORE]
    from .lineage import group_by_lineage
    grouped = group_by_lineage(tuple((lin, recs) for lin, recs in per_candidate))

    per_lineage = []
    lineage_bits: dict = {}          # key -> gate bits, each computed SAME-LINEAGE (no cross-lineage union)
    best_status, best_core_key = None, None
    for key, recs_list in grouped.items():
        combined = [max((recs[j] for recs in recs_list), key=lambda r: r.status) for j in range(8)]
        weakest = min(combined[j].status for j in core_idx)
        per_lineage.append((key, weakest))
        if best_status is None or weakest > best_status:      # argmax: always a REAL winning lineage
            best_status, best_core_key = weakest, key
        idxs = [i for i, l in enumerate(lineages) if lineage_key(l) == key]
        wm = measured.get(key, MeasuredEvidence())
        g_id_k = any(witnesses[i] is not None and g_identity_established(witnesses[i]) for i in idxs)
        # G_hudson_material_state = HC-01 AND HC-02, from the BATCH-COMBINED claim records (per-claim
        # max within one homogeneous batch). This is legitimate same-batch integration — HC-01 from
        # one aliquot and HC-02 from another aliquot OF THE SAME BATCH is the same material — NOT the
        # cross-lineage Frankenstein union (different lineages never share a key, so never combine).
        g_mat_k = (combined[0].status >= ClaimStatus.PROVISIONALLY_SUPPORTED
                   and combined[1].status >= ClaimStatus.PROVISIONALLY_SUPPORTED)
        g_opt_k = g_candidate_optical(wm.optical_result)
        g_caus_k = optical_magnetic_causality(wm.optical_result)
        g_rep_k = replication_gate(wm.replication, th)
        lineage_bits[key] = {
            "g_identity_established": g_id_k, "g_hudson_material_state": g_mat_k,
            "g_conventional_superconductivity": g_conventional_superconductivity(wm),
            "g_candidate_optical": g_opt_k, "optical_magnetic_causality": g_caus_k,
            "replication": g_rep_k, "g_hudson_mechanism": g_mat_k and g_opt_k and g_caus_k and g_rep_k}

    # Compound gates are EXISTENTIAL over lineages, each evaluated SAME-LINEAGE — never a cross-
    # lineage union of components (that would be the Frankenstein bug at the gate level). Component
    # bits are reported from ONE representative lineage (mechanism lineage > conventional-SC lineage
    # > CORE winner) so the reported bits stay internally consistent.
    mech_keys = [k for k, b in lineage_bits.items() if b["g_hudson_mechanism"]]
    conv_keys = [k for k, b in lineage_bits.items() if b["g_conventional_superconductivity"]]
    rep_key = mech_keys[0] if mech_keys else conv_keys[0] if conv_keys else best_core_key
    bits = dict(lineage_bits.get(rep_key, {
        "g_identity_established": False, "g_hudson_material_state": False,
        "g_conventional_superconductivity": False, "g_candidate_optical": False,
        "optical_magnetic_causality": False, "replication": False, "g_hudson_mechanism": False}))
    bits["g_hudson_mechanism"] = bool(mech_keys)                 # existential, same-lineage
    bits["g_conventional_superconductivity"] = bool(conv_keys)   # existential, separate result
    integrated = best_status if best_status is not None else ClaimStatus.CANDIDATE
    gate = HudsonGateResult(bits["g_identity_established"], bits["g_hudson_material_state"],
                            bits["g_conventional_superconductivity"], bits["g_candidate_optical"],
                            bits["optical_magnetic_causality"], bits["replication"],
                            bits["g_hudson_mechanism"], _interim_verdict(bits))
    return HudsonLedger(tuple(portfolio), gate, integrated, best_core_key, tuple(per_lineage))
