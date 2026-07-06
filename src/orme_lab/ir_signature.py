"""IR-doublet signature screen — Hudson patent DE3920144A1 (claim: 1400-1600 cm^-1 doublet).

Triage, not proof. The patent's own OUME identity marker is an IR doublet in
1400-1600 cm^-1 (quoted: Rh 1429.53/1490.99, Ir 1432.09/1495.17). This screen asks,
deterministically, which bond family could produce a line at that wavenumber within
its representative literature force-constant range, and what force constant a
metal-metal bond would need to reach it.

Physics: harmonic diatomic  nu_tilde (cm^-1) = 1302.8 * sqrt(k/mu),  k in mdyne/A, mu in amu.

Reference values are representative literature ranges (Herzberg, Spectra of Diatomic
Molecules; Atkins, Physical Chemistry), not novel measurements. The metal-metal upper
bound is the envelope including multiply-bonded dimers (e.g. Re2Cl8^2-, nu(M-M) ~275 cm^-1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

WAVENUMBER_CONST = 1302.8  # cm^-1 * sqrt(amu / (mdyne/A))

# Atomic masses (amu), CRC standard.
_MASS = {"Rh": 102.905, "Ir": 192.217, "C": 12.011, "N": 14.007, "O": 15.999, "H": 1.008}

_METAL_K_MIN, _METAL_K_MAX = 1.0, 5.0  # metal-metal force-constant envelope (mdyne/A)


def _reduced_mass(m_a: float, m_b: float) -> float:
    return (m_a * m_b) / (m_a + m_b)


def wavenumber(k_mdyne: float, mu_amu: float) -> float:
    """Harmonic diatomic wavenumber (cm^-1) for force constant k (mdyne/A), reduced mass mu (amu)."""
    return WAVENUMBER_CONST * math.sqrt(k_mdyne / mu_amu)


def required_force_constant(nu_cm: float, mu_amu: float) -> float:
    """Force constant (mdyne/A) a bond of reduced mass mu would need to vibrate at nu_cm."""
    return mu_amu * (nu_cm / WAVENUMBER_CONST) ** 2


@dataclass(frozen=True)
class BondFamily:
    name: str
    mu_amu: float
    k_min_mdyne: float
    k_max_mdyne: float
    is_metal_metal: bool = False

    def reachable_band_cm(self) -> tuple[float, float]:
        return (wavenumber(self.k_min_mdyne, self.mu_amu), wavenumber(self.k_max_mdyne, self.mu_amu))

    def contains(self, nu_cm: float) -> bool:
        lo, hi = self.reachable_band_cm()
        return lo <= nu_cm <= hi


# Fixed light-atom reference families (representative literature k ranges).
_LIGHT_FAMILIES = (
    BondFamily("C–O / C=O", _reduced_mass(_MASS["C"], _MASS["O"]), 5.0, 13.0),
    BondFamily("C=C", _reduced_mass(_MASS["C"], _MASS["C"]), 8.0, 10.0),
    BondFamily("N–O", _reduced_mass(_MASS["N"], _MASS["O"]), 10.0, 16.0),
)


def metal_family(symbol: str) -> BondFamily:
    """Homodimer metal-metal family for `symbol` (mu = m/2)."""
    return BondFamily(f"{symbol}–{symbol}", _MASS[symbol] / 2.0, _METAL_K_MIN, _METAL_K_MAX, True)


@dataclass(frozen=True)
class IrSignatureResult:
    symbol: str
    observed_lines_cm: tuple[float, ...]
    k_required_mdyne: tuple[float, ...]
    metal_band_cm: tuple[float, float]
    reachable_by_family: dict[str, tuple[bool, ...]]
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        band = f"{self.metal_band_cm[0]:.0f}–{self.metal_band_cm[1]:.0f} cm^-1"
        kmax = max(self.k_required_mdyne)
        if self.verdict == "metal_bond_consistent":
            return (f"A {self.symbol}-{self.symbol} vibration ({band}) can reach the observed "
                    f"doublet. Metal-metal assignment not excluded (triage only).")
        if self.verdict == "light_atom_consistent":
            return (f"The doublet lies far above the {self.symbol}-{self.symbol} reachable band "
                    f"({band}); reaching it needs k~{kmax:.0f} mdyne/A (vs a metal-metal envelope "
                    f"<=5). A light-atom (C/N/O) bond reaches it within physical force constants. "
                    f"Triage: metal-metal excluded, light-atom assignment consistent.")
        if self.verdict == "metal_bond_excluded":
            return (f"Metal-metal excluded (needs k~{kmax:.0f} mdyne/A >> 5); no reference "
                    f"light-atom family cleanly reaches the doublet either.")
        return "Indeterminate."


def screen_ir_doublet(symbol: str, lines_cm: tuple[float, ...]) -> IrSignatureResult:
    metal = metal_family(symbol)
    k_req = tuple(required_force_constant(nu, metal.mu_amu) for nu in lines_cm)
    reachable = {fam.name: tuple(fam.contains(nu) for nu in lines_cm)
                 for fam in (metal, *_LIGHT_FAMILIES)}

    decisive = max(lines_cm)  # highest line -> largest required k
    if metal.contains(decisive):
        verdict = "metal_bond_consistent"
    elif any(f.contains(decisive) for f in _LIGHT_FAMILIES):
        verdict = "light_atom_consistent"
    else:
        verdict = "metal_bond_excluded"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return IrSignatureResult(symbol, tuple(lines_cm), k_req, metal.reachable_band_cm(),
                             reachable, verdict, level)
