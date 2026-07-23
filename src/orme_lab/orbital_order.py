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
    """Gate-facing d-manifold shape anisotropy in [0,1]: the RANK-2 (quadrupolar) anisotropy of the
    occupation-weighted d-density, |Q_zz| normalized to [0,1]. Level-2 approximation with a known,
    conservative blind spot: it is 0 for any cubic (Oh) site by symmetry — a cubic charge
    distribution has zero quadrupole moment; its anisotropy is 4th-order (eg-t2g splitting), which
    NO rank-2 tensor can capture. So Q_zz=0 means 'no quadrupolar anisotropy', NOT 'spherical' (an
    eg>t2g split shell, e.g. fcc Ir, correctly reads 0 here). Also blind to in-plane redistribution
    (dxz<->dyz, dxy<->dx2y2, which share Q_zz weight). Reading 0 is conservative for the gate (less
    anisotropy -> smaller localization penalty -> not more permissive)."""
    total = sum(occ)
    if total <= 0.0:
        return 0.0
    qzz = sum(w * o for w, o in zip((_QZZ[l] for l in _D_LABELS), occ)) / total
    # |Q_zz| / max magnitude (2.0) -> [0,1]. Q_zz=0 = no rank-2 anisotropy (NOT necessarily
    # spherical; cubic eg-t2g splitting is rank-4 and invisible to any quadrupole — see docstring).
    return min(1.0, abs(qzz) / 2.0)


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
    """Combined gate-facing d-shape anisotropy in [0,1]: the larger of the rank-2 quadrupolar
    (axial) anisotropy and the cubic-field eg-t2g imbalance. Using the max means a shell that is
    anisotropic in EITHER channel reads anisotropic — so a cubic-split site (Q_zz=0) is no longer
    mis-read as isotropic, while a purely axial (tetragonal) distortion the quadrupole sees is
    still captured. 0 only when the d-occupations are genuinely equal-filled."""
    return max(quadrupole_anisotropy(occ), eg_t2g_imbalance(occ))


def dominant_orbital(occ: "tuple[float, ...]") -> str:
    """Label of the most-occupied d-orbital (symmetry metadata; non-scoring provenance)."""
    return _D_LABELS[max(range(len(occ)), key=lambda i: occ[i])]
