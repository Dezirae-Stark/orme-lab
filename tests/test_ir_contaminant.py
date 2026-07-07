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


from orme_lab.ir_contaminant import screen_contaminants, ContaminantMatchResult
from orme_lab.evidence import LAB_CEILING


def test_tight_match_when_all_bands_contain():
    bands = [_synthetic(name="fits", lo=(1420, 1440), hi=(1480, 1500), split=(50, 70))]
    r = screen_contaminants((1430.0, 1490.0), bands)
    assert r.verdict == "tight_match"
    assert r.ranked[0][0] == "fits"
    assert r.evidence_level <= 2


def test_unmatched_when_far_from_every_band():
    bands = [_synthetic(name="a", lo=(1000, 1010), hi=(1020, 1030), split=(10, 20))]
    r = screen_contaminants((1430.0, 1490.0), bands)
    assert r.verdict == "unmatched"


def test_splitting_discriminates_at_equal_position_error():
    # both candidates miss the lines equally, but only `rightsplit` has the right splitting
    rightsplit = _synthetic(name="rightsplit", lo=(1400, 1405), hi=(1515, 1520), split=(55, 65))
    wrongsplit = _synthetic(name="wrongsplit", lo=(1400, 1405), hi=(1515, 1520), split=(100, 110))
    r = screen_contaminants((1430.0, 1490.0), [wrongsplit, rightsplit])
    assert r.ranked[0][0] == "rightsplit"


def test_ranking_is_deterministic_stable_tiebreak():
    # equal score -> route_derived before standard, then name-alphabetical
    b1 = _synthetic(name="zeta", category="route_derived")
    b2 = _synthetic(name="alpha", category="standard")
    r = screen_contaminants((1430.0, 1490.0), [b2, b1])
    assert [n for n, _ in r.ranked] == ["zeta", "alpha"]


def test_result_is_frozen():
    r = screen_contaminants((1430.0, 1490.0), [_synthetic()])
    with pytest.raises(Exception):
        r.verdict = "x"  # frozen dataclass


from orme_lab.ir_contaminant import coupled_stretch, back_out_coupling, coupled_model_for


def test_coupled_roundtrip():
    k, k_int, mu = 10.0, 0.5, 6.856
    nu_sym, nu_asym = coupled_stretch(k, k_int, mu)
    assert nu_asym > nu_sym  # antisymmetric (out-of-phase) is the higher line
    k_back, k_int_back = back_out_coupling(nu_sym, nu_asym, mu)
    assert k_back == pytest.approx(k, rel=1e-6)
    assert k_int_back == pytest.approx(k_int, rel=1e-6)


def test_coupled_model_reports_force_constants():
    band = _synthetic(name="nitrate NO3-", mu=7.464, coupled=True)
    msg = coupled_model_for(band, (1429.53, 1490.99))
    assert "nitrate NO3-" in msg
    assert "mdyne" in msg


def test_coupled_model_not_applicable_for_single_band():
    band = _synthetic(name="water bend", mu=None, coupled=False)
    msg = coupled_model_for(band, (1429.53, 1490.99))
    assert "N/A" in msg or "not a" in msg.lower()


from orme_lab.ir_contaminant import _CONTAMINANTS


def test_library_is_populated_and_well_formed():
    assert len(_CONTAMINANTS) >= 4  # at least the route-derived tier survived sourcing
    for b in _CONTAMINANTS:
        assert b.category in ("route_derived", "standard")
        assert b.lo_band[0] <= b.lo_band[1]
        assert b.hi_band[0] <= b.hi_band[1]
        assert b.split_band[0] <= b.split_band[1]
        assert b.source  # every row cites a source


def test_patent_doublets_run_neutrally():
    # NEUTRAL: assert structure only, never a specific winner.
    for lines in ((1429.53, 1490.99), (1432.09, 1495.17)):
        r = screen_contaminants(lines)
        assert r.verdict in ("tight_match", "plausible_match", "unmatched")
        assert r.evidence_level <= 2
        assert len(r.ranked) == len(_CONTAMINANTS)
        scores = [s for _, s in r.ranked]
        assert scores == sorted(scores)  # ascending / deterministic
