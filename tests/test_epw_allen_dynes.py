import math
from orme_lab.epw.allen_dynes import allen_dynes_tc, bcs_gap_mev
from orme_lab.epw.spectral import EliashbergFunction


def test_einstein_golden_A1():
    tc = allen_dynes_tc(1.0, 300.0, 300.0, 0.10)
    assert math.isclose(tc, 21.95067514, rel_tol=1e-6)


def test_mu_star_monotone_A2_A3():
    tcs = [allen_dynes_tc(1.0, 300.0, 300.0, mu) for mu in (0.10, 0.13, 0.16)]
    assert math.isclose(tcs[0], 21.95067514, rel_tol=1e-6)
    assert math.isclose(tcs[1], 18.74239370, rel_tol=1e-6)
    assert math.isclose(tcs[2], 15.69857840, rel_tol=1e-6)
    assert tcs[0] > tcs[1] > tcs[2]


def test_weak_coupling_A4():
    assert math.isclose(allen_dynes_tc(0.5, 400.0, 400.0, 0.10), 4.95218473, rel_tol=1e-6)


def test_strong_coupling_f2_gt_1_A5():
    assert math.isclose(allen_dynes_tc(2.0, 250.0, 300.0, 0.10), 42.67473048, rel_tol=1e-6)


def test_mu_zero_A8():
    assert math.isclose(allen_dynes_tc(1.0, 300.0, 300.0, 0.0), 33.72638610, rel_tol=1e-6)


def test_subcritical_returns_zero_A6_A7():
    assert allen_dynes_tc(0.10, 300.0, 300.0, 0.10) == 0.0
    assert allen_dynes_tc(0.05, 300.0, 300.0, 0.10) == 0.0


def test_just_above_critical_underflow_safe():
    for lam in (0.107, 0.11):
        tc = allen_dynes_tc(lam, 300.0, 300.0, 0.10)
        assert math.isfinite(tc) and 0.0 <= tc < 1e-30


def test_null_inputs_return_zero():
    assert allen_dynes_tc(0.0, 300.0, 300.0, 0.10) == 0.0
    assert allen_dynes_tc(1.0, 0.0, 0.0, 0.10) == 0.0


def test_bcs_gap_linear():
    assert math.isclose(bcs_gap_mev(21.95067514), 3.33672, rel_tol=1e-5)
    assert bcs_gap_mev(0.0) == 0.0


def test_end_to_end_spike_to_tc():
    ef = EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 1.0, abs_tol=1e-9)
    assert math.isclose(wlog, 300.0, abs_tol=1e-9)
    tc = allen_dynes_tc(lam, wlog, w2, 0.10)
    assert math.isclose(tc, 21.95067514, rel_tol=1e-6)
    assert math.isclose(bcs_gap_mev(tc), 3.33672, rel_tol=1e-5)
