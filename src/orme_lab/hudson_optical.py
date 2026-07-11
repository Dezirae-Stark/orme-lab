"""Hudson optical-coherence branch (Branch B).

Hudson described the proposed ORME phase not as an ordinary zero-resistance metal
but as a resonantly accessible, macroscopically coherent hybrid light-matter state:
a single frequency of light circulating internally, carriers entering as paired
electrons through resonant frequency matching, and a circulating mode producing the
Meissner response. Read literally ("two electrons become pure light") this is
incompatible with condensed-matter physics — Cooper pairs are charge-2e composite
bosons, not photons. The defensible, testable translation (see
``docs/terminology_translation.md`` and ``electromagnetic_coherence.py``) is a
hybrid eigenstate

    |P> = alpha|2e> + beta|photon> + chi|X>

with a MEASURABLE photonic fraction f_ph and electronic fraction f_el.

This branch is DISTINCT from superconductivity (Branch A). A material can be a
room-temperature polariton condensate without being an electrical superconductor,
and vice versa. Branch B therefore adds FALSIFICATION SURFACE, not credence: a high
coherence score is never, by itself, evidence for Hudson — it must survive the
mundane alternatives (fluorescence, Raman, thermal emission, Mie scattering,
nanoparticle plasmons, cavity leakage). The two load-bearing, EXTRAORDINARY claims —
that the mode is self-sustaining (persistent ring-down) and that magnetism tracks the
optical resonance — are default-blocked: the simulation cannot assert them; they
require an external laboratory measurement fed in.

All physics here is toy/surrogate, bounded, and flagged. Real forms used are
textbook: coupled two-oscillator diagonalization and Hopfield mode-composition
weights. TODO(dft): replace bare couplings with computed mode overlaps.
"""
from __future__ import annotations

import math

from .config import ModelThresholds


def polariton_branches(matter_ev: float, photon_ev: float, coupling_ev: float) -> tuple[float, float]:
    """Lower/upper polariton energies from a coupled two-oscillator diagonalization.

    H = [[matter_ev, g], [g, photon_ev]]; eigenvalues
        E_pm = (matter+photon)/2 +/- sqrt((delta/2)^2 + g^2),  delta = matter - photon.
    On resonance the splitting is 2g (the vacuum Rabi splitting). Returns
    (lower, upper).
    """
    mean = 0.5 * (matter_ev + photon_ev)
    half = math.sqrt((0.5 * (matter_ev - photon_ev)) ** 2 + coupling_ev**2)
    return mean - half, mean + half


def mode_composition(matter_ev: float, photon_ev: float, coupling_ev: float) -> tuple[float, float]:
    """Photonic (Hopfield) and electronic fractions of the LOWER polariton.

    f_ph = (1/2)(1 + delta / Omega),  f_el = 1 - f_ph,
    with delta = matter - photon and Omega = sqrt(delta^2 + 4 g^2). On resonance
    (delta=0) both are 1/2; when matter >> photon the lower branch is photon-like
    (f_ph -> 1). Deterministic; bounded to [0, 1].
    """
    delta = matter_ev - photon_ev
    omega = math.sqrt(delta**2 + 4.0 * coupling_ev**2)
    if omega <= 0:
        return 0.5, 0.5
    f_ph = 0.5 * (1.0 + delta / omega)
    f_ph = min(1.0, max(0.0, f_ph))
    return f_ph, 1.0 - f_ph


def is_anticrossing(coupling_ev: float, linewidth_ev: float) -> bool:
    """A resolvable avoided crossing: the Rabi splitting 2g exceeds the linewidth.

    Two UNRELATED peaks that cross as the environment is tuned is the null; a genuine
    hybrid mode shows a minimum gap of 2g > linewidth at resonance.
    """
    return 2.0 * coupling_ev > linewidth_ev
