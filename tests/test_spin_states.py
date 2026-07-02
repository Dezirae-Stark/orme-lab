"""Tests for spin-state construction and the spin-polarization score."""

from __future__ import annotations

from orme_lab.elements import get_element
from orme_lab.spin_states import (
    high_spin_state,
    low_spin_state,
    max_unpaired_electrons,
    spin_polarization_score,
)


def test_high_spin_half_filled_shell_is_maximal():
    # A d5 element would give 5 unpaired; Os is d6 -> 10-6 = 4 unpaired.
    os = get_element("Os")
    assert max_unpaired_electrons(os) == 4
    state = high_spin_state(os)
    assert state.unpaired_electrons == 4
    assert state.is_high_spin


def test_closed_shell_has_no_unpaired_and_zero_score():
    pd = get_element("Pd")  # d10, closed shell
    hs = high_spin_state(pd)
    assert hs.unpaired_electrons == 0
    assert spin_polarization_score(hs) == 0.0


def test_spin_polarization_score_is_bounded():
    for sym in ("Au", "Pt", "Pd", "Ir", "Rh", "Os"):
        el = get_element(sym)
        for state in (high_spin_state(el), low_spin_state(el)):
            score = spin_polarization_score(state)
            assert 0.0 <= score <= 1.0


def test_high_spin_at_least_as_polarized_as_low_spin():
    for sym in ("Au", "Pt", "Ir", "Rh", "Os"):
        el = get_element(sym)
        hs = spin_polarization_score(high_spin_state(el))
        ls = spin_polarization_score(low_spin_state(el))
        assert hs >= ls


def test_spin_only_moment_monotonic_in_unpaired():
    ir = get_element("Ir")
    hs = high_spin_state(ir)
    ls = low_spin_state(ir)
    assert hs.spin_only_moment_bohr >= ls.spin_only_moment_bohr
    assert hs.multiplicity == hs.unpaired_electrons + 1
