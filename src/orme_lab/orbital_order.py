"""Orbital-order descriptors from Löwdin d-occupations (Level 2, MODEL-DERIVED proxies).

d_polarization: frame-robust orbital-order parameter P in [0,1] — normalized departure of the
five d-orbital occupations from equal filling (0 = degenerate, 1 = one orbital dominant).
Grounded: occupation-imbalance definition of orbital order (Tokura & Nagaosa, Science 288, 462,
2000; Fernandes/Chubukov/Schmalian, Nat. Phys. 10, 97, 2014). Off-gate pairing discriminator:
high P is generically triplet pair-breaking / lifts the interorbital-triplet degeneracy
(Ramires & Sigrist, PRB 94, 104501; Clepkens/Lindquist/Kee, PRR 3, 013001).

quadrupole_anisotropy: gate-facing charge-density shape anisotropy — occupation-weighted d-orbital
quadrupole, a d-manifold APPROXIMATION to the density shape (not a full charge-density cube).

Computed at fixed geometry + fixed magnetic config: this isolates cross-channel FEEDBACK by
construction, NOT physical separability (orbital/magnetic/lattice order are symmetry-locked).
"""
from __future__ import annotations

_D_LABELS = ("dz2", "dxz", "dyz", "dxy", "dx2y2")  # m-ordered; align to the projwfc (l=2,m) order in parse_projwfc

# Diagonal quadrupole (3z^2-r^2 -> Q_zz) weights per real d-orbital, normalized; used for the
# Per-orbital TRACELESS diagonal quadrupole (q_xx, q_yy, q_zz) of the real d-harmonics
# (each row sums to 0). The FULL tensor — not just Q_zz — so in-plane redistribution is captured:
# dxz favours x (q_xx>q_yy), dyz favours y (q_yy>q_xx), so dxz<->dyz shows up as Q_xx != Q_yy.
_QUAD = {
    "dz2":   (-2.0, -2.0, +4.0),
    "dxz":   (+2.0, -4.0, +2.0),
    "dyz":   (-4.0, +2.0, +2.0),
    "dxy":   (+2.0, +2.0, -4.0),
    "dx2y2": (+2.0, +2.0, -4.0),
}


def d_polarization(occ: "tuple[float, ...]") -> float:
    """Orbital-order parameter P in [0,1]: normalized d-occupation imbalance (0 = equal filling)."""
    n = len(occ)
    total = sum(occ)
    if total <= 0.0 or n == 0:
        return 0.0
    mean = total / n
    # normalized mean-absolute deviation from equal filling; max deviation is when all charge is
    # in one orbital (dev = 2*mean*(n-1)/n summed) -> normalize to [0,1].
    dev = sum(abs(x - mean) for x in occ)
    dev_max = 2.0 * mean * (n - 1)
    return 0.0 if dev_max <= 0.0 else min(1.0, dev / dev_max)


def quadrupole_anisotropy(occ: "tuple[float, ...]") -> float:
    """Rank-2 d-manifold shape anisotropy in [0,1]: the norm of the FULL occupation-weighted
    quadrupole tensor (Q_xx, Q_yy, Q_zz), normalized. Captures axial (z vs xy) AND in-plane
    (x vs y, e.g. dxz<->dyz redistribution) anisotropy — a strict improvement over a Q_zz-only
    measure. Level-2. One structural blind spot remains and is intrinsic to any rank-2 tensor:
    it is 0 for a cubic (Oh) site by symmetry (all rank-2 components vanish), so Q=0 means 'no
    rank-2 anisotropy', NOT 'spherical' — the cubic eg-t2g split (rank-4, e.g. fcc Ir) is picked
    up by eg_t2g_imbalance instead, and the two are combined in d_manifold_anisotropy."""
    total = sum(occ)
    if total <= 0.0:
        return 0.0
    q = [sum(_QUAD[l][i] * o for l, o in zip(_D_LABELS, occ)) / total for i in range(3)]
    norm = (q[0] * q[0] + q[1] * q[1] + q[2] * q[2]) ** 0.5
    # normalize by ~a single fully-occupied orbital's |Q| (=4.0) -> [0,1], clamped.
    return min(1.0, norm / 4.0)


def eg_t2g_imbalance(occ: "tuple[float, ...]") -> float:
    """Cubic-field eg-t2g population imbalance in [0,1]: |<eg> - <t2g>| / (<eg>+<t2g>), where
    eg = {dz2, dx2y2} and t2g = {dxz, dyz, dxy} (the Oh crystal-field split of the d-manifold).

    This captures the crystal-field anisotropy that `quadrupole_anisotropy` (a rank-2 tensor) is
    structurally blind to: a cubic site has zero quadrupole yet a real eg/t2g occupation split
    (e.g. fcc Ir: eg 1.6892 > t2g 1.4823 -> nonzero here, zero in the quadrupole). Level-2
    descriptor from the same fixed-config Löwdin occupations."""
    eg = (occ[0] + occ[4]) / 2.0        # dz2, dx2y2
    t2g = (occ[1] + occ[2] + occ[3]) / 3.0   # dxz, dyz, dxy
    denom = eg + t2g
    return 0.0 if denom <= 0.0 else min(1.0, abs(eg - t2g) / denom)


def d_manifold_anisotropy(occ: "tuple[float, ...]") -> float:
    """Combined gate-facing d-shape anisotropy in [0,1]: the larger of the FULL rank-2 quadrupole
    anisotropy (axial + in-plane, incl. dxz<->dyz redistribution) and the cubic-field eg-t2g
    imbalance. Max means a shell anisotropic in EITHER channel reads anisotropic — so a cubic-split
    site (rank-2 = 0, e.g. fcc Ir) is not mis-read as isotropic, and an in-plane t2g redistribution
    the eg-t2g term misses is still caught by the full quadrupole. Only genuinely higher-rank
    patterns invisible to BOTH channels read low, and that direction is conservative for the gate
    (less anisotropy -> smaller localization penalty -> never more permissive). Distinct from the
    off-gate polarization P (occupation dispersion), so the anti-tautology separation holds."""
    return max(quadrupole_anisotropy(occ), eg_t2g_imbalance(occ))


def dominant_orbital(occ: "tuple[float, ...]") -> str:
    """Label of the most-occupied d-orbital (symmetry metadata; non-scoring provenance)."""
    return _D_LABELS[max(range(len(occ)), key=lambda i: occ[i])]
