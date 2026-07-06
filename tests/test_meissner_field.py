# tests/test_meissner_field.py
import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.meissner_field import (
    EARTH_FIELD_T,
    penetration_depth,
    screen_meissner,
    superfluid_density,
)


def test_penetration_depth_at_earth_field():
    # Hc1 = 50 uT, ln kappa = 1 -> lambda ~ 1.81 um.
    assert penetration_depth(EARTH_FIELD_T) == pytest.approx(1.814e-6, rel=0.01)


def test_superfluid_density_at_earth_field():
    n = superfluid_density(penetration_depth(EARTH_FIELD_T))
    assert n == pytest.approx(8.58e24, rel=0.02)


def test_patent_claim_is_in_tension_with_isolation():
    assert screen_meissner(EARTH_FIELD_T, isolated_premise=True).verdict == "in_tension_with_isolation"


def test_coupled_density_is_physical():
    assert screen_meissner(EARTH_FIELD_T, isolated_premise=False).verdict == "implied_density_physical"


def test_tiny_field_gives_unphysical_density():
    # Absurdly small Hc1 -> huge lambda -> vanishing n_s -> outside physical bounds.
    assert screen_meissner(1e-12, isolated_premise=False).verdict == "implied_density_unphysical"


def test_evidence_clamped():
    assert screen_meissner(EARTH_FIELD_T).evidence_level <= LAB_CEILING
