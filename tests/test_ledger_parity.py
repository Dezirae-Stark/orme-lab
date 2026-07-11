"""Parity: web/ledger.js assessors & gates match hudson_ledger.py exactly (via node)."""
from __future__ import annotations
import json, re, shutil, subprocess
from pathlib import Path
import pytest
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.identity import IdentityWitness
from orme_lab.structure import dispersed_sample, make_distribution
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab import hudson_ledger as HL

_JS = Path(__file__).resolve().parents[1] / "web" / "ledger.js"
TH = DEFAULT_CONFIG.thresholds


def _th_js():
    return dict(hc02MinIsolated=TH.hudson_hc02_min_isolated_fraction,
                hc02MaxClustered=TH.hudson_hc02_max_clustered_fraction,
                hc02ClusterMargin=TH.hudson_hc02_cluster_margin,
                hc02PgmPgmTol=TH.hudson_hc02_pgm_pgm_tolerance,
                hc02BondLen=TH.hudson_hc02_bond_length_ang,
                replMinBatches=TH.hudson_replication_min_batches,
                replMinLabs=TH.hudson_replication_min_labs)


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    out = subprocess.run([node, "--input-type=module", "-e", js],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_hc02_policy_matches_python():
    el = get_element("Ir")
    for f1 in (0.95, 0.60, 0.30):
        dist = dispersed_sample(el, f1)
        py = HL.assess_hc02(dist, TH).status.value
        distjs = dict(f1=dist.f1(), sizeDist=dist.size_distribution(),
                      nnDistances=[list(t) for t in dist.nn_distances()])
        js = (f'import {{assessHc02}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(assessHc02({json.dumps(distjs)},{json.dumps(_th_js())}).status));')
        assert _node(js) == py, f"HC-02 mismatch at f1={f1}"


def test_identity_and_material_state_match_python():
    cases = [
        ("Ir", "nonmetallic-elemental", "monatomic", 0.0),
        ("Ir", "metallic", "bulk", 0.0),
        ("IrO2", "oxide", "nanoparticle", 4.0),
    ]
    el = get_element("Ir")
    dist = dispersed_sample(el, 0.95)
    for comp, phase, morph, ox in cases:
        w = IdentityWitness(comp, phase, morph, ox, ("XRD", "XPS"))
        py_est = HL.g_identity_established(w)
        py_ms, _ = HL.g_hudson_material_state(w, dist, "Ir", TH)
        wjs = dict(composition=comp, phase=phase, morphology=morph, oxidation=ox)
        distjs = dict(f1=dist.f1(), sizeDist=dist.size_distribution(),
                      nnDistances=[list(t) for t in dist.nn_distances()])
        js = (f'import {{gIdentityEstablished,gHudsonMaterialState}} from "{_JS.as_posix()}";'
              f'const w={json.dumps(wjs)},d={json.dumps(distjs)},th={json.dumps(_th_js())};'
              f'console.log(JSON.stringify([gIdentityEstablished(w),gHudsonMaterialState(w,d,"Ir",th)]));')
        got = _node(js)
        assert got[0] is py_est and got[1] is py_ms


def _witness_js(w):
    return dict(composition=w.composition, phase=w.phase, morphology=w.morphology, oxidation=w.oxidation_state)


def _dist_js(dist):
    return dict(f1=dist.f1(), sizeDist=dist.size_distribution(),
                nnDistances=[list(t) for t in dist.nn_distances()])


def _optical_js(opt):
    if opt is None:
        return None
    return dict(supported=sorted(int(c) for c in opt.supported), persistence=opt.persistence.persistence.value)


def _measured_js(m):
    return dict(zeroResistance=m.zero_resistance, fluxExclusion=m.flux_exclusion,
                criticalBehavior=m.critical_behavior, artifactExcluded=m.artifact_excluded,
                hc01NonmetallicConfirmed=m.hc01_nonmetallic_confirmed,
                hc02DispersionConfirmed=m.hc02_dispersion_confirmed,
                hc03OrbitalConfirmed=m.hc03_orbital_confirmed,
                hc04IsotopeConfirmed=m.hc04_isotope_confirmed,
                hc05RecoveryConfirmed=m.hc05_recovery_confirmed,
                hc08MassConfirmed=m.hc08_mass_confirmed,
                replication=(dict(nBatches=m.replication.n_batches, nLabs=m.replication.n_labs,
                                  preregistered=m.replication.preregistered_thresholds,
                                  rawRetained=m.replication.raw_data_retained,
                                  blindedOk=m.replication.blinded_controls_correct)
                             if m.replication is not None else None))


def _material_js(lineage_key, element, witness, dist, credited_sc_lead, optical, measured):
    fam, batch = lineage_key.split("/")[:2]
    return dict(lineage=dict(familyId=fam, batchId=batch, aliquotId=fam, processing=[]),
               element=element,
               witness=(_witness_js(witness) if witness is not None else None),
               distribution=(_dist_js(dist) if dist is not None else None),
               creditedScLead=bool(credited_sc_lead),
               optical=_optical_js(optical),
               measured=_measured_js(measured))


def test_anti_frankenstein_max_min_discriminates_js():
    # Mirrors test_hudson_ledger.test_anti_frankenstein_max_min_discriminates_from_forbidden_min_max:
    # 5 single-claim Ir lineages, one core claim SUPPORTED each, no lineage clearing more than
    # one -> forbidden min[max] would read SUPPORTED but the correct max[min] must not.
    el = get_element("Ir")
    hud_witness = IdentityWitness("Ir", "nonmetallic-elemental", "monatomic", 0.0, ())
    metal = IdentityWitness("Ir", "metallic", "bulk", 0.0, ())
    disp = dispersed_sample(el, 0.95)
    clustered = make_distribution([(make_compact_cluster(el, 13), 1.0)])
    from orme_lab.hudson_optical import evaluate_hudson_optical
    opt_transport = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                            matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                            matter_loss_ev=0.02, measured_ringdown_fs=1e30)
    from orme_lab.hudson_ledger import MeasuredEvidence
    witnesses = [hud_witness, metal, metal, metal, metal]
    distributions = [clustered, disp, clustered, clustered, clustered]
    opticals = [None, None, None, None, opt_transport]
    measured = [
        MeasuredEvidence(hc01_nonmetallic_confirmed=True),
        MeasuredEvidence(hc02_dispersion_confirmed=True),
        MeasuredEvidence(hc04_isotope_confirmed=True),
        MeasuredEvidence(flux_exclusion=True),
        MeasuredEvidence(),
    ]
    doublet = (1429.53, 1490.99)
    materials = [
        _material_js(f"lin{i}/lin{i}", "Ir", witnesses[i], distributions[i], False, opticals[i], measured[i])
        for i in range(5)
    ]
    js = (f'import {{evaluateLedger,CLAIM_STATUS}} from "{_JS.as_posix()}";'
          f'const led=evaluateLedger({json.dumps(materials)},{{th:{json.dumps(_th_js())},doublet:{json.dumps(doublet)}}});'
          f'const core=["HC-01","HC-02","HC-04","HC-06","HC-07"];'
          f'const forbidden=Math.min(...led.claims.filter(c=>core.includes(c.id)).map(c=>c.status));'
          f'console.log(JSON.stringify({{integratedStatus:led.integratedStatus,gHudsonMechanism:led.gate.gHudsonMechanism,'
          f'gConventional:led.gate.gConventionalSuperconductivity,forbidden,verdict:led.gate.interimVerdict}}));')
    got = _node(js)
    assert got["forbidden"] >= 4          # SUPPORTED somewhere for every core claim (portfolio)
    assert got["integratedStatus"] < 4    # no single lineage clears the core conjunction
    assert got["forbidden"] > got["integratedStatus"]
    assert got["gHudsonMechanism"] is False
    assert got["gConventional"] is False
    assert got["verdict"] != "HUDSON CLAIM VALIDATED"


