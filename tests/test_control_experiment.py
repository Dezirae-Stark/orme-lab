"""Tests for the IR-doublet control-experiment predictor (Level-3 laboratory predictions)."""

from __future__ import annotations

import pytest

from orme_lab.evidence import EvidenceLevel
from orme_lab.control_experiment import (
    Prediction,
    predict_isotope_shift,
    _shift_for_bond,
)

PATENT_RH = (1429.53, 1490.99)  # Rh doublet


def test_isotope_shift_13C_carboxylate_redshifts_by_about_33():
    p = predict_isotope_shift(PATENT_RH, "13C", contaminant_bond=("C", "O"),
                              intrinsic_bond=("Rh", "Rh"))
    # 13C on a C-O bond red-shifts the ~1491 line by ~33 cm^-1
    sc = _shift_for_bond(max(PATENT_RH), ("C", "O"), "13C")
    assert sc == pytest.approx(-33.0, abs=1.5)
    assert p.decisive is True
    assert p.evidence_level == EvidenceLevel.LABORATORY_PREDICTION


def test_isotope_shift_18O_carboxylate_redshifts_by_about_36():
    sc = _shift_for_bond(max(PATENT_RH), ("C", "O"), "18O")
    assert sc == pytest.approx(-36.0, abs=1.5)


def test_metal_metal_bond_has_zero_shift_under_CO_label():
    # labelling C/O does nothing to a metal-metal bond -> intrinsic prediction ~0
    assert _shift_for_bond(1490.99, ("Rh", "Rh"), "13C") == 0.0
    assert _shift_for_bond(1490.99, ("Rh", "Rh"), "18O") == 0.0


def test_15N_on_CO_bond_is_not_decisive_neutral_lever():
    # 15N does not test a C-O carboxylate (no nitrogen) -> 0 shift -> not decisive.
    # Proves a discriminator can return decisive=False.
    p = predict_isotope_shift(PATENT_RH, "15N", contaminant_bond=("C", "O"),
                              intrinsic_bond=("Rh", "Rh"))
    assert _shift_for_bond(max(PATENT_RH), ("C", "O"), "15N") == 0.0
    assert p.decisive is False


def test_prediction_is_frozen():
    p = predict_isotope_shift(PATENT_RH, "13C")
    with pytest.raises(Exception):
        p.decisive = False
