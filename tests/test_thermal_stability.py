# tests/test_thermal_stability.py
import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.thermal_stability import screen_thermal


def test_tammann_temperature_ir():
    # Ir T_m 2446 C -> Tammann 0.5*(2446+273.15)-273.15 = 1086.4 C.
    assert screen_thermal("Ir", 1200.0).t_tammann_c == pytest.approx(1086.4, abs=1.0)


def test_ir_1200_exceeds_envelope():
    assert screen_thermal("Ir", 1200.0).verdict == "exceeds_envelope"


def test_ir_800_marginal():
    assert screen_thermal("Ir", 800.0).verdict == "marginal"


def test_au_800_exceeds_for_low_melting_metal():
    # Au T_m 1064 C -> Tammann ~395 C; 800 C is above it -> anomalous for Au.
    assert screen_thermal("Au", 800.0).verdict == "exceeds_envelope"


def test_os_500_within_envelope():
    assert screen_thermal("Os", 500.0).verdict == "within_refractory_envelope"


def test_evidence_clamped():
    assert screen_thermal("Ir", 1200.0).evidence_level <= LAB_CEILING
