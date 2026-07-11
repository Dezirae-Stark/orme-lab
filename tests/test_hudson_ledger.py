"""Tests for the Hudson Claim Ledger."""
from __future__ import annotations

from orme_lab.hudson_ledger import (
    ClaimRecord,
    ClaimStatus,
    HudsonClaimId,
    MeasuredEvidence,
    ReplicationEvidence,
    Route,
)


def test_status_ladder_is_ordered():
    assert ClaimStatus.CANDIDATE < ClaimStatus.LEAD < ClaimStatus.SUPPORTED < ClaimStatus.INDEPENDENTLY_REPLICATED


def test_claim_ids_cover_all_eight():
    assert [c.value for c in HudsonClaimId] == [f"HC-0{i}" for i in range(1, 9)]


def test_records_construct():
    r = ClaimRecord(HudsonClaimId.HC_07, "superconductivity", "R->0 + magnetic + thermo",
                    "ionic/percolation/artifact", ClaimStatus.LEAD, 2, Route.CONVENTIONAL, True, None, "note")
    assert r.status is ClaimStatus.LEAD and r.route is Route.CONVENTIONAL
    rep = ReplicationEvidence(3, 2, True, True, True)
    assert rep.n_batches == 3
    m = MeasuredEvidence()
    assert m.zero_resistance is False and m.optical_result is None


from orme_lab.config import DEFAULT_CONFIG
from orme_lab.hudson_ledger import (
    HudsonIdentity,
    NONMETALLIC_ELEMENTAL,
    assess_hc01,
    g_identity_established,
)
from orme_lab.identity import IdentityWitness

TH = DEFAULT_CONFIG.thresholds


def test_identity_established_is_phase_agnostic():
    # a fully-characterized METAL is "established" (we know what it is) even though it is NOT Hudson's state
    metal = IdentityWitness("Ir", "metallic", "bulk", 0.0, ())
    assert g_identity_established(metal) is True
    hc01 = assess_hc01(metal, "Ir", TH)
    assert hc01.status.name in ("CANDIDATE",)            # metallic -> HC-01 not supported (ruled against)


def test_hc01_supported_only_for_nonmetallic_elemental():
    hud = IdentityWitness("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0, ())
    hc01 = assess_hc01(hud, "Ir", TH)
    assert hc01.status >= __import__("orme_lab.hudson_ledger", fromlist=["ClaimStatus"]).ClaimStatus.PROVISIONALLY_SUPPORTED
    # an oxide/salt is the ruled-out mundane alternative
    oxide = IdentityWitness("IrO2", "oxide", "nanoparticle", 4.0, ())
    assert assess_hc01(oxide, "Ir", TH).status.name == "CANDIDATE"


def test_identity_unresolved_when_uncharacterized():
    blank = IdentityWitness(None, None, None, None, ())
    assert g_identity_established(blank) is False


from orme_lab.hudson_ledger import assess_hc02, g_hudson_material_state
from orme_lab.elements import get_element
from orme_lab.structure import dispersed_sample, make_distribution
from orme_lab.geometry import make_compact_cluster, make_monomer


def test_hc02_clears_for_well_dispersed_sample():
    el = get_element("Ir")
    disp = dispersed_sample(el, 0.95)                    # 95% isolated
    r = assess_hc02(disp, TH)
    assert r.status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    # a clustered sample fails the policy
    clustered = make_distribution([(make_compact_cluster(el, 13), 1.0)])
    assert assess_hc02(clustered, TH).status.name == "CANDIDATE"


def test_hc02_flags_pgm_pgm_coordination():
    el = get_element("Ir")
    # 60% isolated / 40% clustered: below the isolated floor AND above clustered cap -> fails
    mixed = dispersed_sample(el, 0.60)
    assert assess_hc02(mixed, TH).status.name == "CANDIDATE"


def test_material_state_gate_combines_hc01_and_hc02():
    el = get_element("Ir")
    hud_witness = IdentityWitness("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0, ())
    ok, ident = g_hudson_material_state(hud_witness, dispersed_sample(el, 0.95), "Ir", TH)
    assert ok is True and ident is HudsonIdentity.HUDSON_SATISFIED
    metal_witness = IdentityWitness("Ir", "metallic", "bulk", 0.0, ())
    ok2, ident2 = g_hudson_material_state(metal_witness, dispersed_sample(el, 0.95), "Ir", TH)
    assert ok2 is False and ident2 is HudsonIdentity.HUDSON_FAILED


from orme_lab.hudson_ledger import (
    g_candidate_optical,
    g_conventional_superconductivity,
    optical_magnetic_causality,
    replication_gate,
)
from orme_lab.hudson_optical import evaluate_hudson_optical


def _optical(**kw):
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                   matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                   matter_loss_ev=0.02, **kw)


def test_conventional_sc_gate_is_default_blocked():
    assert g_conventional_superconductivity(MeasuredEvidence()) is False
    full = MeasuredEvidence(zero_resistance=True, flux_exclusion=True,
                            critical_behavior=True, artifact_excluded=True)
    assert g_conventional_superconductivity(full) is True


def test_optical_gates_need_measured_persistence_and_magnetism():
    # simulation-only optical result: strong coupling but NO persistence/magnetism -> gates False
    assert g_candidate_optical(_optical()) is False
    assert optical_magnetic_causality(_optical()) is False
    full = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert g_candidate_optical(full) is True
    assert optical_magnetic_causality(full) is True


def test_replication_gate_is_default_blocked():
    assert replication_gate(None, TH) is False
    assert replication_gate(ReplicationEvidence(3, 2, True, True, True), TH) is True
    assert replication_gate(ReplicationEvidence(2, 2, True, True, True), TH) is False   # < 3 batches


from orme_lab.hudson_ledger import assess_hc04, assess_hc06, assess_hc07
from orme_lab.geometry import make_compact_cluster
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state
from orme_lab.identity import IdentityWitness as IW


def _candidate(sym):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)


def test_hc07_credited_lead_is_lead_not_supported():
    # a credited_sc_lead candidate gives HC-07 status LEAD (never SUPPORTED from a sim lead)
    rec = _candidate("Os")
    r = assess_hc07(rec, MeasuredEvidence(), TH)
    assert r.status is ClaimStatus.LEAD or r.status is ClaimStatus.CANDIDATE
    assert r.status < ClaimStatus.SUPPORTED
    # measured conventional evidence reaches SUPPORTED, route=conventional
    full = MeasuredEvidence(zero_resistance=True, flux_exclusion=True,
                            critical_behavior=True, artifact_excluded=True)
    r2 = assess_hc07(rec, full, TH)
    assert r2.status >= ClaimStatus.SUPPORTED and r2.route is Route.CONVENTIONAL


def test_hc06_either_route_labelled():
    rec = _candidate("Os")
    conv = assess_hc06(rec, MeasuredEvidence(flux_exclusion=True), TH)
    assert conv.status >= ClaimStatus.SUPPORTED and conv.route is Route.CONVENTIONAL
    opt_result = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    opt = assess_hc06(rec, MeasuredEvidence(optical_result=opt_result), TH)
    assert opt.route is Route.OPTICAL and opt.status >= ClaimStatus.SUPPORTED


def test_hc04_folds_the_ir_control():
    r = assess_hc04((1429.53, 1490.99), TH)
    assert r.id.value == "HC-04"
    assert "contaminant" in r.mundane_alternative.lower()
