"""Tests for the structural distribution ('monatomic' as a measured mixture)."""
from __future__ import annotations

import math

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster, make_dimer, make_monomer
from orme_lab.spin_states import high_spin_state
from orme_lab.structure import (
    StructuralDistribution,
    dispersed_sample,
    evaluate_sample,
    make_distribution,
)

PT = get_element("Pt")
MONO = make_monomer(PT)
DIMER = make_dimer(PT)
CLUST = make_compact_cluster(PT, 13)


def test_make_distribution_normalizes():
    d = make_distribution([(MONO, 2.0), (CLUST, 2.0)])   # unnormalized weights
    assert isinstance(d, StructuralDistribution)
    assert math.isclose(sum(p.fraction for p in d.populations), 1.0)
    assert all(math.isclose(p.fraction, 0.5) for p in d.populations)


def test_f1_and_size_distribution():
    d = make_distribution([(MONO, 0.8), (DIMER, 0.15), (CLUST, 0.05)])
    assert math.isclose(d.f1(), 0.8)
    sd = d.size_distribution()
    assert math.isclose(sd[1], 0.8) and math.isclose(sd[2], 0.15) and math.isclose(sd[13], 0.05)


def test_expected_coupling_is_coverage_weighted():
    th = DEFAULT_CONFIG.thresholds
    # monomer-only -> 0 coupling; cluster-only -> the cluster's coupling; mixture in between
    assert make_distribution([(MONO, 1.0)]).expected_coupling(th) == 0.0
    c_clust = make_distribution([(CLUST, 1.0)]).expected_coupling(th)
    assert c_clust > 0.0
    mix = make_distribution([(MONO, 0.5), (CLUST, 0.5)]).expected_coupling(th)
    assert math.isclose(mix, 0.5 * c_clust)


def test_evaluate_sample_survivor_is_only_the_cluster_tail():
    # A mostly-monomer sample: monomers are ruled out (no coupling), so the surviving
    # fraction is only the cluster populations that pass the gate.
    d = make_distribution([(MONO, 0.82), (DIMER, 0.14), (CLUST, 0.04)])
    s = evaluate_sample(PT, d, "high_spin", high_spin_state(PT), DEFAULT_CONFIG)
    assert math.isclose(s.f1, 0.82)
    assert len(s.populations) == 3
    mono_v = next(p for p in s.populations if p.n_atoms == 1)
    assert mono_v.ruled_out is True and mono_v.sc_plausibility == 0.0
    # surviving fraction = sum of not-ruled-out populations; <= 1 and excludes the monomers
    assert 0.0 <= s.surviving_fraction <= 0.18
    assert s.expected_coupling >= 0.0


def test_credited_fraction_needs_identity_witness():
    from orme_lab.identity import IdentityWitness
    d = make_distribution([(MONO, 0.5), (CLUST, 0.5)])
    # no witness -> nothing credited, even the surviving cluster (consistent w/ per-candidate layer)
    s0 = evaluate_sample(PT, d, "high_spin", high_spin_state(PT), DEFAULT_CONFIG)
    assert s0.credited_fraction == 0.0
    assert s0.surviving_fraction > 0.0
    # a metallic witness for the whole sample -> the surviving fraction becomes credited
    w = IdentityWitness("Pt", "metallic", "sub-nm-cluster", 0.0, ("XRD", "XPS"))
    s1 = evaluate_sample(PT, d, "high_spin", high_spin_state(PT), DEFAULT_CONFIG, identity=w)
    assert s1.credited_fraction == s1.surviving_fraction
    assert s1.credited_fraction > 0.0


def test_all_zero_weights_fall_back_to_uniform():
    d = make_distribution([(MONO, 0.0), (CLUST, 0.0)])
    assert math.isclose(sum(p.fraction for p in d.populations), 1.0)
    assert all(math.isclose(p.fraction, 0.5) for p in d.populations)


def test_dispersed_sample_factory():
    d = dispersed_sample(PT, f1=0.9)
    assert math.isclose(d.f1(), 0.9)
    assert math.isclose(sum(p.fraction for p in d.populations), 1.0)


def test_evaluate_sample_is_deterministic():
    d = make_distribution([(MONO, 0.5), (CLUST, 0.5)])
    a = evaluate_sample(PT, d, "high_spin", high_spin_state(PT), DEFAULT_CONFIG)
    b = evaluate_sample(PT, d, "high_spin", high_spin_state(PT), DEFAULT_CONFIG)
    assert a == b
