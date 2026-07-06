# src/orme_lab/thermal_stability.py
"""Thermal-stability screen — Hudson patent DE3920144A1 (claims: no sinter at 800 C,
amorphous powder to 1200 C).

Triage, not proof. Compares a claimed stability temperature against the Huttig
(~0.3*T_m) and Tammann (~0.5*T_m) sintering-onset heuristics computed from the bulk
melting point. A claim below the refractory envelope is unremarkable for that metal;
a claim above its Tammann onset would be anomalous for it.

Reference: Tammann/Huttig rule (established in sintering / heterogeneous-catalysis
literature); melting points are CRC-standard values. Heuristic, flagged as such.
"""
from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

HUTTIG_FRACTION = 0.3
TAMMANN_FRACTION = 0.5
_ABS_ZERO_C = -273.15

# Bulk melting points (C), CRC standard.
_MELT_C = {
    "Rh": 1964, "Ir": 2446, "Pt": 1768, "Pd": 1555, "Os": 3033,
    "Ru": 2334, "Au": 1064, "Ag": 962, "Cu": 1085,
}


def _c_to_k(t_c: float) -> float:
    return t_c - _ABS_ZERO_C


def _k_to_c(t_k: float) -> float:
    return t_k + _ABS_ZERO_C


@dataclass(frozen=True)
class ThermalStabilityResult:
    symbol: str
    t_melt_c: float
    t_huttig_c: float
    t_tammann_c: float
    t_claim_c: float
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        if self.verdict == "within_refractory_envelope":
            return (f"{self.symbol}: claimed stability at {self.t_claim_c:.0f} C is below the "
                    f"Huttig onset ({self.t_huttig_c:.0f} C); ordinary bulk powder already "
                    f"survives this. Not diagnostic of an exotic state.")
        if self.verdict == "marginal":
            return (f"{self.symbol}: {self.t_claim_c:.0f} C sits between Huttig "
                    f"({self.t_huttig_c:.0f}) and Tammann ({self.t_tammann_c:.0f} C) — the "
                    f"ordinary sintering-onset window. Not clearly anomalous.")
        return (f"{self.symbol}: {self.t_claim_c:.0f} C exceeds the Tammann bulk-mobility onset "
                f"({self.t_tammann_c:.0f} C); persistent non-sintering here would be anomalous "
                f"for this metal.")


def screen_thermal(symbol: str, t_claim_c: float) -> ThermalStabilityResult:
    t_melt_c = _MELT_C[symbol]
    t_m_k = _c_to_k(t_melt_c)
    t_huttig_c = _k_to_c(HUTTIG_FRACTION * t_m_k)
    t_tammann_c = _k_to_c(TAMMANN_FRACTION * t_m_k)

    if t_claim_c < t_huttig_c:
        verdict = "within_refractory_envelope"
    elif t_claim_c < t_tammann_c:
        verdict = "marginal"
    else:
        verdict = "exceeds_envelope"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return ThermalStabilityResult(symbol, t_melt_c, t_huttig_c, t_tammann_c, t_claim_c, verdict, level)
