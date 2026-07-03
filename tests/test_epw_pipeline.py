from orme_lab.pipeline import run_screen, evaluate_candidate
from orme_lab.backends import EPWBackend
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.epw.spectral import EliashbergFunction
from orme_lab.evidence import LAB_CEILING


class FakeRunner:
    def __init__(self, ef): self._ef = ef
    def run(self, approx, cfg): return self._ef


def _spike(): return EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))


def _epw_backend():
    b = EPWBackend(runner=FakeRunner(_spike()))
    b.available = lambda: True          # force the gate open for the fake
    return b


def test_no_backend_leaves_sc_columns_toy_and_none():
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=None)
    assert rec.sc_source == "toy" and rec.sc_tc_kelvin is None


def test_epw_backend_populates_tc_fields():
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=_epw_backend())
    assert rec.sc_source == "epw"
    assert rec.sc_tc_kelvin is not None and rec.sc_lambda is not None


def test_evidence_level_never_exceeds_lab_ceiling():
    au = get_element("Au")
    for backend in (None, _epw_backend()):
        rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                                 high_spin_state(au), DEFAULT_CONFIG, backend=backend)
        assert rec.evidence_level <= int(LAB_CEILING)


def test_backend_error_records_failed_and_continues():
    class Boom:
        def run(self, approx, cfg):
            from orme_lab.epw.runner import EPWError
            raise EPWError("boom")
    b = EPWBackend(runner=Boom()); b.available = lambda: True
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=b)
    assert rec.sc_source == "epw:failed" and rec.sc_tc_kelvin is None


def test_screen_toy_columns_identical_with_and_without_epw():
    au = [get_element("Au")]
    toy = run_screen(au, DEFAULT_CONFIG)
    epw = run_screen(au, DEFAULT_CONFIG, backend=_epw_backend())
    for a, b in zip(toy, epw):
        assert a.sc_plausibility == b.sc_plausibility and a.coupling == b.coupling
        assert a.evidence_level == b.evidence_level
