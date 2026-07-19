import pytest
from orme_lab.electromagnetic_coherence import magnetic_drive_response, DRIVE_BASELINE
from orme_lab.magnetic_field import PairingSymmetry


def test_triplet_with_coherence_and_moment_responds():
    r = magnetic_drive_response(0.8, 0.6, PairingSymmetry.TRIPLET)
    assert r > DRIVE_BASELINE


def test_singlet_has_no_magnetic_drive_channel():
    assert magnetic_drive_response(0.8, 0.6, PairingSymmetry.SINGLET) == 0.0


def test_no_moment_no_drive():
    assert magnetic_drive_response(0.8, 0.0, PairingSymmetry.TRIPLET) == 0.0


def test_no_coherence_no_drive():
    assert magnetic_drive_response(0.0, 0.6, PairingSymmetry.TRIPLET) == 0.0


def test_bounded_unit_interval():
    assert 0.0 <= magnetic_drive_response(1.0, 1.0, PairingSymmetry.TRIPLET) <= 1.0
