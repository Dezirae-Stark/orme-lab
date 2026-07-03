import math
from orme_lab.epw.result import EPWResult
from orme_lab.epw.spectral import EliashbergFunction


def test_toy_absent_all_none():
    r = EPWResult.toy_absent()
    assert r.source == "toy" and r.tc_kelvin is None and r.gap_mev is None


def test_not_applicable_and_failed():
    assert EPWResult.not_applicable("monomer").source == "n/a"
    assert EPWResult.failed("scf did not converge").source == "epw:failed"


def test_from_eliashberg_stable():
    ef = EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))
    r = EPWResult.from_eliashberg(ef, mu_star=0.10, provenance="fcc-Pb approximant")
    assert r.source == "epw"
    assert math.isclose(r.tc_kelvin, 21.95067514, rel_tol=1e-6)
    assert math.isclose(r.lam, 1.0, abs_tol=1e-9)
    assert r.mu_star == 0.10 and r.unstable is False


def test_from_eliashberg_unstable_gives_none_tc():
    ef = EliashbergFunction(omega=(-2, -1, 0, 1, 2), a2f=(1.0, 1.0, 0, 0, 0.2))
    r = EPWResult.from_eliashberg(ef, mu_star=0.10, provenance="unstable")
    assert r.source == "epw:unstable" and r.tc_kelvin is None and r.unstable is True
