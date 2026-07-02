"""Tests for the element registry and derived atomic quantities."""

from __future__ import annotations

import pytest

from orme_lab.elements import (
    CORE_SCREEN_SYMBOLS,
    all_elements,
    core_screen_elements,
    get_element,
)


def test_core_screen_has_six_named_elements():
    els = core_screen_elements()
    assert [e.symbol for e in els] == list(CORE_SCREEN_SYMBOLS)
    assert {e.symbol for e in els} == {"Au", "Pt", "Pd", "Ir", "Rh", "Os"}


def test_platinum_ground_state_is_d9s1():
    pt = get_element("Pt")
    assert pt.atomic_number == 78
    assert pt.d_electrons == 9
    assert pt.s_electrons == 1
    assert pt.valence_electrons == 10
    assert pt.d_shell_vacancies == 1


def test_palladium_is_closed_d_shell():
    pd = get_element("Pd")
    assert pd.d_electrons == 10
    assert pd.d_shell_vacancies == 0  # no room for unpaired spins


def test_unknown_element_raises():
    with pytest.raises(KeyError):
        get_element("Xx")


def test_all_elements_sorted_by_atomic_number():
    zs = [e.atomic_number for e in all_elements()]
    assert zs == sorted(zs)
