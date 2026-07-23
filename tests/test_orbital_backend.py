import pytest

from orme_lab.backends import Capability, QuantumEspressoBackend
from orme_lab.epw.orbital_result import OrbitalResult


def test_orbital_result_from_occupations_aggregates():
    r = OrbitalResult.from_occupations(
        ((2.0, 0.0, 0.0, 0.0, 0.0), (2.0, 0.0, 0.0, 0.0, 0.0)), source="epw"
    )
    assert r.polarization == pytest.approx(1.0)
    assert 0.0 <= r.anisotropy <= 1.0
    assert r.provenance and r.source == "epw"


def test_qe_backend_declares_orbital_order():
    assert Capability.ORBITAL_ORDER in QuantumEspressoBackend.declared_capabilities
    assert "projwfc.x" in QuantumEspressoBackend.binary_requires
