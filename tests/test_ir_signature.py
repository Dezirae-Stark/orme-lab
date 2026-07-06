import math

import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.ir_signature import (
    WAVENUMBER_CONST,
    screen_ir_doublet,
    wavenumber,
    required_force_constant,
)


def test_wavenumber_calibration_co():
    # C=O harmonic: k~18.6 mdyne/A, mu(C,O)=6.86 amu -> ~2145 cm^-1 (obs ~2143).
    mu_co = (12.011 * 15.999) / (12.011 + 15.999)
    assert wavenumber(18.6, mu_co) == pytest.approx(2145, rel=0.03)


def test_required_force_constant_rh_line():
    # Rh homodimer mu = 102.905/2; upper patent line 1490.99 cm^-1 -> ~67.4 mdyne/A.
    k = required_force_constant(1490.99, 102.905 / 2)
    assert k == pytest.approx(67.4, rel=0.02)


def test_patent_doublet_excludes_metal_metal():
    r = screen_ir_doublet("Rh", (1429.53, 1490.99))
    assert r.metal_band_cm[1] < 500.0        # Rh-Rh cannot exceed ~406 cm^-1
    assert r.verdict == "light_atom_consistent"
    assert r.reachable_by_family["C–O / C=O"] == (True, True)


def test_low_doublet_stays_metal_consistent():
    # A genuinely metal-range doublet must flip the verdict — the ruler can fail.
    r = screen_ir_doublet("Rh", (200.0, 300.0))
    assert r.verdict == "metal_bond_consistent"


def test_evidence_clamped():
    r = screen_ir_doublet("Rh", (1429.53, 1490.99))
    assert r.evidence_level <= LAB_CEILING
