"""McMillan-Allen-Dynes Tc and the BCS weak-coupling gap.

PHONON-CHANNEL, SPIN-SINGLET Tc of an imposed reference lattice -- not a
superconductivity estimate for the ORME claim; a returned Tc is not evidence
the material superconducts. Level 2.

Tc = f1 f2 (omega_log/1.20) exp[-1.04(1+lam)/(lam - mu*(1+0.62 lam))]
  f1 = [1 + (lam/L1)^1.5]^(1/3),        L1 = 2.46(1 + 3.8 mu*)
  f2 = 1 + (w2/wlog - 1) lam^2/(lam^2+L2^2), L2 = 1.82(1 + 6.3 mu*)(w2/wlog)

Constants verified against Allen & Dynes 1975 (Phys. Rev. B 12, 905) via
SECONDARY sources only (primary PRB paywalled) -- see
research-wiki/prior-art/epw-allen-dynes-tc-citation-verification.md.

G-DENOM: D = lam - mu*(1+0.62 lam) changes sign at lam_crit = mu*/(1-0.62 mu*);
below it the raw formula returns a spurious huge Tc, so D<=0 (or lam<=0 or
wlog<=0) returns Tc=0.
"""

from __future__ import annotations

import math

from ..config import BOLTZMANN, EV_IN_JOULES

MU_STAR_DEFAULT = 0.10
_KB_MEV_PER_K = (BOLTZMANN / EV_IN_JOULES) * 1000.0   # 8.617333262e-2 meV/K


def allen_dynes_tc(lam: float, omega_log_k: float, omega_2_k: float,
                   mu_star: float = MU_STAR_DEFAULT) -> float:
    if lam <= 0.0 or omega_log_k <= 0.0:
        return 0.0
    denom = lam - mu_star * (1.0 + 0.62 * lam)
    if denom <= 0.0:                       # G-DENOM: invalid / non-superconducting
        return 0.0
    ratio = (omega_2_k / omega_log_k) if omega_log_k > 0.0 else 1.0
    lam1 = 2.46 * (1.0 + 3.8 * mu_star)
    lam2 = 1.82 * (1.0 + 6.3 * mu_star) * ratio
    f1 = (1.0 + (lam / lam1) ** 1.5) ** (1.0 / 3.0)
    f2 = 1.0 + (ratio - 1.0) * lam * lam / (lam * lam + lam2 * lam2)
    exponent = -1.04 * (1.0 + lam) / denom
    try:
        tc = f1 * f2 * (omega_log_k / 1.20) * math.exp(exponent)
    except OverflowError:                  # extreme exponent -> unphysical, clamp
        return 0.0
    return tc if math.isfinite(tc) else 0.0


def bcs_gap_mev(tc_k: float) -> float:
    if tc_k <= 0.0:
        return 0.0
    return 1.764 * _KB_MEV_PER_K * tc_k
