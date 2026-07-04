import pytest
from orme_lab.lab_loop.config import ObjectiveWeights, DEFAULT_LOOP_CONFIG


def test_decisiveness_dominates_coverage():
    w = ObjectiveWeights()
    assert w.w_decisiveness > w.w_coverage


def test_loop_config_is_frozen():
    with pytest.raises(Exception):
        DEFAULT_LOOP_CONFIG.max_avenues = 99  # type: ignore[misc]


def test_defaults_are_bounded_and_sane():
    c = DEFAULT_LOOP_CONFIG
    assert c.max_avenues > 0
    assert c.proposals_per_round > 0
    assert c.convergence_rounds > 0
    assert c.ledger_dir.endswith("ledger")
