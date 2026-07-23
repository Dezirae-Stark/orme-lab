"""OrbitalResult -- the value the ORBITAL_ORDER seam returns.

Numeric fields are None when no computed value exists (toy/absent, not
applicable, or a failed run). `source` is always present.

`anisotropy` is the gate-facing d-manifold charge-shape descriptor (the same
role the toy density-anisotropy value plays at the DENSITY_ANISOTROPY seam).
`polarization` is the OFF-GATE orbital-order parameter -- a different
contraction of the same Löwdin occupations (mean-absolute-deviation from equal
filling, not the quadrupole shape) -- used only as an against-triplet pairing
discriminator, never as positive SC/pairing evidence, and never fed back into
the gate scalar. Computed at fixed geometry + fixed magnetic config: this is
computational isolation of cross-channel FEEDBACK, NOT physical separability.
Level 2.
"""

from __future__ import annotations

from dataclasses import dataclass

from ..orbital_order import d_manifold_anisotropy, d_polarization, dominant_orbital


@dataclass(frozen=True)
class OrbitalResult:
    anisotropy: float | None
    polarization: float | None
    dominant_orbital: str | None
    source: str
    provenance: str = ""

    @classmethod
    def toy_absent(cls) -> "OrbitalResult":
        return cls(None, None, None, "toy", "")

    @classmethod
    def not_applicable(cls, reason: str) -> "OrbitalResult":
        return cls(None, None, None, "n/a", reason)

    @classmethod
    def failed(cls, reason: str) -> "OrbitalResult":
        return cls(None, None, None, "orbital:failed", reason)

    @classmethod
    def from_occupations(
        cls, per_atom: "tuple[tuple[float, ...], ...]", source: str
    ) -> "OrbitalResult":
        """Aggregate per-atom (metal-site) d-occupations into one OrbitalResult:
        mean over the metal atoms of the off-gate polarization and the gate-facing
        anisotropy, plus the dominant orbital of the mean occupation."""
        n = len(per_atom)
        if n == 0:
            return cls.not_applicable("no per-atom occupations")
        pol = sum(d_polarization(a) for a in per_atom) / n
        # gate-facing shape anisotropy: combined rank-2 quadrupole + cubic-field eg-t2g imbalance,
        # so a cubic-split site (Q_zz=0, e.g. fcc Ir) is not mis-read as isotropic.
        aniso = sum(d_manifold_anisotropy(a) for a in per_atom) / n
        width = len(per_atom[0])
        mean_occ = tuple(sum(a[i] for a in per_atom) / n for i in range(width))
        dom = dominant_orbital(mean_occ)
        provenance = (
            f"mean over {n} metal atom(s); fixed geometry + fixed magnetic config "
            "(computational isolation of cross-channel feedback, NOT physical "
            "separability)"
        )
        return cls(aniso, pol, dom, source, provenance)
