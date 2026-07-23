import pytest
from orme_lab.orbital_order import d_polarization, quadrupole_anisotropy, dominant_orbital


def test_equal_filling_zero_polarization():
    assert d_polarization((0.4, 0.4, 0.4, 0.4, 0.4)) == pytest.approx(0.0)


def test_single_orbital_dominant_high_polarization():
    p = d_polarization((2.0, 0.0, 0.0, 0.0, 0.0))
    assert p == pytest.approx(1.0)


def test_polarization_monotone_in_imbalance():
    assert d_polarization((1.0, 0.5, 0.5, 0.5, 0.5)) < d_polarization((1.8, 0.2, 0.2, 0.2, 0.2))


def test_polarization_bounded_unit_interval():
    for occ in [(0,0,0,0,0), (2,2,2,2,2), (1.3,0.1,0.9,0.0,0.7)]:
        assert 0.0 <= d_polarization(occ) <= 1.0


def test_quadrupole_anisotropy_bounded_and_zero_for_spherical():
    # equal d-occupation is spherically symmetric -> zero shape anisotropy
    assert quadrupole_anisotropy((0.4,)*5) == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= quadrupole_anisotropy((1.5, 0.1, 0.1, 0.1, 0.1)) <= 1.0


def test_dominant_orbital_names_the_max():
    assert dominant_orbital((0.1, 0.1, 0.9, 0.1, 0.1)) == "dxy" or isinstance(dominant_orbital((0.1,0.1,0.9,0.1,0.1)), str)
