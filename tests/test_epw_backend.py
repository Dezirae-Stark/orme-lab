import math
from orme_lab.backends import Capability, get_backend, EPWBackend
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster, make_monomer
from orme_lab.spin_states import high_spin_state
from orme_lab.epw.spectral import EliashbergFunction


class FakeRunner:
    """Returns a canned .a2f-equivalent spectrum (bypasses binaries)."""
    def __init__(self, ef):
        self._ef = ef
    def run(self, approx, cfg):
        return self._ef


class FakeRunnerText:
    def run(self, approx, cfg):   # emulate a raw-text runner path
        raise AssertionError("not used")


def _spike_ef():
    return EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))


def test_epw_backend_provides_only_sc_gap():
    b = EPWBackend()
    assert b.provides(Capability.SC_GAP) is True
    assert b.provides(Capability.INTER_UNIT_COUPLING) is False
    assert b.capabilities() == frozenset({Capability.SC_GAP})


def test_superconducting_gap_computes_tc_via_injected_runner():
    b = EPWBackend(runner=FakeRunner(_spike_ef()))
    au = get_element("Au")
    r = b.superconducting_gap(au, make_compact_cluster(au, 13), high_spin_state(au))
    assert r.source == "epw"
    assert math.isclose(r.tc_kelvin, 21.95067514, rel_tol=1e-6)


def test_monomer_returns_not_applicable():
    b = EPWBackend(runner=FakeRunner(_spike_ef()))
    au = get_element("Au")
    r = b.superconducting_gap(au, make_monomer(au), high_spin_state(au))
    assert r.source == "n/a" and r.tc_kelvin is None


def test_runner_failure_returns_failed_not_raise():
    class Boom:
        def run(self, approx, cfg):
            from orme_lab.epw.runner import EPWError
            raise EPWError("scf blew up")
    b = EPWBackend(runner=Boom())
    au = get_element("Au")
    r = b.superconducting_gap(au, make_compact_cluster(au, 13), high_spin_state(au))
    assert r.source == "epw:failed" and r.tc_kelvin is None


def test_get_backend_forwards_runner_kwarg():
    b = get_backend("epw", runner=FakeRunner(_spike_ef()))
    assert isinstance(b, EPWBackend)
