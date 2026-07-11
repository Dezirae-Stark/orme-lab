"""Tests for the generalized adversarial validator."""
from __future__ import annotations

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state
from orme_lab.validator import AdversarialTest, ValidationSuite, design_validation


def _record(sym):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)


def _measurements(suite):
    return [t.measurement for t in suite.tests]


def _mechanisms(suite):
    return {t.mechanism for t in suite.tests if t.mechanism}


def test_generic_branch_table_always_present():
    s = design_validation(_record("Au"))
    for m in ("R(T,B,I)", "Meissner flux expulsion", "current reversal",
              "AC frequency sweep", "heat-capacity anomaly", "sample subdivision"):
        assert m in _measurements(s)


def test_seven_fields_populated():
    s = design_validation(_record("Au"))
    t = next(t for t in s.tests if t.measurement == "R(T,B,I)")
    assert isinstance(t, AdversarialTest)
    assert t.claimed_signature and t.instrument and t.rejection_threshold
    assert t.mundane_alternatives and t.control_samples
    assert t.evidence_level == 3                      # this design is a Level-3 prediction
    assert t.evidence_level_if_confirmed >= 3


def test_high_spin_gets_triplet_and_granular_not_isotope():
    # Os high-spin survivors: spin_fluctuation, triplet, granular (M_phonon pair-broken).
    s = design_validation(_record("Os"))
    ms = _measurements(s)
    assert "NMR Knight shift + H_c2" in ms          # triplet
    assert "Shapiro steps" in ms                     # granular
    assert "magnetic-QCP tuning" in ms               # spin-fluctuation
    assert "isotope effect" not in ms                # phonon did NOT survive -> no phonon test


def test_closed_shell_gets_isotope_not_triplet():
    # Au closed-shell survivors: phonon, granular.
    s = design_validation(_record("Au"))
    ms = _measurements(s)
    assert "isotope effect" in ms                    # phonon
    assert "Shapiro steps" in ms                     # granular
    assert "NMR Knight shift + H_c2" not in ms       # triplet did NOT survive


def test_mechanism_tests_are_tagged():
    s = design_validation(_record("Os"))
    assert "M_triplet" in _mechanisms(s)
    assert "M_granular_josephson" in _mechanisms(s)
    assert "M_phonon" not in _mechanisms(s)


def test_ir_doublet_control_folds_in():
    s = design_validation(_record("Os"), observed_doublet=(1429.53, 1490.99))
    assert any("IR-doublet control" in t.note for t in s.tests)
    # a folded IR test carries the contaminant alternative
    ir = next(t for t in s.tests if "IR-doublet control" in t.note)
    assert any("contaminant" in alt[0] for alt in ir.mundane_alternatives)


def test_ir_control_is_not_tagged_as_a_surviving_mechanism():
    # Os rejects M_excitonic_polaritonic (EM channel off), so a folded IR identity control
    # must NOT carry that (or any) mechanism tag — otherwise explain()/mechanism filters route
    # users to a mechanism the candidate explicitly rejected.
    rec = _record("Os")
    assert "M_excitonic_polaritonic" not in rec.surviving_mechanisms      # precondition
    s = design_validation(rec, observed_doublet=(1429.53, 1490.99))
    ir_controls = [t for t in s.tests if "IR-doublet control" in t.note]
    assert ir_controls                                                    # they were folded in
    assert all(t.mechanism is None for t in ir_controls)
    assert "M_excitonic_polaritonic" not in _mechanisms(s)


def test_suite_is_deterministic():
    a = design_validation(_record("Os"))
    b = design_validation(_record("Os"))
    assert a == b
    assert a.decisive_count == b.decisive_count and a.decisive_count > 0


def test_explain_names_routed_mechanisms():
    s = design_validation(_record("Os"))
    assert "Level-3" in s.explain() and "M_triplet" in s.explain()


def test_every_design_is_level_3():
    s = design_validation(_record("Os"), observed_doublet=(1429.53, 1490.99))
    assert all(t.evidence_level == 3 for t in s.tests)          # the lab designs; it cannot run them


def test_non_decisive_tests_cannot_reach_observation():
    s = design_validation(_record("Au"))
    for name in ("current reversal", "AC frequency sweep"):
        t = next(t for t in s.tests if t.measurement == name)
        assert t.decisive is False
        assert t.evidence_level_if_confirmed == 3               # non-decisive -> no Level-4 observation
    r = next(t for t in s.tests if t.measurement == "R(T,B,I)")
    assert r.decisive is True and r.evidence_level_if_confirmed == 4
