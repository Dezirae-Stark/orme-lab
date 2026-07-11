"""Tests for uncertainty propagation + rank stability."""
from __future__ import annotations

from dataclasses import replace

from orme_lab.pipeline import run_screen
from orme_lab.uncertainty import (
    ScoreDistribution,
    analytic_interval,
    missing_data_penalty,
    propagate_mc,
)


def test_mc_is_reproducible_with_fixed_seed():
    a = propagate_mc(n=32, seed=0)
    b = propagate_mc(n=32, seed=0)
    assert a == b                      # byte-identical (determinism charter)
    assert all(isinstance(d, ScoreDistribution) for d in a)


def test_distributions_are_well_formed():
    dists = propagate_mc(n=32, seed=0)
    assert dists, "screen produced no distributions"
    for d in dists:
        assert d.p5 <= d.p50 <= d.p95
        assert d.std >= 0.0
        assert 0.0 <= d.rank1_fraction <= 1.0
        assert d.rank_p5 <= d.rank_p95
        assert d.n == 32 and d.seed == 0


def test_exactly_one_rank_one_per_draw():
    # The stable tie-break picks a single #1 each draw, so rank1_fraction sums to ~1.
    dists = propagate_mc(n=32, seed=0)
    assert abs(sum(d.rank1_fraction for d in dists) - 1.0) < 1e-9


def test_a_passing_candidate_shows_real_spread_in_both_legs():
    # A compact-cluster candidate sits near the gate floors, so perturbing thresholds
    # moves its score — MC AND the analytic cross-check should both register that.
    dists = propagate_mc(n=64, seed=0)
    spread = [d for d in dists if d.p95 > d.p5]
    assert spread, "no candidate showed any score spread under threshold perturbation"
    d = spread[0]
    lo, hi = analytic_interval(d.key)
    assert lo <= hi
    assert (hi - lo) > 0.0            # analytic sensitivity agrees there is spread


def test_different_seed_gives_different_draws_but_stable_top_mean():
    a = propagate_mc(n=48, seed=0)
    b = propagate_mc(n=48, seed=1)
    assert a != b                      # different random draws
    # the top candidate's mean score is stable across seeds (within a loose tolerance)
    assert abs(a[0].mean - b[0].mean) < 0.02


def test_missing_data_penalty_widens_underconstrained():
    rec = run_screen()[0]              # toy path -> no EPW value
    assert missing_data_penalty(rec) == 1.5
    constrained = replace(rec, sc_source="epw", sc_tc_kelvin=7.9)
    assert missing_data_penalty(constrained) == 1.0
