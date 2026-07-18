"""Tests for the mechanism-specific pairing tracks."""
from __future__ import annotations

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.mechanisms import (
    Mechanism,
    evaluate_mechanisms,
    summarize,
    surviving,
)

TH = DEFAULT_CONFIG.thresholds


def _eval(*, coupling=0.657, carrier=0.657, stability=0.333, spin_pol=0.0, em=None, n=13,
          field=1.0, obs=1.0):
    return evaluate_mechanisms(coupling=coupling, carrier_proxy=carrier,
                               structural_stability=stability, field_suppression=field,
                               observable_signal=obs, spin_polarization=spin_pol,
                               em_coherence_score=em, n_atoms=n, thresholds=TH)


def test_field_suppressed_or_unmeasurable_rejects_every_mechanism():
    # Global necessary conditions: a candidate destroyed by an applied field, or with no
    # measurable observable, has no viable SC phase in ANY channel -> zero survivors.
    assert surviving(_eval(spin_pol=0.6, field=0.05)) == ()   # below min_field_tolerance
    assert surviving(_eval(spin_pol=0.0, obs=0.0)) == ()       # below min_observable_signal
    # and the rejection reason names the global condition
    assert "field-suppressed" in _by(_eval(field=0.05), Mechanism.PHONON).rejection


def test_non_finite_field_or_observable_rejects_every_mechanism():
    # A non-finite gate value (NaN critical field under an applied field) must reject: a bare
    # `<` lets NaN through (NaN < x is False) while the generic gate's `NaN >= x` also fails,
    # reintroducing the survivors-vs-all_passed inconsistency this gate prevents.
    nan = float("nan")
    assert surviving(_eval(field=nan)) == ()
    assert surviving(_eval(obs=nan)) == ()
    assert "field-suppressed" in _by(_eval(field=nan), Mechanism.PHONON).rejection


def _by(results, mech):
    return next(m for m in results if m.mechanism == mech.value)


def test_high_spin_rejects_phonon_but_survives_magnetic():
    # The load-bearing case: a large local moment pair-breaks singlet phonon SC, but ENABLES
    # the magnetic channels. High-spin routes out of M_phonon into M_spin_fluctuation/M_triplet.
    r = _eval(spin_pol=0.8)   # Os high-spin
    assert _by(r, Mechanism.PHONON).survives is False
    assert "pair-breaking" in _by(r, Mechanism.PHONON).rejection
    assert _by(r, Mechanism.SPIN_FLUCTUATION).survives is True
    assert _by(r, Mechanism.TRIPLET).survives is True
    assert Mechanism.PHONON.value not in surviving(r)


def test_closed_shell_survives_phonon_not_magnetic():
    # No moment: phonon is available, but there is nothing to mediate a magnetic channel.
    r = _eval(spin_pol=0.0)   # Au / Pd closed-shell
    assert _by(r, Mechanism.PHONON).survives is True
    assert _by(r, Mechanism.SPIN_FLUCTUATION).survives is False
    assert _by(r, Mechanism.TRIPLET).survives is False


def test_phonon_graded_penalty_below_threshold():
    # A modest moment (0.2 < 0.5) still allows phonon but with a reduced plausibility.
    strong = _by(_eval(spin_pol=0.0), Mechanism.PHONON).plausibility
    weak = _by(_eval(spin_pol=0.2), Mechanism.PHONON).plausibility
    assert 0.0 < weak < strong


def test_granular_is_a_sharp_threshold():
    assert _by(_eval(n=1), Mechanism.GRANULAR_JOSEPHSON).survives is False       # single unit
    assert _by(_eval(n=2, coupling=0.1), Mechanism.GRANULAR_JOSEPHSON).survives is False  # E_J/E_C=0.2<1
    assert _by(_eval(n=13, coupling=0.657), Mechanism.GRANULAR_JOSEPHSON).survives is True  # E_J/E_C=8.5


def test_excitonic_needs_em_channel():
    assert _by(_eval(em=None), Mechanism.EXCITONIC_POLARITONIC).survives is False
    assert _by(_eval(em=0.2), Mechanism.EXCITONIC_POLARITONIC).survives is False   # below floor
    assert _by(_eval(em=0.8), Mechanism.EXCITONIC_POLARITONIC).survives is True


