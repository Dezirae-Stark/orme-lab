"""Parity: web/ledger.js assessors & gates match hudson_ledger.py exactly (via node)."""
from __future__ import annotations
import json, shutil, subprocess
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
