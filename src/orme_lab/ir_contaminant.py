"""IR-doublet contaminant control — Hudson patent DE3920144A1 (positive leg).

Triage, not proof. The negative leg (src/orme_lab/ir_signature.py) excludes a
metal-metal assignment for the patent's quoted doublet. This module supplies the
positive leg: a cited reference library of IR-active species the patent's own
wet-chemistry route would deposit, scored against the observed doublet by line
position AND splitting, and ranked. Verdict may be `unmatched` — with metal-metal
already excluded, that is the anomalous branch that would support the patent.

Band values are sourced and citation-audited before entry (see
~/.claude/research-wiki/prior-art/ir-contaminant-bands.md); every row carries a
source comment. Reuses the harmonic constant 1302.8 from ir_signature.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING
from .ir_signature import WAVENUMBER_CONST, wavenumber  # noqa: F401  (wavenumber used in Task 5)

_CAT_RANK = {"route_derived": 0, "standard": 1}
_TOL_PLAUSIBLE = 1.0  # total normalised band-width residual admitted as a plausible match


@dataclass(frozen=True)
class ContaminantBand:
    name: str
    category: str                       # "route_derived" | "standard"
    lo_band: tuple[float, float]        # lower-line cm^-1 range
    hi_band: tuple[float, float]        # upper-line cm^-1 range
    split_band: tuple[float, float]     # asym-sym splitting cm^-1 range
    oscillator_mu: float | None         # stretch reduced mass (amu) for layer-2; None if N/A
    coupled_applicable: bool
    source: str


def _band_residual(x: float, band: tuple[float, float]) -> float:
    """0 if x is inside [lo, hi]; else the distance outside expressed in band-widths."""
    lo, hi = band
    if lo <= x <= hi:
        return 0.0
    width = hi - lo if hi > lo else 1.0
    return (lo - x) / width if x < lo else (x - hi) / width


def match_score(lines_cm: tuple[float, ...], band: ContaminantBand) -> float:
    """Total normalised residual of a doublet against a candidate band (0 = perfect)."""
    lo_line, hi_line = min(lines_cm), max(lines_cm)
    split = hi_line - lo_line
    return (_band_residual(lo_line, band.lo_band)
            + _band_residual(hi_line, band.hi_band)
            + _band_residual(split, band.split_band))
