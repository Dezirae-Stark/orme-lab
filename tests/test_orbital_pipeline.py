"""Task 6: pipeline wiring for the orbital-order seam -- gated, default byte-identical,
provenance-tagged. See docs/superpowers/plans/2026-07-23-orbital-order-descriptor.md."""

import dataclasses

import pytest

from orme_lab.backends import Capability, DFTBackend, implemented
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.epw.orbital_result import OrbitalResult
from orme_lab.geometry import make_compact_cluster
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state


class _FakeOrbitalBackend(DFTBackend):
    name = "fake-orbital"
    description = "test double: canned OrbitalResult"
    declared_capabilities = frozenset({Capability.ORBITAL_ORDER})
    binary_requires = ("fake-projwfc",)

    def __init__(self, orbital):
        self._orbital = orbital

    @classmethod
    def available(cls) -> bool:
        return True

    @implemented(Capability.ORBITAL_ORDER)
    def orbital_order(self, element, geometry, state):
        return self._orbital


def _rec(compute_orbital_order, backend=None):
    el = get_element("Ir")
    geo = make_compact_cluster(el, 13)
    state = high_spin_state(el)
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_orbital_order=compute_orbital_order)
    return evaluate_candidate(el, geo, "high_spin", state, cfg, backend=backend)


def test_default_path_byte_identical_and_inert():
    r = _rec(compute_orbital_order=False)
    assert r.orbital_order_param is None
    assert r.orbital_order_source == "toy"


def test_flag_on_without_backend_is_absent_not_fabricated():
    r = _rec(compute_orbital_order=True, backend=None)
    assert r.orbital_order_param is None
    assert r.orbital_order_source == "absent"


def test_computed_overrides_anisotropy_and_sets_param():
    fake = _FakeOrbitalBackend(
        OrbitalResult(anisotropy=0.42, polarization=0.77, dominant_orbital="dxy",
                       source="qe:projwfc", provenance="test")
    )
    r = _rec(compute_orbital_order=True, backend=fake)
    assert r.orbital_order_source == "computed"
    assert r.orbital_order_param == pytest.approx(0.77)
    assert r.anisotropy == pytest.approx(fake._orbital.anisotropy)
