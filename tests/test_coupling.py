"""Tests for inter-unit coupling -- the hypothesis 4/5 crux.

The load-bearing physical claim: an electronically isolated unit (a monomer)
cannot support bulk superconductivity, so its coupling must score ~0 and be
flagged isolated. Connected geometries must score higher.
"""

from __future__ import annotations

from orme_lab.config import ModelThresholds
from orme_lab.coupling import (
    inter_unit_coupling_score,
    is_electronically_isolated,
    orbital_overlap_proxy,
)
from orme_lab.elements import get_element
from orme_lab.geometry import (
    make_compact_cluster,
    make_dimer,
    make_monomer,
)

TH = ModelThresholds()


def test_monomer_has_zero_coupling_and_is_isolated():
    pt = get_element("Pt")
    mono = make_monomer(pt)
    score = inter_unit_coupling_score(mono, TH)
    assert score == 0.0
    assert is_electronically_isolated(score, TH)  # hypothesis 5 gate bites


def test_dimer_couples_more_than_monomer():
    pt = get_element("Pt")
    mono = inter_unit_coupling_score(make_monomer(pt), TH)
    dimer = inter_unit_coupling_score(make_dimer(pt), TH)
    assert dimer > mono


def test_compact_cluster_couples_more_than_dimer():
    pt = get_element("Pt")
    dimer = inter_unit_coupling_score(make_dimer(pt), TH)
    compact = inter_unit_coupling_score(make_compact_cluster(pt, 13), TH)
    assert compact >= dimer


def test_coupling_scores_bounded():
    for sym in ("Au", "Pt", "Pd", "Ir", "Rh", "Os"):
        el = get_element(sym)
        for geom in (make_monomer(el), make_dimer(el), make_compact_cluster(el, 13)):
            s = inter_unit_coupling_score(geom, TH)
            assert 0.0 <= s <= 1.0


def test_overlap_proxy_decays_with_distance():
    near = orbital_overlap_proxy(2.5, TH)
    far = orbital_overlap_proxy(8.0, TH)
    assert near > far
    assert orbital_overlap_proxy(float("inf"), TH) == 0.0