def test_single_lineage_full_stack_matches_python():
    # Mirrors test_hudson_ledger.test_single_lineage_full_stack_supports_integrated_but_still_not_validated,
    # cell-for-cell against HL.evaluate_hudson_ledger built from equivalent Python objects.
    el = get_element("Ir")
    hud_witness = IdentityWitness("Ir", "nonmetallic-elemental", "monatomic", 0.0, ())
    disp = dispersed_sample(el, 0.95)
    from orme_lab.hudson_optical import evaluate_hudson_optical
    opt = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                  matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                  matter_loss_ev=0.02, measured_ringdown_fs=1e30, measured_dM_dP=1.0,
                                  dM_dP_on_resonance=True)
    from orme_lab.hudson_ledger import MeasuredEvidence, ReplicationEvidence
    from orme_lab.pipeline import evaluate_candidate
    from orme_lab.spin_states import high_spin_state
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.lineage import singleton_lineage
    cand = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin", high_spin_state(el), DEFAULT_CONFIG)
    m = MeasuredEvidence(optical_result=opt, hc01_nonmetallic_confirmed=True, flux_exclusion=True,
                         hc04_isotope_confirmed=True, replication=ReplicationEvidence(3, 2, True, True, True))
    doublet = (1429.53, 1490.99)
    py = HL.evaluate_hudson_ledger([cand], witnesses=[hud_witness], distributions=[disp],
                                   lineages=[singleton_lineage("Ir")], measured={"Ir/Ir": m},
                                   observed_doublet=doublet, thresholds=TH)

    material = _material_js("Ir/Ir", "Ir", hud_witness, disp, cand.credited_sc_lead, opt, m)
    js = (f'import {{evaluateLedger}} from "{_JS.as_posix()}";'
          f'const led=evaluateLedger([{json.dumps(material)}],{{th:{json.dumps(_th_js())},doublet:{json.dumps(doublet)}}});'
          f'console.log(JSON.stringify({{integratedStatus:led.integratedStatus,gHudsonMechanism:led.gate.gHudsonMechanism,'
          f'verdict:led.gate.interimVerdict,claims:led.claims.map(c=>c.status)}}));')
    got = _node(js)
    assert got["integratedStatus"] == py.integrated_status.value
    assert got["gHudsonMechanism"] is py.gate.g_hudson_mechanism
    assert got["verdict"] == py.gate.interim_verdict
    assert got["verdict"] != "HUDSON CLAIM VALIDATED"
    assert got["claims"] == [c.status.value for c in py.claims]


