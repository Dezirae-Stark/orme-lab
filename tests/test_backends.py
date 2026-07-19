"""Tests for the ab-initio backend interfaces and their pipeline wiring."""

from __future__ import annotations

import pytest

from orme_lab.backends import (
    BACKENDS,
    ASEBackend,
    Capability,
    DFTBackend,
    PySCFBackend,
    available_backends,
    get_backend,
    implemented,
    list_backends,
)
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster, make_monomer
from orme_lab.pipeline import evaluate_candidate, run_screen
from orme_lab.spin_states import high_spin_state


def test_registry_contains_the_seven_spec_backends():
    assert set(BACKENDS) == {"ase", "pyscf", "gpaw", "orca", "nwchem",
                             "quantum-espresso", "epw"}
    assert len(list_backends()) == 7


def test_stub_adapters_implement_nothing_and_seams_raise():
    bk = get_backend("pyscf")
    # declared != implemented: PySCF declares capabilities but wires none yet
    assert Capability.SPIN_STATE in bk.declared_capabilities
    assert not bk.provides(Capability.SPIN_STATE)
    assert bk.capabilities() == frozenset()
    with pytest.raises(NotImplementedError):
        bk.density_anisotropy(high_spin_state(get_element("Os")))


def test_availability_probes_dependencies():
    # Availability is a REAL probe of installed tools, not an environment
    # assumption: ASE/PySCF need absent Python packages, so they are False
    # regardless of what else is installed.
    assert ASEBackend.available() is False
    assert PySCFBackend.available() is False
    # the abstract base has no requirements and is never "available"
    assert DFTBackend.available() is False
    # available_backends() reports EXACTLY those whose deps are present here
    # (empty on a bare box; installing e.g. Quantum ESPRESSO flips entries on --
    # see the available_backends docstring). Verify the mechanism, not the ambient
    # state: every listed backend is genuinely available, and deps-absent ones are
    # excluded.
    avail = available_backends()
    for name in avail:
        assert BACKENDS[name].available() is True
    assert "ase" not in avail
    assert "pyscf" not in avail


def test_unknown_backend_raises():
    with pytest.raises(KeyError):
        get_backend("vasp")


def test_no_backend_is_identical_to_toy_pipeline():
    a = run_screen()
    b = run_screen(backend=None)
    assert [r.as_csv_row() for r in a] == [r.as_csv_row() for r in b]


class _FakeCouplingBackend(DFTBackend):
    """A backend that genuinely implements ONE seam (coupling)."""

    name = "fake"
    declared_capabilities = frozenset({Capability.INTER_UNIT_COUPLING})

    @implemented(Capability.INTER_UNIT_COUPLING)
    def inter_unit_coupling(self, geometry):
        return 0.123  # deterministic sentinel


def test_implemented_capability_overrides_toy_value():
    fake = _FakeCouplingBackend()
    assert fake.provides(Capability.INTER_UNIT_COUPLING)
    assert fake.capabilities() == frozenset({Capability.INTER_UNIT_COUPLING})

    pt = get_element("Pt")
    rec = evaluate_candidate(
        pt, make_compact_cluster(pt, 13), "high_spin",
        high_spin_state(pt), DEFAULT_CONFIG, backend=fake,
    )
    assert rec.coupling == 0.123  # backend value used, not the toy score


def test_unimplemented_capability_falls_back_to_toy():
    # ASE stub provides no coupling implementation -> toy coupling is used.
    pt = get_element("Pt")
    geom = make_compact_cluster(pt, 13)
    toy = evaluate_candidate(pt, geom, "high_spin", high_spin_state(pt), DEFAULT_CONFIG)
    with_stub = evaluate_candidate(
        pt, geom, "high_spin", high_spin_state(pt), DEFAULT_CONFIG, backend=ASEBackend()
    )
    assert with_stub.coupling == toy.coupling


def test_new_capabilities_are_unimplemented_stubs():
    b = DFTBackend()
    assert not b.provides(Capability.NON_PHONON_PAIRING)
    assert not b.provides(Capability.SPIN_DRIVE_RESPONSE)
    with pytest.raises(NotImplementedError):
        b.non_phonon_pairing(None, None, None)
    with pytest.raises(NotImplementedError):
        b.spin_drive_response(None, None, None)


def test_fake_backend_can_change_the_verdict():
    # A monomer is ruled out on coupling; a backend forcing high coupling lifts
    # that specific gate (others may still fail — we only check the gate value).
    class HighCoupling(DFTBackend):
        name = "hc"
        @implemented(Capability.INTER_UNIT_COUPLING)
        def inter_unit_coupling(self, geometry):
            return 0.9

    au = get_element("Au")
    rec = evaluate_candidate(
        au, make_monomer(au), "high_spin", high_spin_state(au), DEFAULT_CONFIG,
        backend=HighCoupling(),
    )
    assert rec.coupling == 0.9
    assert not rec.isolated  # coupling gate no longer flags it isolated
