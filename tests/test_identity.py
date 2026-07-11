"""Tests for the phase-identity gate (G_identity)."""
from __future__ import annotations

from orme_lab.identity import (
    IdentityVerdict,
    IdentityWitness,
    evaluate_identity,
)


def _metallic(target="Ir"):
    return IdentityWitness(composition=target, phase="metallic", morphology="sub-nm-cluster",
                           oxidation_state=0.0, instruments=("XRD", "XPS"))


def test_no_witness_is_unestablished_and_blocks():
    r = evaluate_identity("Ir", None)
    assert r.verdict == IdentityVerdict.UNESTABLISHED
    assert r.established is False
    assert set(r.missing) == {"composition", "phase", "morphology", "oxidation"}


def test_full_metallic_witness_is_established():
    r = evaluate_identity("Ir", _metallic("Ir"))
    assert r.verdict == IdentityVerdict.ESTABLISHED
    assert r.established is True
    assert r.missing == ()


def test_oxide_phase_is_contradicted():
    w = IdentityWitness(composition="Ir", phase="oxide", morphology="nanoparticle",
                        oxidation_state=4.0, instruments=("XRD",))
    r = evaluate_identity("Ir", w)
    assert r.verdict == IdentityVerdict.CONTRADICTED
    assert r.established is False


def test_wrong_composition_is_contradicted():
    w = IdentityWitness(composition="IrCl3", phase="salt", morphology="bulk",
                        oxidation_state=3.0, instruments=("ICP-MS",))
    r = evaluate_identity("Ir", w)
    assert r.verdict == IdentityVerdict.CONTRADICTED


def test_partial_witness_is_unestablished_with_missing():
    w = IdentityWitness(composition="Ir", phase="metallic", morphology=None,
                        oxidation_state=None, instruments=("XPS",))
    r = evaluate_identity("Ir", w)
    assert r.verdict == IdentityVerdict.UNESTABLISHED
    assert set(r.missing) == {"morphology", "oxidation"}


def test_witness_with_no_instrument_is_not_a_witness():
    w = IdentityWitness(composition="Ir", phase="metallic", morphology="bulk",
                        oxidation_state=0.0, instruments=())
    r = evaluate_identity("Ir", w)
    assert r.verdict == IdentityVerdict.UNESTABLISHED


# ---- pipeline integration: G_identity gates crediting ----
from orme_lab.pipeline import evaluate_candidate, run_screen
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state


def _pt_candidate(identity=None):
    pt = get_element("Pt")
    return evaluate_candidate(pt, make_compact_cluster(pt, 13), "high_spin",
                              high_spin_state(pt), DEFAULT_CONFIG, identity=identity)


def test_no_witness_blocks_crediting():
    rec = _pt_candidate(identity=None)
    assert rec.identity_verdict == "unestablished"
    assert rec.identity_established is False
    assert rec.credited_sc_lead is False


def test_metallic_witness_credits_iff_proxies_pass():
    w = IdentityWitness("Pt", "metallic", "sub-nm-cluster", 0.0, ("XRD", "XPS"))
    rec = _pt_candidate(identity=w)
    assert rec.identity_established is True
    assert rec.credited_sc_lead == ((not rec.ruled_out) and rec.sc_plausibility > 0)


def test_contradicted_witness_never_credits():
    w = IdentityWitness("PtO2", "oxide", "nanoparticle", 4.0, ("XRD",))
    rec = _pt_candidate(identity=w)
    assert rec.identity_verdict == "contradicted"
    assert rec.credited_sc_lead is False


def test_full_screen_credits_nothing_without_identity():
    # The honesty invariant: across the whole default screen (no characterization
    # witness), NO candidate is credited as an SC lead — including any that pass the
    # SC proxy gate. Crediting requires phase identity, which is unestablished here.
    recs = run_screen()
    assert all(r.credited_sc_lead is False for r in recs)
    assert all(r.identity_verdict == "unestablished" for r in recs)
