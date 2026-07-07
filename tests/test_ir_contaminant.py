import math
import pytest
from orme_lab.ir_contaminant import ContaminantBand, match_score, _band_residual


def _synthetic(name="x", category="route_derived", lo=(1420, 1440), hi=(1480, 1500),
               split=(50, 70), mu=6.856, coupled=True, source="test"):
    return ContaminantBand(name, category, lo, hi, split, mu, coupled, source)


def test_band_residual_inside_is_zero():
    assert _band_residual(1430, (1420, 1440)) == 0.0


def test_band_residual_outside_is_bandwidths():
    # 10 cm^-1 below a 20-wide band -> 0.5 band-widths
    assert _band_residual(1410, (1420, 1440)) == pytest.approx(0.5)
    assert _band_residual(1460, (1420, 1440)) == pytest.approx(1.0)


def test_match_score_dead_centre_is_zero():
    band = _synthetic()
    # lines 1430 / 1490 -> both centred, split 60 centred
    assert match_score((1430.0, 1490.0), band) == pytest.approx(0.0)


def test_match_score_orders_lines():
    band = _synthetic()
    # unordered input must be normalised (min=lo, max=hi)
    assert match_score((1490.0, 1430.0), band) == pytest.approx(0.0)
