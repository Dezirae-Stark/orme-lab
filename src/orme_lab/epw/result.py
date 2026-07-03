"""EPWResult -- the value the SC_GAP seam returns.

Numeric fields are None when EPW did not produce a Tc (toy/absent, not
applicable, failed, or dynamically unstable). `source` is always present.

PHONON-CHANNEL, SPIN-SINGLET Tc of an IMPOSED reference lattice -- NOT a
superconductivity estimate for the ORME claim; a returned Tc is not evidence
the material superconducts. Level 2.
"""

from __future__ import annotations

from dataclasses import dataclass

from .allen_dynes import allen_dynes_tc, bcs_gap_mev
from .spectral import EliashbergFunction


@dataclass(frozen=True)
class EPWResult:
    tc_kelvin: float | None
    lam: float | None
    omega_log_k: float | None
    omega_2_k: float | None
    gap_mev: float | None
    mu_star: float | None
    source: str
    unstable: bool = False
    provenance: str = ""

    @classmethod
    def toy_absent(cls) -> "EPWResult":
        return cls(None, None, None, None, None, None, "toy", False, "")

    @classmethod
    def not_applicable(cls, reason: str) -> "EPWResult":
        return cls(None, None, None, None, None, None, "n/a", False, reason)

    @classmethod
    def failed(cls, reason: str) -> "EPWResult":
        return cls(None, None, None, None, None, None, "epw:failed", False, reason)

    @classmethod
    def from_eliashberg(cls, ef: EliashbergFunction, mu_star: float,
                        provenance: str) -> "EPWResult":
        lam, wlog, w2 = ef.moments()
        if ef.unstable:
            # Unstable branch intentionally keeps the real lam/omega_log_k/omega_2_k
            # (only Tc/gap are nulled) -- the moments are still informative even
            # though Tc is not meaningful for a dynamically unstable lattice.
            return cls(None, lam, wlog, w2, None, mu_star, "epw:unstable", True, provenance)
        tc = allen_dynes_tc(lam, wlog, w2, mu_star)
        gap = bcs_gap_mev(tc)
        return cls(tc, lam, wlog, w2, gap, mu_star, "epw", False, provenance)
