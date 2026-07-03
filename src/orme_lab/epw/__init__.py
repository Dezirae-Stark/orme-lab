"""EPW (Quantum ESPRESSO + EPW) electron-phonon Tc backend.

PHONON-CHANNEL, SPIN-SINGLET Tc of an IMPOSED periodic reference lattice --
NOT a superconductivity estimate for the ORME claim, NOT the finite cluster,
NOT any observed phase. A returned Tc is not evidence the material
superconducts. Everything here stays Level 2. See
docs/superpowers/specs/2026-07-03-epw-backend-design.md.
"""

from __future__ import annotations

from .config import EPWConfig
from .result import EPWResult
from .approximant import build_approximant, ApproximantUndefined, PeriodicApproximant
from .spectral import EliashbergFunction
from .allen_dynes import allen_dynes_tc, bcs_gap_mev
from .runner import EPWError, LiveEPWRunner, EPWRunner

__all__ = [
    "EPWConfig", "EPWResult", "build_approximant", "ApproximantUndefined",
    "PeriodicApproximant", "EliashbergFunction", "allen_dynes_tc", "bcs_gap_mev",
    "EPWError", "LiveEPWRunner", "EPWRunner",
]
