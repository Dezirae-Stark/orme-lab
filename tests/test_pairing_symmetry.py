import math
import pytest
from orme_lab.magnetic_field import (
    PairingSymmetry, pauli_limit_tesla, pairing_critical_field, field_response_ratio,
    critical_field_proxy,
)


def test_pauli_limit_is_1_86_tc():
    assert pauli_limit_tesla(10.0) == pytest.approx(18.6)


def test_undetermined_matches_legacy_proxy():
    # UNDETERMINED must reproduce the legacy toy critical field exactly (byte-identical default).
    for spin in (0.0, 0.3, 0.8):
        for coup in (0.2, 0.5, 0.9):
            assert pairing_critical_field(spin, coup, PairingSymmetry.UNDETERMINED) == \
                pytest.approx(critical_field_proxy(spin, coup))


def test_triplet_field_rises_with_spin():
    lo = pairing_critical_field(0.1, 0.6, PairingSymmetry.TRIPLET)
    hi = pairing_critical_field(0.9, 0.6, PairingSymmetry.TRIPLET)
    assert hi > lo  # equal-spin triplet is field-robust: more moment, more critical field


def test_singlet_field_falls_with_spin():
    lo = pairing_critical_field(0.1, 0.6, PairingSymmetry.SINGLET)
    hi = pairing_critical_field(0.9, 0.6, PairingSymmetry.SINGLET)
    assert hi < lo  # singlet: a larger moment pair-breaks -> lower critical field


def test_singlet_capped_at_pauli_when_tc_known():
    # With a Tc, a singlet critical field can never exceed the Pauli limit.
    cf = pairing_critical_field(0.0, 1.0, PairingSymmetry.SINGLET, tc_kelvin=1.0)
    assert cf <= pauli_limit_tesla(1.0) + 1e-9


def test_field_response_ratio_none_without_tc():
    assert field_response_ratio(3.0, None) is None
    assert field_response_ratio(3.0, 0.0) is None


def test_field_response_ratio_gt_one_signals_enhancement():
    # Bc above the Pauli limit -> ratio > 1 -> only triplet can host it.
    r = field_response_ratio(pauli_limit_tesla(2.0) * 1.5, 2.0)
    assert r == pytest.approx(1.5)


from dataclasses import replace
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state


def _rec(symmetry="undetermined", field_t=0.0):
    el = get_element("Ir")
    geo = make_compact_cluster(el, 13)
    cfg = replace(DEFAULT_CONFIG, pairing_symmetry=symmetry, applied_field_t=field_t)
    return evaluate_candidate(el, geo, "high_spin", high_spin_state(el), cfg)


def test_default_symmetry_is_byte_identical():
    # UNDETERMINED default: field_suppression identical to a run with no symmetry concept.
    r = _rec("undetermined", field_t=0.0)
    assert r.pairing_symmetry == "undetermined"
    assert r.field_suppression == pytest.approx(1.0)   # zero field
    assert r.field_response_ratio is None               # no Tc on the toy path


def test_singlet_high_spin_lower_field_than_triplet_under_field():
    s = _rec("singlet", field_t=2.0)
    t = _rec("triplet", field_t=2.0)
    # Under an applied field, a high-spin singlet is suppressed more than a triplet.
    assert s.field_suppression <= t.field_suppression