def test_dossier_findings_match_python_and_demo_states_are_labelled():
    # Findings (demo:false): HC-04 (IR-doublet contaminant screen) and HC-06 (Meissner screen)
    # carry no witness/distribution/optical/measured input of their own, so their computed
    # status must equal the bare Python assessors for the SAME (empty) inputs -- parity, not
    # a hand-set number here.
    doublet = (1429.53, 1490.99)
    py_hc04 = HL.assess_hc04(doublet, TH).status.value
    py_hc06 = HL.assess_hc06(None, HL.MeasuredEvidence(), TH).status.value

    js = (f'import {{DOSSIER, assessHc04, assessHc06, CLAIM_STATUS}} from "{_JS.as_posix()}";'
          f'const doublet={json.dumps(doublet)};'
          f'const th={json.dumps(_th_js())};'
          f'const findings=DOSSIER.filter(d=>d.demo===false);'
          f'const demos=DOSSIER.filter(d=>d.demo===true);'
          f'console.log(JSON.stringify({{'
          f'hc04:assessHc04(doublet,th).status,'
          f'hc06:assessHc06(null,{{}},th).status,'
          f'findingsNotDemo:findings.every(d=>d.demo===false),'
          f'demosLabelled:demos.every(d=>d.demo===true && typeof d.note==="string" && d.note.includes("demonstration")),'
          f'noFindingIsDemo:!findings.some(d=>d.note && d.note.includes("demonstration")),'
          f'}}));')
    got = _node(js)
    assert got["hc04"] == py_hc04
    assert got["hc06"] == py_hc06
    assert got["findingsNotDemo"] is True
    assert got["demosLabelled"] is True
    assert got["noFindingIsDemo"] is True


