"""Task 9: acceptance contract for the orbital-order descriptor -- one test per
spec criterion (1-7). Criterion 8 (LIVE end-to-end QE validation) is exercised
manually, not in this suite (no live QE dependency in the deterministic tests),
and logged in docs/epw-orbital-order-run.md.

See docs/superpowers/plans/2026-07-23-orbital-order-descriptor.md.
"""

import dataclasses

import pytest

from orme_lab.backends import Capability, DFTBackend, implemented
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.epw.orbital_result import OrbitalResult
from orme_lab.geometry import make_compact_cluster
from orme_lab.lab_loop.avenue import (
    ActionSpec, Avenue, Comparator, FalsificationCondition, METRIC_RANGES, Tier,
)
from orme_lab.lab_loop.closure import GATE_INPUT_CLOSURE, OFF_GATE_INVARIANTS, is_independent
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.triage import Verdict, triage
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state


class _FakeOrbitalBackend(DFTBackend):
    name = "fake-orbital"
    description = "test double: canned OrbitalResult"
    declared_capabilities = frozenset({Capability.ORBITAL_ORDER})
    binary_requires = ("fake-projwfc",)

    def __init__(self, orbital):
        self._orbital = orbital

    @classmethod
    def available(cls) -> bool:
        return True

    @implemented(Capability.ORBITAL_ORDER)
    def orbital_order(self, element, geometry, state):
        return self._orbital


def _rec(compute_orbital_order, backend=None):
    el = get_element("Ir")
    geo = make_compact_cluster(el, 13)
    state = high_spin_state(el)
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_orbital_order=compute_orbital_order)
    return evaluate_candidate(el, geo, "high_spin", state, cfg, backend=backend)


def _av(target, metric, comp, thr, invariants, symmetry="undetermined"):
    return Avenue("a", Tier.TIER1, "d", target,
                  ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                             False, True, None, symmetry),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


# --- Criterion 1: inert-without-backend + toy-fallback flagged -------------

def test_1_inert_without_backend_toy_fallback_flagged():
    off = _rec(compute_orbital_order=False)
    assert off.orbital_order_param is None
    assert off.orbital_order_source == "toy"

    on_no_backend = _rec(compute_orbital_order=True, backend=None)
    assert on_no_backend.orbital_order_param is None
    assert on_no_backend.orbital_order_source == "absent"

    # inert: flag-off (`off`) and flag-on-but-no-backend (`on_no_backend`) must be
    # identical on EVERY CandidateRecord field except orbital_order_source itself
    # (the only field the "absent" path is permitted to move). This is a genuine
    # cross-record comparison, not a tautology built from `off` -- normalise
    # `on_no_backend`'s orbital_order_source back to "toy" and diff every field.
    normalized = dataclasses.replace(on_no_backend, orbital_order_source="toy")
    off_fields = dataclasses.fields(off)
    assert {f.name for f in off_fields} == {f.name for f in dataclasses.fields(normalized)}
    mismatches = [
        f.name for f in off_fields
        if getattr(off, f.name) != getattr(normalized, f.name)
    ]
    assert mismatches == []
    assert off == normalized


# --- Criterion 2: computed differs from toy on >=1 candidate (fake backend) -

def test_2_computed_differs_from_toy():
    toy = _rec(compute_orbital_order=False)
    fake = _FakeOrbitalBackend(
        OrbitalResult(anisotropy=0.55, polarization=0.81, dominant_orbital="dxy",
                       source="qe:projwfc", provenance="test")
    )
    computed = _rec(compute_orbital_order=True, backend=fake)
    assert computed.orbital_order_source == "computed"
    assert computed.orbital_order_param != toy.orbital_order_param
    assert computed.anisotropy != pytest.approx(toy.anisotropy)


# --- Criterion 3: anti-tautology (moves a pairing outcome not from gate inputs) -

def test_3_anti_tautology_moves_pairing_outcome_not_from_gate_inputs():
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    high = AvenueResult(av, (), {"max_orbital_order": 0.9})
    low = AvenueResult(av, (), {"max_orbital_order": 0.1})
    assert triage(high, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(low, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED
    # orbital_order_param is off-gate: independent of (never re-derivable from)
    # the gate's own scalar inputs (e.g. anisotropy).
    assert is_independent(("orbital_order_param",))
    assert "orbital_order_param" not in GATE_INPUT_CLOSURE
    assert "orbital_order_param" in OFF_GATE_INVARIANTS


# --- Criterion 4: can worsen standing (H7-triplet killed by high P) --------

def test_4_high_orbital_order_worsens_standing_kills_triplet():
    av = _av("H7-triplet", "max_orbital_order", Comparator.GT, 0.5, ("orbital_order_param",))
    res = AvenueResult(av, (), {"max_orbital_order": 0.8})
    out = triage(res, frozenset(HYPOTHESES))
    assert out.verdict == Verdict.KILLED_HYPOTHESIS
    assert out.killed_hypothesis == "H7-triplet"
    assert METRIC_RANGES["max_orbital_order"] == (0.0, 1.0)


# --- Criterion 5: no VALIDATED + Level-2 + provenance correct on every path -

def test_5_no_validated_level2_and_provenance_correct_every_path():
    assert not hasattr(Verdict, "VALIDATED")
    assert not hasattr(Verdict, "CONFIRMED")

    off = _rec(compute_orbital_order=False)
    assert off.evidence_level <= 2
    assert off.orbital_order_source == "toy"

    absent = _rec(compute_orbital_order=True, backend=None)
    assert absent.evidence_level <= 2
    assert absent.orbital_order_source == "absent"

    fake = _FakeOrbitalBackend(
        OrbitalResult(anisotropy=0.4, polarization=0.6, dominant_orbital="dz2",
                       source="qe:projwfc", provenance="test")
    )
    computed = _rec(compute_orbital_order=True, backend=fake)
    assert computed.evidence_level <= 2
    assert computed.orbital_order_source == "computed"


# --- Criterion 6: guardrail -- no positive SC/pairing score on the toy path -

def test_6_no_positive_sc_score_from_orbital_order_on_toy_path():
    # Toggling compute_orbital_order with no backend (absent path) must not move
    # any positive scoring/decision field -- orbital order never contributes a
    # positive SC/pairing score, only an against-triplet off-gate falsifier.
    off = _rec(compute_orbital_order=False)
    absent = _rec(compute_orbital_order=True, backend=None)
    for field in ("sc_plausibility", "credited_sc_lead", "ruled_out",
                  "evidence_level", "surviving_mechanisms", "anisotropy",
                  "coupling", "carrier_proxy"):
        assert getattr(off, field) == getattr(absent, field), field


# --- Criterion 7: golden closure test green (also run directly here) -------

def test_7_golden_closure_pinned_with_orbital_order():
    assert OFF_GATE_INVARIANTS == frozenset({
        "sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev", "sc_mu_star",
        "em_coherence_score", "em_regime", "em_rabi_ev", "em_lifetime_fs",
        "identity_verdict", "identity_established",
        "hudson_regime", "hudson_photon_fraction", "hudson_persistence",
        "hudson_highest_claim", "hudson_supported_levels",
        "field_response_ratio", "em_drive_response",
        "orbital_order_param",
    })
    assert GATE_INPUT_CLOSURE.isdisjoint(OFF_GATE_INVARIANTS)
