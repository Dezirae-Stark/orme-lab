import math
from orme_lab.epw.spectral import EliashbergFunction


def _ef(omega, a2f):
    return EliashbergFunction(omega=tuple(omega), a2f=tuple(a2f))


def test_single_interior_spike_S1():
    ef = _ef([0, 1, 2, 3, 4], [0, 0, 1, 0, 0])   # spike area 1 at w0=2
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 1.0, abs_tol=1e-12)
    assert math.isclose(wlog, 2.0, abs_tol=1e-12)
    assert math.isclose(w2, 2.0, abs_tol=1e-12)


def test_single_interior_spike_S2():
    ef = _ef(list(range(11)), [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0])  # spike 2 at w0=5
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 0.8, abs_tol=1e-12)   # 2*P*dw/w0 = 2*2/5
    assert math.isclose(wlog, 5.0, abs_tol=1e-12)
    assert math.isclose(w2, 5.0, abs_tol=1e-12)


def test_two_spike_distinguishes_wlog_from_w2_S3():
    ef = _ef([0, 1, 2, 3, 4, 5], [0, 2, 0, 0, 2, 0])
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 3.0, abs_tol=1e-10)
    assert math.isclose(wlog, 4 ** (1 / 3), abs_tol=1e-10)
    assert math.isclose(w2, math.sqrt(6), abs_tol=1e-10)


def test_omega_zero_and_ln_guards_finite():
    ef = _ef([0, 0.5, 1.0], [0.0, 0.3, 0.0])
    for v in ef.moments():
        assert math.isfinite(v)
    ef2 = _ef([0, 0.5, 1.0], [9.9, 0.3, 0.0])   # nonzero a2f at omega=0 must not poison
    for v in ef2.moments():
        assert math.isfinite(v)


def test_null_spectrum_returns_zero_not_nan():
    ef = _ef([0, 1, 2, 3], [0, 0, 0, 0])
    lam, wlog, w2 = ef.moments()
    assert lam == 0.0 and wlog == 0.0 and w2 == 0.0


def test_unstable_flag_on_negative_frequency_mass():
    stable = _ef([0, 1, 2, 3], [0, 0, 1, 0])
    unstable = _ef([-2, -1, 0, 1, 2], [1.0, 1.0, 0, 0, 0.2])
    assert stable.unstable is False
    assert unstable.unstable is True
