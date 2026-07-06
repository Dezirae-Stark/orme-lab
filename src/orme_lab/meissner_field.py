# src/orme_lab/meissner_field.py
"""Meissner Hc1 screen — Hudson patent DE3920144A1 (claim: lower critical field Hc1
below Earth's field ~50 uT for Ir/Au S-OUME).

Triage, not proof. From Hc1 back out the London penetration depth and the implied
superfluid density, and test the claim against (a) physical density bounds and
(b) the lab's own isolation premise (H-04/H-05): any Meissner screening needs
inter-unit phase coherence that an isolated monomer lacks.

  B_c1 ~ (Phi0 / 4 pi lambda^2) * ln kappa      (kappa ~ 2.7 -> ln kappa ~ 1, documented default)
  n_s  = m_e / (mu0 lambda^2 e^2)

Reference constants and conventional-SC Hc scales (Al ~0.01 T, Sn ~0.03 T, Pb ~0.08 T):
Tinkham, Introduction to Superconductivity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

PHI0 = 2.067833831e-15        # magnetic flux quantum (Wb)
MU0 = 1.25663706212e-6        # vacuum permeability (H/m)
M_E = 9.1093837015e-31        # electron mass (kg)
E_CHARGE = 1.602176634e-19    # elementary charge (C)

EARTH_FIELD_T = 50e-6         # nominal Earth field (T)
_NORMAL_METAL_N = 1e29        # reference normal-metal carrier density (m^-3)
_N_PHYSICAL_MIN, _N_PHYSICAL_MAX = 1e22, 1e29


def penetration_depth(b_c1_t: float, ln_kappa: float = 1.0) -> float:
    """London penetration depth lambda (m) implied by a lower critical field B_c1 (T)."""
    return math.sqrt(PHI0 * ln_kappa / (4.0 * math.pi * b_c1_t))


def superfluid_density(lambda_m: float) -> float:
    """Superfluid carrier density n_s (m^-3) for penetration depth lambda (m)."""
    return M_E / (MU0 * lambda_m ** 2 * E_CHARGE ** 2)


@dataclass(frozen=True)
class MeissnerFieldResult:
    b_c1_tesla: float
    lambda_london_m: float
    implied_superfluid_density_m3: float
    normal_metal_ratio: float
    isolated_premise: bool
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        if self.verdict == "in_tension_with_isolation":
            return (f"Hc1~{self.b_c1_tesla * 1e6:.0f} uT implies lambda~{self.lambda_london_m * 1e6:.2f} um "
                    f"and n_s~{self.implied_superfluid_density_m3:.1e} m^-3 "
                    f"({self.normal_metal_ratio:.1e}x a normal metal). But Meissner screening needs "
                    f"inter-unit phase coherence, which the isolated-monomer premise (H-04/H-05) "
                    f"lacks — the claim is internally in tension with its own premise.")
        if self.verdict == "implied_density_physical":
            return (f"Implied n_s~{self.implied_superfluid_density_m3:.1e} m^-3 is low "
                    f"({self.normal_metal_ratio:.1e}x a normal metal) but within physical bounds "
                    f"for a coupled dilute superconductor.")
        return (f"Implied n_s~{self.implied_superfluid_density_m3:.1e} m^-3 falls outside physical "
                f"bounds [{_N_PHYSICAL_MIN:.0e}, {_N_PHYSICAL_MAX:.0e}] m^-3.")


def screen_meissner(b_c1_t: float = EARTH_FIELD_T, *, isolated_premise: bool = True,
                    ln_kappa: float = 1.0) -> MeissnerFieldResult:
    lam = penetration_depth(b_c1_t, ln_kappa)
    n_s = superfluid_density(lam)
    ratio = n_s / _NORMAL_METAL_N

    if isolated_premise:
        verdict = "in_tension_with_isolation"
    elif _N_PHYSICAL_MIN <= n_s <= _N_PHYSICAL_MAX:
        verdict = "implied_density_physical"
    else:
        verdict = "implied_density_unphysical"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return MeissnerFieldResult(b_c1_t, lam, n_s, ratio, isolated_premise, verdict, level)
