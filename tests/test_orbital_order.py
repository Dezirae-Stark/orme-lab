import pytest
from orme_lab.orbital_order import (
    d_polarization, quadrupole_anisotropy, dominant_orbital,
    eg_t2g_imbalance,
)

# real Ir fixture d-occupations (spin-summed, _D_LABELS order): eg (dz2, dx2y2) > t2g
_IR = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)


def test_eg_t2g_zero_for_equal_filling():
    assert eg_t2g_imbalance((0.4,) * 5) == pytest.approx(0.0)


def test_eg_t2g_nonzero_for_cubic_split_ir():
    assert eg_t2g_imbalance(_IR) > 0.0


def test_full_quadrupole_catches_in_plane_redistribution():
    # Codex PR#27 counterexample: dxz/dyz redistribution (dyz=2, dxz=0) is NOT equal-filled
    # (d_polarization=0.25) and Q_zz cancels + eg==t2g, so a Q_zz-only or eg-t2g-only measure
    # would read it isotropic. The FULL quadrupole tensor (Q_xx != Q_yy) must catch it.
    occ = (1.0, 0.0, 2.0, 1.0, 1.0)   # dz2, dxz, dyz, dxy, dx2y2
    assert d_polarization(occ) == pytest.approx(0.25)
    assert eg_t2g_imbalance(occ) == pytest.approx(0.0)     # eg mean == t2g mean here
    assert quadrupole_anisotropy(occ) > 0.0  # gate uses the full quadrupole directly


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
    # _D_LABELS = (dz2, dxz, dyz, dxy, dx2y2); index 2 (dyz) is the max here.
    assert dominant_orbital((0.1, 0.1, 0.9, 0.1, 0.1)) == "dyz"


def test_gate_anisotropy_is_quadrupole_only_cubic_blind():
    # gate reframe: OrbitalResult.anisotropy is the full quadrupole ONLY; for cubic Ir it is 0.0,
    # honestly rank-2 (conservative). eg-t2g no longer enters the gate.
    from orme_lab.epw.orbital_result import OrbitalResult
    ir = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)
    r = OrbitalResult.from_occupations((ir,), source="qe:projwfc")
    assert r.anisotropy == pytest.approx(quadrupole_anisotropy(ir))
    assert r.anisotropy == pytest.approx(0.0, abs=1e-9)
