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
_CONTAMINANTS: "tuple[ContaminantBand, ...]" = ()  # populated in Task 4 from the sourced table


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


@dataclass(frozen=True)
class ContaminantMatchResult:
    observed_lines_cm: tuple[float, ...]
    splitting_cm: float
    ranked: tuple[tuple[str, float], ...]   # (name, score), ascending
    verdict: str                            # tight_match | plausible_match | unmatched
    top_source: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        top_name, top_score = self.ranked[0]
        if self.verdict == "tight_match":
            return (f"Doublet {self.observed_lines_cm} (splitting {self.splitting_cm:.1f} cm^-1) "
                    f"falls inside the cited band of {top_name}. A mundane contaminant "
                    f"explains it (triage only; source: {self.top_source}).")
        if self.verdict == "plausible_match":
            return (f"Closest cited species is {top_name} (residual {top_score:.2f} band-widths; "
                    f"source: {self.top_source}); a contaminant assignment is plausible but not tight.")
        return (f"No cited contaminant matches the doublet within tolerance "
                f"(closest {top_name}, residual {top_score:.2f} band-widths). With metal-metal "
                f"already excluded, the doublet is unmatched — an anomalous result.")


def screen_contaminants(lines_cm: tuple[float, ...],
                        bands: "list[ContaminantBand] | None" = None) -> ContaminantMatchResult:
    table = list(_CONTAMINANTS if bands is None else bands)
    lo, hi = min(lines_cm), max(lines_cm)
    scored = [(b, match_score(lines_cm, b)) for b in table]
    scored.sort(key=lambda bs: (bs[1], _CAT_RANK[bs[0].category], bs[0].name))

    top_band, top_score = scored[0]
    lo_r = _band_residual(lo, top_band.lo_band)
    hi_r = _band_residual(hi, top_band.hi_band)
    sp_r = _band_residual(hi - lo, top_band.split_band)
    if lo_r == 0.0 and hi_r == 0.0 and sp_r == 0.0:
        verdict = "tight_match"
    elif top_score <= _TOL_PLAUSIBLE:
        verdict = "plausible_match"
    else:
        verdict = "unmatched"

    ranked = tuple((b.name, s) for b, s in scored)
    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return ContaminantMatchResult(tuple(lines_cm), hi - lo, ranked, verdict, top_band.source, level)


# ---- Layer 2: coupled-oscillator model for the top match --------------------
# Two equivalent coupled bond stretches split into symmetric/antisymmetric modes:
#   nu_sym  = 1302.8 * sqrt((k - k')/mu)   (in-phase, lower)
#   nu_asym = 1302.8 * sqrt((k + k')/mu)   (out-of-phase, higher)
# k = bond force constant, k' = interaction constant, mu = one-oscillator reduced mass.
_PHYSICAL_LIGHT_K = (4.0, 18.0)  # representative light-atom stretch envelope (mdyne/A)


def coupled_stretch(k: float, k_int: float, mu: float) -> tuple[float, float]:
    nu_sym = WAVENUMBER_CONST * math.sqrt((k - k_int) / mu)
    nu_asym = WAVENUMBER_CONST * math.sqrt((k + k_int) / mu)
    return (nu_sym, nu_asym)


def back_out_coupling(nu_lo: float, nu_hi: float, mu: float) -> tuple[float, float]:
    a = (nu_hi / WAVENUMBER_CONST) ** 2   # (k + k')/mu
    b = (nu_lo / WAVENUMBER_CONST) ** 2   # (k - k')/mu
    k = mu * (a + b) / 2.0
    k_int = mu * (a - b) / 2.0
    return (k, k_int)


def coupled_model_for(band: ContaminantBand, lines_cm: tuple[float, ...]) -> str:
    if not band.coupled_applicable or band.oscillator_mu is None:
        return (f"Coupled-stretch model N/A for {band.name}: the doublet is not a "
                f"symmetric two-oscillator pair for this species.")
    lo, hi = min(lines_cm), max(lines_cm)
    k, k_int = back_out_coupling(lo, hi, band.oscillator_mu)
    lo_k, hi_k = _PHYSICAL_LIGHT_K
    verdict = "physical" if lo_k <= k <= hi_k else "outside the light-atom envelope"
    return (f"{band.name}: observed doublet implies bond k~{k:.1f} mdyne/A and interaction "
            f"k'~{k_int:.2f} mdyne/A (mu={band.oscillator_mu:.3f} amu) — {verdict} "
            f"[{lo_k:.0f}-{hi_k:.0f}].")
