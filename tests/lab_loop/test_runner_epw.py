from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import run_avenue
from _fake_epw import FakeEPWBackend, FailingEPWBackend, UnavailableEPWBackend


def _epw_avenue(use_epw):
    # compact_cluster: a monomer would be ApproximantUndefined -> not_applicable.
    return Avenue(
        id="epw", tier=Tier.TIER1, description="epw probe", targeted_hypothesis="H5",
        action=ActionSpec(("Pd",), ("compact_cluster",), ("low_spin",),
                          0.0, 20.0, use_epw=use_epw, use_em=False, coupling_channel=None),
        falsification=FalsificationCondition("max_sc_lambda", Comparator.GT, 0.1),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_not_requested_when_use_epw_false():
    res = run_avenue(_epw_avenue(use_epw=False))
    assert res.epw_status == "not_requested"


def test_ran_with_fake_backend():
    res = run_avenue(_epw_avenue(use_epw=True), epw_backend=FakeEPWBackend())
    assert res.epw_status == "ran"
    assert any(r.sc_source.startswith("epw") for r in res.records)
    assert any(r.sc_lambda is not None for r in res.records)


def test_unavailable_when_backend_reports_unavailable():
    # A backend whose available() is False (binaries absent, or unusable) must
    # never run EPW; epw_status is "unavailable" and sc_* stay None. Uses an
    # explicitly-unavailable backend so this holds even where real QE is installed.
    res = run_avenue(_epw_avenue(use_epw=True), epw_backend=UnavailableEPWBackend())
    assert res.epw_status == "unavailable"
    assert all(r.sc_lambda is None for r in res.records)


def test_failed_is_distinct_from_ran():
    # EPW available and attempted, but the run errors -> source 'epw:failed'.
    # This must NOT report "ran" (that would falsely claim a successful computation).
    res = run_avenue(_epw_avenue(use_epw=True), epw_backend=FailingEPWBackend())
    assert res.epw_status == "failed"
    assert all(r.sc_lambda is None for r in res.records)
    assert any(r.sc_source == "epw:failed" for r in res.records)