def test_dossier_evaluates_never_validated_and_portfolio_vs_integrated_diverges():
    # evaluateLedger(DOSSIER) never yields the forbidden affirmative verdict, and the demo
    # states are arranged so the portfolio best-of clears HC-06 AND HC-07 (SUPPORTED) while no
    # single lineage clears the core conjunction -- integrated stays below SUPPORTED. This is
    # the anti-Frankenstein divergence made visible from the dossier itself.
    doublet = (1429.53, 1490.99)
    js = (f'import {{DOSSIER, evaluateLedger, CLAIM_STATUS}} from "{_JS.as_posix()}";'
          f'const led=evaluateLedger(DOSSIER,{{th:{json.dumps(_th_js())},doublet:{json.dumps(doublet)}}});'
          f'const hc06=led.claims.find(c=>c.id==="HC-06").status;'
          f'const hc07=led.claims.find(c=>c.id==="HC-07").status;'
          f'console.log(JSON.stringify({{verdict:led.gate.interimVerdict,integratedStatus:led.integratedStatus,hc06,hc07}}));')
    got = _node(js)
    assert got["verdict"] != "HUDSON CLAIM VALIDATED"
    assert got["hc06"] >= HL.ClaimStatus.SUPPORTED.value
    assert got["hc07"] >= HL.ClaimStatus.SUPPORTED.value
    assert got["integratedStatus"] < HL.ClaimStatus.SUPPORTED.value


def test_optical_and_replication_gates_match_python():
    # optical persistent vs metastable; replication thresholds
    supported = [3, 4, 5, 6]  # STRONG,MACRO,LOW_LOSS,ELECTRONIC as int levels
    for persist, expect in (("persistent", True), ("metastable", False)):
        opt = dict(supported=supported, persistence=persist)
        js = (f'import {{gCandidateOptical}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(gCandidateOptical({json.dumps(opt)})));')
        assert _node(js) is expect
    for batches, labs, ok in ((3, 2, True), (2, 2, False), (3, 1, False)):
        rep = dict(nBatches=batches, nLabs=labs, preregistered=True, rawRetained=True, blindedOk=True)
        py = HL.replication_gate(HL.ReplicationEvidence(batches, labs, True, True, True), TH)
        js = (f'import {{replicationGate}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(replicationGate({json.dumps(rep)},{json.dumps(_th_js())})));')
        assert _node(js) is py is ok


def test_branchflow_results_match_python_gates():
    # branchFlow's two result booleans must equal the Python ledger's gate bits for the same
    # single-material inputs (conventional SC gate; Hudson mechanism conjunction).
    from orme_lab.hudson_ledger import (evaluate_hudson_ledger, MeasuredEvidence,
                                        ReplicationEvidence)
    from orme_lab.hudson_optical import evaluate_hudson_optical
    from orme_lab.identity import IdentityWitness
    from orme_lab.structure import dispersed_sample
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate
    from orme_lab.lineage import singleton_lineage
    el = get_element("Ir")
    opt = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                  matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                  matter_loss_ev=0.02, measured_ringdown_fs=1e30,
                                  measured_dM_dP=1.0, dM_dP_on_resonance=True)
    # a fully-evidenced single material: conventional SC full AND the Hudson mechanism full
    cand = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)
    m = MeasuredEvidence(zero_resistance=True, flux_exclusion=True, critical_behavior=True,
                         artifact_excluded=True, optical_result=opt,
                         replication=ReplicationEvidence(3, 2, True, True, True))
    w = IdentityWitness("Ir", "nonmetallic-elemental", "monatomic", 0.0, ("XRD", "XPS"))
    led = evaluate_hudson_ledger([cand], witnesses=[w], distributions=[dispersed_sample(el, 0.95)],
                                 lineages=[singleton_lineage("m1")], measured={"m1/m1": m},
                                 observed_doublet=(1429.53, 1490.99), thresholds=TH)
    py_conv = led.gate.g_conventional_superconductivity
    py_mech = led.gate.g_hudson_mechanism
    # JS: the equivalent single material fixture (witness nonmetallic-elemental, dispersed, full evidence)
    matjs = dict(
        lineage=dict(familyId="m1", batchId="m1", aliquotId="m1", processing=[]),
        element="Ir",
        witness=dict(composition="Ir", phase="nonmetallic-elemental", morphology="monatomic", oxidation=0.0),
        distribution=dict(f1=0.95, sizeDist={"1": 0.95, "2": 0.03, "13": 0.02},
                          nnDistances=[[float("inf"), 0.95], [2.82, 0.03], [2.82, 0.02]]),
        optical=dict(supported=[3, 4, 5, 6, 7], persistence="persistent"),
        measured=dict(zeroResistance=True, fluxExclusion=True, criticalBehavior=True,
                      artifactExcluded=True, hc01NonmetallicConfirmed=True, hc02DispersionConfirmed=True,
                      replication=dict(nBatches=3, nLabs=2, preregistered=True, rawRetained=True, blindedOk=True)),
        demo=True)
    js = (f'import {{branchFlow}} from "{_JS.as_posix()}";'
          f'const bf=branchFlow({json.dumps(matjs)},[1429.53,1490.99],{json.dumps(_th_js())});'
          f'console.log(JSON.stringify([bf.conventional.result, bf.hudson.result]));')
    got = _node(js)
    assert got == [py_conv, py_mech]


