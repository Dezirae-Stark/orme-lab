"""Regression tests for the PR #28 review findings (Codex):
P1 — the clean-limit gate must be ENFORCED at the decision layer, not merely diagnostic: a
     dirty/inadmissible candidate must not be able to register an unconventional signature
     (kill H7-singlet via field enhancement). The enhancement kill consults the clean-limit-gated
     `field_response_ratio_admissible` (None when inadmissible); the suppression kill (H7-triplet)
     keeps the raw `field_response_ratio` (admissibility-independent).
P2 — R_Pauli must be computed from the backend's real Hc2 when FIELD_RESPONSE is provided, not the
     stale toy triplet proxy.
"""
from dataclasses import replace

import pytest

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.backends import DFTBackend, Capability
from orme_lab.epw.result import EPWResult
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator
from orme_lab.lab_loop.runner import AvenueResult, _metrics
from orme_lab.lab_loop.triage import triage, Verdict
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, is_independent

_EL = get_element("Ir")
_GEO = make_compact_cluster(_EL, 13)
_ST = high_spin_state(_EL)


class _ScGap(DFTBackend):
    """SC_GAP-only backend returning a chosen Tc (toy triplet field drives R_Pauli)."""
    def __init__(self, tc): self._tc = tc
    @classmethod
    def available(cls) -> bool: return True
    def provides(self, cap) -> bool: return cap == Capability.SC_GAP
    def superconducting_gap(self, e, g, s):
        return EPWResult(self._tc, 1.0, 100.0, 100.0, 1.0, 0.1, "epw", False, "t")


class _FieldAndGap(DFTBackend):
    """Provides BOTH FIELD_RESPONSE (a real Hc2) and SC_GAP (a Tc)."""
    def __init__(self, hc2, tc): self._hc2, self._tc = hc2, tc
    @classmethod
    def available(cls) -> bool: return True
    def provides(self, cap) -> bool: return cap in (Capability.FIELD_RESPONSE, Capability.SC_GAP)
    def critical_field(self, spin, coupling): return self._hc2
    def superconducting_gap(self, e, g, s):
        return EPWResult(self._tc, 1.0, 100.0, 100.0, 1.0, 0.1, "epw", False, "t")


# ---- P1: the gate is enforced at the decision layer ------------------------------------------

def test_admissible_metric_is_offgate_and_ranged():
    from orme_lab.lab_loop.avenue import METRIC_RANGES
    assert "field_response_ratio_admissible" in OFF_GATE_INVARIANTS
    assert is_independent(("field_response_ratio_admissible",))
    assert "max_field_response_ratio_admissible" in METRIC_RANGES


def test_dirty_candidate_admissible_ratio_is_none():
    dirty = evaluate_candidate(_EL, _GEO, "high_spin", _ST,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=False), backend=_ScGap(0.1))
    assert dirty.field_response_ratio is not None and dirty.field_response_ratio > 1.0  # raw enh present
    assert dirty.unconventional_admissible is False
    assert dirty.field_response_ratio_admissible is None    # gated OFF -> cannot register enhancement


def test_clean_candidate_admissible_ratio_present():
    clean = evaluate_candidate(_EL, _GEO, "high_spin", _ST,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=True), backend=_ScGap(0.1))
    assert clean.unconventional_admissible is True
    assert clean.field_response_ratio_admissible is not None and clean.field_response_ratio_admissible > 1.0


def _singlet_enhancement_av():
    a = ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, True, False, None, "singlet")
    return Avenue("a", Tier.TIER1, "d", "H7-singlet", a,
                  FalsificationCondition("max_field_response_ratio_admissible", Comparator.GT, 1.0),
                  ("field_response_ratio_admissible",), "enhancement kill (clean-limit-gated)")


def test_dirty_cannot_kill_h7_singlet_via_enhancement():
    # decision-layer enforcement: a dirty candidate (admissible metric None) does NOT register the
    # unconventional signature -> H7-singlet survives (INCONCLUSIVE, absent evidence never fires).
    av = _singlet_enhancement_av()
    dirty_metrics = _metrics((evaluate_candidate(_EL, _GEO, "high_spin", _ST,
        replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=False), backend=_ScGap(0.1)),))
    res = AvenueResult(av, (), dirty_metrics)
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.INCONCLUSIVE


def test_clean_admissible_kills_h7_singlet_via_enhancement():
    av = _singlet_enhancement_av()
    clean_metrics = _metrics((evaluate_candidate(_EL, _GEO, "high_spin", _ST,
        replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=True), backend=_ScGap(0.1)),))
    res = AvenueResult(av, (), clean_metrics)
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS


# ---- P2: R_Pauli uses the backend Hc2 when provided ------------------------------------------

def test_r_pauli_uses_backend_hc2_not_toy_proxy():
    # backend Hc2 = 0.1 T, Tc = 1.0 K -> Bp = 1.86 T -> R_Pauli ~ 0.054 <= 1 (Pauli-limited).
    # The stale toy triplet field would give R_Pauli > 1 and wrongly admit unconventional; the fix
    # uses the backend Hc2, so even clean + big Borb stays inadmissible.
    rec = evaluate_candidate(_EL, _GEO, "high_spin", _ST,
              replace(DEFAULT_CONFIG, b_orb_tesla=500.0, is_clean_limit=True),
              backend=_FieldAndGap(hc2=0.1, tc=1.0))
    assert rec.field_response_ratio is not None and rec.field_response_ratio <= 1.0
    assert rec.unconventional_admissible is False
    assert rec.field_response_ratio_admissible is None