def test_surrogates_are_labelled():
    r = _eval(spin_pol=0.6)
    assert _by(r, Mechanism.SPIN_FLUCTUATION).is_surrogate is True
    assert _by(r, Mechanism.TRIPLET).is_surrogate is True
    assert _by(r, Mechanism.EXCITONIC_POLARITONIC).is_surrogate is True
    assert _by(r, Mechanism.PHONON).is_surrogate is False           # established physics
    assert _by(r, Mechanism.GRANULAR_JOSEPHSON).is_surrogate is False


def test_evaluate_is_deterministic_and_ordered():
    a = _eval(spin_pol=0.6)
    b = _eval(spin_pol=0.6)
    assert a == b
    assert [m.mechanism for m in a] == [
        Mechanism.PHONON.value, Mechanism.SPIN_FLUCTUATION.value, Mechanism.TRIPLET.value,
        Mechanism.EXCITONIC_POLARITONIC.value, Mechanism.GRANULAR_JOSEPHSON.value,
    ]


def test_summary_names_survivors_and_rejections():
    s = summarize(_eval(spin_pol=0.8))
    assert "M_spin_fluctuation" in s and "M_phonon✗" in s


# ---- pipeline integration: crediting requires a surviving mechanism ----
from orme_lab.pipeline import evaluate_candidate
from orme_lab.identity import IdentityWitness
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state


def _cand(sym, identity=None):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG, identity=identity)


def test_high_spin_candidate_credits_via_magnetic_not_phonon():
    # The resolution of the high-spin ⊥ singlet-EPW tension, end to end.
    w = IdentityWitness("Os", "metallic", "sub-nm-cluster", 0.0, ("XRD",))
    r = _cand("Os", identity=w)                       # Os high-spin: spin_pol 0.8
    assert "M_phonon" not in r.surviving_mechanisms   # pair-broken out of the phonon channel
    assert "M_spin_fluctuation" in r.surviving_mechanisms
    assert r.credited_sc_lead is True                 # credited via a magnetic mechanism


def test_closed_shell_candidate_credits_via_phonon():
    w = IdentityWitness("Au", "metallic", "sub-nm-cluster", 0.0, ("XRD",))
    r = _cand("Au", identity=w)                        # Au closed-shell: spin_pol 0.0
    assert "M_phonon" in r.surviving_mechanisms
    assert "M_spin_fluctuation" not in r.surviving_mechanisms
    assert r.credited_sc_lead is True


def test_mechanisms_reported_even_when_not_credited():
    r = _cand("Os")                                   # no identity witness
    assert r.credited_sc_lead is False                # identity unestablished
    assert r.surviving_mechanisms                     # ...but the mechanism analysis is still reported
    assert "M_phonon" not in r.surviving_mechanisms


# ---- creditable-mechanism filter by pairing symmetry ----
from orme_lab.mechanisms import creditable_under, filter_by_symmetry
from orme_lab.magnetic_field import PairingSymmetry
from orme_lab.config import ModelThresholds


def test_creditable_sets_partition_by_symmetry():
    assert Mechanism.TRIPLET in creditable_under(PairingSymmetry.TRIPLET)
    assert Mechanism.PHONON not in creditable_under(PairingSymmetry.TRIPLET)
    assert Mechanism.PHONON in creditable_under(PairingSymmetry.SINGLET)
    assert Mechanism.TRIPLET not in creditable_under(PairingSymmetry.SINGLET)
    # UNDETERMINED credits everything (default, unchanged)
    assert set(creditable_under(PairingSymmetry.UNDETERMINED)) == set(Mechanism)


def test_filter_removes_incompatible_survivors():
    th = ModelThresholds()
    # high spin + good coupling: _triplet survives, _phonon is pair-broken
    results = evaluate_mechanisms(
        coupling=0.6, carrier_proxy=0.5, structural_stability=0.5,
        field_suppression=1.0, observable_signal=0.5,
        spin_polarization=0.8, em_coherence_score=None, n_atoms=13, thresholds=th)
    singlet = filter_by_symmetry(results, PairingSymmetry.SINGLET)
    # under the singlet assumption the surviving triplet track is NOT creditable
    assert all(m.mechanism != Mechanism.TRIPLET.value for m in singlet if m.survives)