def test_branchflow_energy_transport_needs_persistent():
    # the Branch-B energy-transport stage must be false for a metastable ring-down, true for persistent
    def _bf(persist):
        matjs = dict(lineage=dict(familyId="x", batchId="x", aliquotId="x", processing=[]), element="Ir",
                     witness=None, distribution=None,
                     optical=dict(supported=[3, 4, 5, 6], persistence=persist), measured={}, demo=True)
        js = (f'import {{branchFlow}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(branchFlow({json.dumps(matjs)},[1429.53,1490.99],{json.dumps(_th_js())}).hudson.energyTransport));')
        return _node(js)
    assert _bf("metastable") is False
    assert _bf("persistent") is True


def test_ledger_js_no_egress_no_nondeterminism_no_innerhtml():
    """Static hygiene guard (Task 7): web/ledger.js must not reach the network, must not read
    wall-clock/RNG into computed output, and must never assign innerHTML (researcher/derived
    text goes through textContent/createElement only — see the module's own comment at its top)."""
    code_lines = [line for line in _JS.read_text().splitlines() if not line.strip().startswith("//")]
    code = "\n".join(code_lines)
    for forbidden in ("fetch(", "XMLHttpRequest", "WebSocket", "Date.now", "Math.random"):
        assert forbidden not in code, f"forbidden token {forbidden!r} found in web/ledger.js"
    for line in code_lines:
        assert ".innerHTML" not in line, f"innerHTML assignment found in web/ledger.js: {line!r}"


def test_branchflow_conventional_and_hudson_blocks_never_cross_read():
    """Static isolation guard (Task 4): branchFlow's returned `conventional` block must reference
    only measured.*-derived locals (m.*) and gConventionalSuperconductivity; the returned `hudson`
    block must reference only optical/material-state/replication locals — never a Branch-A
    measured field. Enforces the two-branches-never-merge invariant at the source-text level, not
    just at the computed-output level (test_branchflow_results_match_python_gates)."""
    src = _JS.read_text()
    conv_m = re.search(r"conventional:\s*\{([^}]*)\}", src)
    hud_m = re.search(r"hudson:\s*\{([^}]*)\}", src)
    assert conv_m and hud_m, "branchFlow's conventional/hudson return blocks not found in web/ledger.js"
    conv_block, hud_block = conv_m.group(1), hud_m.group(1)
    # Branch A (conventional) block: only measured.* (m.*) fields and the conventional-SC gate.
    for forbidden in ("coherentMode", "materialCoupling", "energyTransport", "causalMagnetism",
                       "materialState", "replication", "opt."):
        assert forbidden not in conv_block, f"conventional block references Branch-B token {forbidden!r}"
    # Branch B (hudson) block: only optical/material-state/replication locals, never a Branch-A
    # measured field or the conventional-SC gate.
    for forbidden in ("m.zeroResistance", "m.fluxExclusion", "m.criticalBehavior", "m.artifactExcluded",
                       "gConventionalSuperconductivity"):
        assert forbidden not in hud_block, f"hudson block references Branch-A token {forbidden!r}"
