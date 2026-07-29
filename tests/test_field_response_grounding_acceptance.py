"""Acceptance contract for the heavy-fermion Hc2/Pauli-limit grounding (Task 5).

One test per spec criterion in docs/superpowers/specs/2026-07-30-field-response-hc2-grounding-design.md
("Test contract (acceptance)"). Where a criterion is already covered by a Task 1-4 unit test, this
file re-exercises it at the acceptance level (not a verbatim duplicate) so the grounding stands as a
single, named contract independent of the implementation-order tests.
"""
from dataclasses import replace

import pytest

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.magnetic_field import pauli_violation_ratio
from orme_lab.field_response_refs import BENCHMARKS, CESII_ANCHOR, classifies_correctly
from orme_lab.validator import _mech_test
from orme_lab.mechanisms import Mechanism
from orme_lab.lab_loop.closure import is_independent
from orme_lab.lab_loop.triage import Verdict, triage
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator


def _action(sym):
    return ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, True, True, None, sym)


def _av(target, metric, comp, thr, invariants, sym="triplet"):
    return Avenue("a", Tier.TIER1, "d", target, _action(sym),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


def test_1_r_pauli_boundary_matches_benchmark_table():
    # every cited benchmark classifies on the correct side of the R_Pauli=1 boundary
    for b in BENCHMARKS:
        assert classifies_correctly(b), f"{b.material} misclassified at R_Pauli=1"
    # and the discriminator's own function reproduces the same boundary direction
    assert pauli_violation_ratio(9.0, 10.0) <= 1.0    # Hc2 below Pauli limit -> singlet direction
    assert pauli_violation_ratio(40.0, 10.0) > 1.0    # Hc2 well above Pauli limit -> unconventional


def test_2_clean_limit_gate_actually_gates():
    el = get_element("Ir"); geo = make_compact_cluster(el, 13); st = high_spin_state(el)
    # dirty limit: huge Borb cannot register unconventional regardless of R_Pauli
    dirty = evaluate_candidate(el, geo, "high_spin", st,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=False))
    assert dirty.unconventional_admissible is False
    # clean but unknown Maki alpha (no Borb) -> still conservative non-registration
    clean_no_alpha = evaluate_candidate(el, geo, "high_spin", st,
              replace(DEFAULT_CONFIG, is_clean_limit=True))
    assert clean_no_alpha.unconventional_admissible is False


def test_3_pauli_limited_ratio_can_worsen_standing_against_triplet():
    # a Pauli-limited (R_Pauli <= 1) measurement kills H7-triplet on the field axis alone
    trip = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",))
    open_all = frozenset(HYPOTHESES)
    pauli_limited = {"max_field_response_ratio": 0.6}
    out = triage(AvenueResult(trip, (), pauli_limited), open_all)
    assert out.verdict == Verdict.KILLED_HYPOTHESIS and out.killed_hypothesis == "H7-triplet"


def test_4_field_response_stays_off_gate():
    assert is_independent(("field_response_ratio",))


def test_5_decisive_measurement_block_names_falsification_and_companions():
    t = _mech_test(Mechanism.TRIPLET.value)
    blob = (t.measurement + t.claimed_signature + t.rejection_threshold + t.note).lower()
    assert "pauli" in blob and "r_pauli" in blob
    assert "against" in blob and "consistent-with" in blob        # explicit falsification
    assert "non-fermi" in blob or "n < 2" in blob                 # NFL companion
    assert "effective-mass" in blob                                # effective-mass companion
    assert t.evidence_level == 3                                   # LABORATORY_PREDICTION, a prediction not an observation


def test_6_no_validated_level_2_everywhere_cesii_scoped():
    assert not hasattr(Verdict, "VALIDATED")
    el = get_element("Ir"); geo = make_compact_cluster(el, 13); st = high_spin_state(el)
    for sym in ("undetermined", "singlet", "triplet"):
        rec = evaluate_candidate(el, geo, "high_spin", st, replace(DEFAULT_CONFIG, pairing_symmetry=sym))
        assert rec.evidence_level <= 2
    t = CESII_ANCHOR.scoping.lower()
    assert "not" in t and "pgm" in t and "240" in CESII_ANCHOR.conditions
    assert "gpa" in CESII_ANCHOR.conditions.lower()


def test_7_refs_module_never_scores_a_pgm_candidate():
    import orme_lab.field_response_refs as m
    assert not hasattr(m, "score_candidate")
    for name in dir(m):
        obj = getattr(m, name)
        if callable(obj):
            assert "CandidateRecord" not in (getattr(obj, "__doc__", "") or "")


def test_8_default_path_byte_identical():
    # default LabConfig (no b_orb_tesla/is_clean_limit) -> conservative, not-registered, None extras
    el = get_element("Ir"); geo = make_compact_cluster(el, 13); st = high_spin_state(el)
    rec = evaluate_candidate(el, geo, "high_spin", st, DEFAULT_CONFIG)
    assert rec.b_orb_tesla is None and rec.is_clean_limit is None
    assert rec.unconventional_admissible is False


def test_2b_clean_limit_true_positive_through_pipeline():
    """TRUE-POSITIVE end-to-end (closes the Task-2 reviewer gap): with a Tc injected via a fake
    SC_GAP backend so R_Pauli>1 is real, a CLEAN candidate with a large Borb REGISTERS an
    unconventional signature, and the SAME candidate DIRTY does not. Exercises the pipeline wiring
    of maki_alpha / Bp / the fr_ratio>1 branch -- not just clean_limit_admits_unconventional in
    isolation. All prior pipeline tests hit the toy path (Tc=None), so this is the only place
    unconventional_admissible is observed True through evaluate_candidate."""
    from orme_lab.backends import DFTBackend, Capability
    from orme_lab.epw.result import EPWResult

    class _TcBackend(DFTBackend):
        name = "tc-double"
        @classmethod
        def available(cls) -> bool:
            return True
        def provides(self, cap) -> bool:            # only SC_GAP; all other seams stay toy
            return cap == Capability.SC_GAP
        def superconducting_gap(self, element, geometry, state):
            # tiny Tc -> Bp = 1.86*0.1 = 0.186 T, well below the toy critical field -> R_Pauli >> 1
            return EPWResult(0.1, 1.0, 100.0, 100.0, 1.0, 0.1, "epw", False, "test-double")

    el = get_element("Ir"); geo = make_compact_cluster(el, 13); st = high_spin_state(el)
    be = _TcBackend()
    clean = evaluate_candidate(el, geo, "high_spin", st,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=True), backend=be)
    dirty = evaluate_candidate(el, geo, "high_spin", st,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=False), backend=be)
    assert clean.field_response_ratio is not None and clean.field_response_ratio > 1.0  # R_Pauli>1 real
    assert clean.unconventional_admissible is True     # clean + big Borb + R_Pauli>1 -> registers
    assert dirty.unconventional_admissible is False     # same, dirty -> gated off (the gate bites)
    assert clean.evidence_level <= 2                     # still Level 2
