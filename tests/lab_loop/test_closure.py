# tests/lab_loop/test_closure.py
from orme_lab.lab_loop.closure import (
    GATE_INPUT_CLOSURE, OFF_GATE_INVARIANTS, is_independent,
)


def test_gate_inputs_are_in_closure():
    # The five AND-gate inputs and their upstream feeders are in-closure.
    for f in ("coupling", "carrier_proxy", "field_suppression",
              "structural_stability", "observable_signal"):
        assert f in GATE_INPUT_CLOSURE


def test_epw_block_is_off_gate():
    for f in ("sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev"):
        assert f in OFF_GATE_INVARIANTS


def test_closure_and_offgate_are_disjoint():
    assert GATE_INPUT_CLOSURE.isdisjoint(OFF_GATE_INVARIANTS)


def test_offgate_set_is_pinned_exactly():
    # Exact pin, not subset: if the model ever gains a new off-gate signal (or the
    # gate widens to consume one of these), this breaks LOUDLY — that is the point
    # of the closure oracle (spec §8.1). Update deliberately, never by accident.
    assert OFF_GATE_INVARIANTS == frozenset({
        "sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev", "sc_mu_star",
    })


def test_gate_input_closure_is_pinned_exactly():
    assert GATE_INPUT_CLOSURE == frozenset({
        "coupling", "carrier_proxy", "field_suppression",
        "structural_stability", "observable_signal",
        "anisotropy", "is_ricebean", "spin_polarization",
        "meissner_screening", "susceptibility", "resistance_regime",
        "sc_plausibility", "ruled_out",
    })


def test_predictor_touching_offgate_is_independent():
    assert is_independent(("sc_lambda",)) is True
    assert is_independent(("coupling", "sc_tc_kelvin")) is True


def test_predictor_only_in_closure_is_not_independent():
    assert is_independent(("coupling", "carrier_proxy")) is False


def test_empty_predictors_is_not_independent():
    assert is_independent(()) is False
