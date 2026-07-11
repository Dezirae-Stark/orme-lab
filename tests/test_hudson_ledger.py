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


from orme_lab.hudson_ledger import assess_hc03, assess_hc05, assess_hc08


def test_procedural_claims_emit_level3_designs_and_default_to_candidate():
    for fn, hc in ((assess_hc03, "HC-03"), (assess_hc05, "HC-05"), (assess_hc08, "HC-08")):
        r = fn(MeasuredEvidence())
        assert r.id.value == hc
        assert r.computable is False
        assert r.evidence_level == 3                    # a laboratory-prediction design
        assert r.status is ClaimStatus.CANDIDATE
        assert r.mundane_alternative and r.required_observation


def test_procedural_claims_reach_supported_only_with_measured_confirmation():
    assert assess_hc05(MeasuredEvidence(hc05_recovery_confirmed=True)).status >= ClaimStatus.SUPPORTED
    assert assess_hc08(MeasuredEvidence(hc08_mass_confirmed=True)).status >= ClaimStatus.SUPPORTED
    assert assess_hc03(MeasuredEvidence(hc03_orbital_confirmed=True)).status >= ClaimStatus.SUPPORTED


from orme_lab.hudson_ledger import HudsonLedger, evaluate_hudson_ledger
from orme_lab.lineage import singleton_lineage


def _sat_witness():
    return IW("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0, ())


def test_ledger_default_path_is_default_blocked_and_never_validated():
    led = evaluate_hudson_ledger([_candidate("Os")], thresholds=TH)
    assert isinstance(led, HudsonLedger)
    assert led.gate.g_hudson_mechanism is False           # no measured evidence
    assert led.gate.g_conventional_superconductivity is False
    assert "VALIDATED" not in led.gate.interim_verdict.upper() or "NOT" in led.gate.interim_verdict.upper()
    assert led.gate.interim_verdict != "HUDSON CLAIM VALIDATED"


_CORE_HC = (HudsonClaimId.HC_01, HudsonClaimId.HC_02, HudsonClaimId.HC_04,
            HudsonClaimId.HC_06, HudsonClaimId.HC_07)


def test_anti_frankenstein_max_min_discriminates_from_forbidden_min_max():
    # THE keystone. Five Ir lineages, each with EXACTLY ONE core claim SUPPORTED, all five core
    # claims covered across the fleet, and NO single lineage clearing more than one. This is the
    # only input shape that makes the two roll-ups DIVERGE:
    #   forbidden min_claim(max_candidate) -> every core SUPPORTED somewhere -> SUPPORTED
    #   correct  max_lineage(min_claim)    -> each lineage's weakest core is CANDIDATE -> CANDIDATE
    # If the code ever regressed to min[max], integrated_status would be SUPPORTED and this fails.
    el = get_element("Ir")
    metal = IW("Ir", "metallic", "bulk", 0.0, ())
    disp = dispersed_sample(el, 0.95)
    clustered = make_distribution([(make_compact_cluster(el, 13), 1.0)])
    opt_transport = _optical(measured_ringdown_fs=1e30)          # persistent transport, NO dM/dP
    cands = [_candidate("Ir") for _ in range(5)]
    lineages = [singleton_lineage(f"lin{i}") for i in range(5)]
    witnesses = [_sat_witness(), metal, metal, metal, metal]     # only lin0 is nonmetallic-elemental
    distributions = [clustered, disp, clustered, clustered, clustered]  # only lin1 is dispersed
    measured = {
        "lin0/lin0": MeasuredEvidence(hc01_nonmetallic_confirmed=True),   # HC-01 only
        "lin1/lin1": MeasuredEvidence(hc02_dispersion_confirmed=True),    # HC-02 only
        "lin2/lin2": MeasuredEvidence(hc04_isotope_confirmed=True),       # HC-04 only (global doublet)
        "lin3/lin3": MeasuredEvidence(flux_exclusion=True),               # HC-06 only (flux, not full SC)
        "lin4/lin4": MeasuredEvidence(optical_result=opt_transport),      # HC-07 only (optical transport)
    }
    led = evaluate_hudson_ledger(cands, witnesses=witnesses, distributions=distributions,
                                 lineages=lineages, measured=measured,
                                 observed_doublet=(1429.53, 1490.99), thresholds=TH)
    # portfolio best-of: every core claim is SUPPORTED SOMEWHERE
    forbidden_minmax = min(led.claim_status(hc) for hc in _CORE_HC)      # what min[max] WOULD yield
    assert forbidden_minmax >= ClaimStatus.SUPPORTED
    # ...but NO single lineage clears the core conjunction -> the correct roll-up is NOT supported
    assert led.integrated_status < ClaimStatus.SUPPORTED
    # the two forms DIVERGE on these inputs -> the test is non-vacuous (a regression to min[max] fails)
    assert forbidden_minmax > led.integrated_status
    assert led.gate.g_hudson_mechanism is False
    assert led.gate.g_conventional_superconductivity is False           # no lineage has all 4 SC criteria


def test_ledger_never_emits_the_validated_string_anywhere():
    # The invariant is mechanical: NO ledger output (explain() or interim_verdict) may contain the
    # exact phrase, so an external grep can rely on its absence. Guard the FULL surface, not just
    # equality on interim_verdict.
    el = get_element("Ir")
    opt = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    m = MeasuredEvidence(optical_result=opt, hc01_nonmetallic_confirmed=True,
                         hc02_dispersion_confirmed=True, flux_exclusion=True, hc04_isotope_confirmed=True,
                         replication=ReplicationEvidence(3, 2, True, True, True))
    full = evaluate_hudson_ledger([_candidate("Ir")], witnesses=[_sat_witness()],
                                  distributions=[dispersed_sample(el, 0.95)], lineages=[singleton_lineage("Ir")],
                                  measured={"Ir/Ir": m}, observed_doublet=(1429.53, 1490.99), thresholds=TH)
    default = evaluate_hudson_ledger([_candidate("Os")], thresholds=TH)
    for led in (default, full):
        assert "HUDSON CLAIM VALIDATED" not in led.explain()
        assert "HUDSON CLAIM VALIDATED" not in led.gate.interim_verdict


def test_single_lineage_full_stack_supports_integrated_but_still_not_validated():
    el = get_element("Ir")
    opt = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    m = MeasuredEvidence(optical_result=opt, hc01_nonmetallic_confirmed=True,
                         flux_exclusion=True, hc04_isotope_confirmed=True,
                         replication=ReplicationEvidence(3, 2, True, True, True))
    led = evaluate_hudson_ledger([_candidate("Ir")], witnesses=[_sat_witness()],
                                 distributions=[dispersed_sample(el, 0.95)],
                                 lineages=[singleton_lineage("Ir")],
                                 measured={"Ir/Ir": m}, observed_doublet=(1429.53, 1490.99),
                                 thresholds=TH)
    assert led.gate.g_hudson_mechanism is True             # one lineage clears the mechanism
    assert led.gate.interim_verdict != "HUDSON CLAIM VALIDATED"   # never that string
    assert "replication" in led.gate.interim_verdict or "supported" in led.gate.interim_verdict
