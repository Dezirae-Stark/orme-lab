"""Test-only EPW double. NEVER shipped as production. Proves the seam plumbing
without QE binaries by returning a synthetic .a2f that flows through the real
spectral -> allen_dynes path."""
from orme_lab.backends import EPWBackend

# 11 whitespace columns per row: omega(meV) then the SAME a2f value in all 10
# smearing columns (so any configured smearing_column picks up signal). A
# triangular a2f peaked at 20 meV yields a finite positive lambda.
_SYNTHETIC_A2F = "\n".join(
    f"{omega:.4f} " + " ".join([f"{a2f:.4f}"] * 10)
    for omega, a2f in [
        (0.0, 0.0), (10.0, 0.5), (20.0, 1.0), (30.0, 0.5), (40.0, 0.0),
    ]
)


class FakeEPWRunner:
    def run(self, approx, cfg) -> str:
        return _SYNTHETIC_A2F


class FakeEPWBackend(EPWBackend):
    """EPWBackend whose availability is forced True and whose runner is the fake,
    so the pipeline SC_GAP gate (provides AND available) fires in tests."""
    def __init__(self):
        super().__init__(runner=FakeEPWRunner())

    @classmethod
    def available(cls) -> bool:
        return True


class UnavailableEPWBackend(EPWBackend):
    """EPW backend that is unavailable regardless of environment (binaries may or
    may not be installed). Exercises the 'unavailable' status/path deterministically
    without depending on the ambient absence of pw.x/ph.x/epw.x."""
    @classmethod
    def available(cls) -> bool:
        return False


class FailingEPWRunner:
    """Runner that raises EPWError -- superconducting_gap catches it and returns
    EPWResult.failed (source 'epw:failed'), exercising the honest 'failed' status."""
    def run(self, approx, cfg) -> str:
        from orme_lab.epw.runner import EPWError
        raise EPWError("synthetic EPW failure")


class FailingEPWBackend(EPWBackend):
    """Available EPW backend whose run always fails -> epw_status 'failed'."""
    def __init__(self):
        super().__init__(runner=FailingEPWRunner())

    @classmethod
    def available(cls) -> bool:
        return True
