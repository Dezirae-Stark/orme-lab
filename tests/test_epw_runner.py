import pytest
from orme_lab.epw.runner import scratch_name, assert_stage_complete, EPWError
from orme_lab.epw.approximant import PeriodicApproximant


def _approx(label):
    return PeriodicApproximant("Os", "hcp", 2.7, 1.6329931619, True, 0.4, label)


def test_scratch_name_is_deterministic_and_distinct():
    a = scratch_name(_approx("Os-hcp-compact13"))
    b = scratch_name(_approx("Os-hcp-compact13"))
    c = scratch_name(_approx("Os-hcp-compact6"))
    assert a == b and a != c
    assert " " not in a and "/" not in a


def test_assert_stage_complete_accepts_job_done():
    assert_stage_complete("... JOB DONE ...", require_convergence=False)


def test_assert_stage_complete_rejects_missing_job_done():
    with pytest.raises(EPWError):
        assert_stage_complete("stopped early", require_convergence=False)


def test_assert_stage_complete_requires_convergence_when_asked():
    with pytest.raises(EPWError):
        assert_stage_complete("JOB DONE", require_convergence=True)  # no convergence line
    assert_stage_complete("convergence has been achieved\nJOB DONE", require_convergence=True)


def test_assert_stage_complete_rejects_crash_marker():
    with pytest.raises(EPWError):
        assert_stage_complete("JOB DONE\n %%%% CRASH %%%%", require_convergence=False)
