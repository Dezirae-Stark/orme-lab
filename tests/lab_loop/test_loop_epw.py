from orme_lab.backends import EPWBackend
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.loop import run_loop
from _fake_epw import FailingEPWBackend


def _av(use_epw):
    return Avenue(
        id="epw-unavail", tier=Tier.TIER1, description="d", targeted_hypothesis="H5",
        action=ActionSpec(("Pd",), ("compact_cluster",), ("low_spin",),
                          0.0, 20.0, use_epw=use_epw, use_em=False, coupling_channel=None),
        falsification=FalsificationCondition("max_sc_lambda", Comparator.GT, 0.1),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_digest_flags_epw_unavailable():
    rep = run_loop(OneShot([_av(use_epw=True)]), epw_backend=EPWBackend(),
                   loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                          convergence_rounds=1))
    assert "epw" in rep.digest.lower()
    assert "unavailable" in rep.digest.lower()
    assert "validated" not in rep.digest.lower()


def test_digest_flags_epw_failed():
    rep = run_loop(OneShot([_av(use_epw=True)]), epw_backend=FailingEPWBackend(),
                   loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                          convergence_rounds=1))
    assert "epw" in rep.digest.lower()
    assert "failed" in rep.digest.lower()
    assert "validated" not in rep.digest.lower()
