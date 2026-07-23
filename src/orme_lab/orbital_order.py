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
# occupation-weighted shape tensor. Standard angular quadrupole signs of the real d-harmonics.
_QZZ = {"dz2": +2.0, "dxz": +1.0, "dyz": +1.0, "dxy": -2.0, "dx2y2": -2.0}


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
    """Gate-facing d-manifold charge-shape anisotropy in [0,1] from occupation-weighted quadrupole."""
    total = sum(occ)
    if total <= 0.0:
        return 0.0
    qzz = sum(w * o for w, o in zip((_QZZ[l] for l in _D_LABELS), occ)) / total
    # |Q_zz| normalized by its max magnitude (2.0) -> [0,1] departure from spherical (Q_zz=0).
    return min(1.0, abs(qzz) / 2.0)


def dominant_orbital(occ: "tuple[float, ...]") -> str:
    """Label of the most-occupied d-orbital (symmetry metadata; non-scoring provenance)."""
    return _D_LABELS[max(range(len(occ)), key=lambda i: occ[i])]
