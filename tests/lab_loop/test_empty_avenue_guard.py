"""Regression: an avenue with an empty screening axis (no elements / geometry /
spin) must never run. An empty grid yields zero records and all-0.0 metrics,
which would spuriously FIRE any 'less-than' falsifier — silently retiring a
hypothesis having tested nothing. Found by the ultracode adversarial review.
"""
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.runner import validate_runnable, run_avenue
from orme_lab.lab_loop.hypotheses import validate_scope
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _av(elements=("Ir",), geoms=("dimer",), spins=("high_spin",), hyp="H1-open-shell"):
    return Avenue(
        id="empty", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, geoms, spins, 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_validate_runnable_rejects_empty_axes():
    assert validate_runnable(_av(elements=()))[0] is False
    assert validate_runnable(_av(geoms=()))[0] is False
    assert validate_runnable(_av(spins=()))[0] is False
    assert validate_runnable(_av())[0] is True  # non-empty still passes


def test_validate_scope_rejects_empty_scope_standalone():
    # validate_scope is called directly too — must be correct without validate_runnable.
    assert validate_scope(_av(elements=(), hyp="H1-open-shell"))[0] is False
    assert validate_scope(_av(elements=(), hyp="H1-closed-shell"))[0] is False
    assert validate_scope(_av(geoms=(), hyp="H3-cluster"))[0] is False
    assert validate_scope(_av(geoms=(), hyp="H3-monomer"))[0] is False


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_empty_element_avenue_cannot_retire_a_hypothesis():
    # The exact ultracode-verified exploit: an empty-elements avenue must be
    # SKIPPED, never run, and must NOT retire H1-open-shell.
    gen = OneShot([_av(elements=(), hyp="H1-open-shell")])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                               convergence_rounds=1))
    assert "empty" not in {r.avenue_id for r in rep.ledger.records}      # never ran
    assert "H1-open-shell" in rep.ledger.open_hypotheses                 # not retired
    assert not any(r.verdict == Verdict.KILLED_HYPOTHESIS.value for r in rep.ledger.records)
    assert "empty" in rep.digest                                        # surfaced honestly
