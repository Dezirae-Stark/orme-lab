"""Per-element run trust gates.

Turns the raw numbers a run produces into a pass/fail verdict. A lambda that
fails ANY gate is NOT trustworthy and must not be reported as a converged result
(it stays at most a Level-2 counterfactual, and only if every gate passes).

The four gates:
  * wannier_match     -- interpolated bands track the DFT bands near E_F
  * lambda_converged  -- lambda is stable w.r.t. fine-grid refinement
  * dynamically_stable-- no imaginary phonon modes (soft Gamma tol upstream)
  * tc_computed       -- a positive lambda produced a finite Tc
"""
from __future__ import annotations

from dataclasses import dataclass

WANNIER_MAX_DEV_MEV = 10.0     # interpolated vs DFT bands near E_F
LAMBDA_DELTA_FRAC = 0.05       # |d lambda| / lambda on fine-grid refinement
MIN_FREQ_CM = -1.0             # allow a tiny negative acoustic tol at Gamma
LAMBDA_FLOOR = 0.02            # a metal with a full Fermi surface but lambda below
                              # this has an effectively-collapsed electron-phonon
                              # coupling -- a failure (e.g. Pt Tier-0 lambda~1e-5),
                              # not a physical result. Genuine weak couplers still
                              # exceed it; a value this low means the a2f is empty.


@dataclass(frozen=True)
class ConvergenceReport:
    wannier_band_max_dev_mev: float
    lambda_grid_delta_frac: float
    min_phonon_freq_cm: float
    lambda_value: float
    tc_kelvin: float

    def gates(self) -> dict[str, bool]:
        return {
            "wannier_match": self.wannier_band_max_dev_mev <= WANNIER_MAX_DEV_MEV,
            "lambda_converged": abs(self.lambda_grid_delta_frac) <= LAMBDA_DELTA_FRAC,
            "dynamically_stable": self.min_phonon_freq_cm >= MIN_FREQ_CM,
            "coupling_present": self.lambda_value >= LAMBDA_FLOOR,
            "tc_computed": self.tc_kelvin >= 0.0 and self.lambda_value > 0.0,
        }

    def trustworthy(self) -> bool:
        return all(self.gates().values())

    def failing_gates(self) -> list[str]:
        return [name for name, ok in self.gates().items() if not ok]
