"""Tests for predicted observables, the SC plausibility gate, and the pipeline.

These tests encode the project's anti-overclaiming commitments as assertions:

* an isolated unit is RULED OUT (never gets a positive plausibility),
* zero coupling / zero carriers zeroes the plausibility (AND-gate, not average),
* screening (Meissner proxy) collapses when any ingredient is missing,
* a full screen is deterministic and ranks ruled-out candidates last.
"""

from __future__ import annotations

from orme_lab.config import DEFAULT_CONFIG, ModelThresholds
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster, make_monomer
from orme_lab.observables import (
    curie_susceptibility,
    meissner_screening_proxy,
    predict_resistance_regime,
)
from orme_lab.pipeline import (
    evaluate_candidate,
    run_screen,
    structural_stability_proxy,
)
from orme_lab.spin_states import high_spin_state, low_spin_state
from orme_lab.superconductivity import superconductivity_plausibility_score

TH = ModelThresholds()


def test_isolated_monomer_is_ruled_out():
    pt = get_element("Pt")
    rec = evaluate_candidate(
        pt, make_monomer(pt), "high_spin", high_spin_state(pt), DEFAULT_CONFIG
    )
    assert rec.isolated
    assert rec.ruled_out
    assert rec.sc_plausibility == 0.0
    assert "RULED OUT" in rec.verdict


def test_plausibility_is_and_gate_not_average():
    # Strong on four axes, dead on coupling -> must be zero, not averaged up.
    result = superconductivity_plausibility_score(
        coupling_score=0.0,      # fails
        carrier_proxy=0.9,
        field_suppression=0.9,
        structural_stability=0.9,
        observable_signal=0.9,
        thresholds=TH,
    )
    assert result.score == 0.0
    assert "coupling" in result.failed_gates


def test_all_gates_pass_gives_positive_bounded_score():
    result = superconductivity_plausibility_score(
        coupling_score=0.8,
        carrier_proxy=0.8,
        field_suppression=0.8,
        structural_stability=0.8,
        observable_signal=0.8,
        thresholds=TH,
    )
    assert result.all_passed
    assert 0.0 < result.score <= 1.0
    assert "NOT RULED OUT" in result.explain()


def test_meissner_screening_needs_all_ingredients():
    assert meissner_screening_proxy(0.0, 0.9, 0.9) == 0.0   # no coupling
    assert meissner_screening_proxy(0.9, 0.0, 0.9) == 0.0   # no carriers
    assert meissner_screening_proxy(0.9, 0.9, 0.0) == 0.0   # field killed it
    assert meissner_screening_proxy(0.9, 0.9, 0.9) > 0.0


def test_curie_susceptibility_zero_for_spinless_state():
    pd = get_element("Pd")  # closed shell -> no unpaired electrons
    chi = curie_susceptibility(high_spin_state(pd), temperature_k=300.0)
    assert chi == 0.0


def test_resistance_regime_routing():
    assert predict_resistance_regime(0.9, 0.9) == "candidate-sc"
    assert predict_resistance_regime(0.4, 0.1) == "metallic"
    assert predict_resistance_regime(0.05, 0.05) == "activated"


def test_structural_stability_monomer_is_zero():
    pt = get_element("Pt")
    assert structural_stability_proxy(make_monomer(pt)) == 0.0
    assert structural_stability_proxy(make_compact_cluster(pt, 13)) > 0.0


def test_run_screen_is_deterministic_and_ranks_ruled_out_last():
    a = run_screen()
    b = run_screen()
    # deterministic: identical config -> identical ranking
    assert [r.as_csv_row() for r in a] == [r.as_csv_row() for r in b]
    # ruled-out candidates should not outrank surviving ones
    plausibilities = [r.sc_plausibility for r in a]
    assert plausibilities == sorted(plausibilities, reverse=True)
    # the six named elements are all represented
    assert {r.element for r in a} == {"Au", "Pt", "Pd", "Ir", "Rh", "Os"}
