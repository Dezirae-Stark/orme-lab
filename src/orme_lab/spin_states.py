"""Spin-state modelling and the spin-polarization toy score.

Hypotheses 1 & 2: PGM atoms/clusters may enter unusual metastable electronic
configurations, and high-spin states may deform the electron density.

A "high-spin" state is one where valence electrons occupy separate d-orbitals
with parallel spins (maximizing unpaired electrons) rather than pairing up.
Hund's first rule favours this in free atoms; a ligand/crystal field can force
the opposite ("low-spin"). The number of *unpaired* electrons sets the magnetic
moment and is the lever behind the density-anisotropy story.

The score here is a normalized proxy in [0, 1], not a computed magnetic moment.

    TODO(dft): replace the combinatorial unpaired-electron estimate with spin
    densities from a broken-symmetry / unrestricted DFT calculation, which can
    resolve genuine high-spin vs low-spin ordering including field effects.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import BOHR_MAGNETON
from .elements import Element


@dataclass(frozen=True)
class SpinState:
    """A candidate spin configuration for one atomic centre.

    Attributes
    ----------
    unpaired_electrons:
        Number of electrons with unpaired spin. This is the physically
        meaningful quantity; everything else derives from it.
    is_high_spin:
        Whether this configuration is the maximum-multiplicity (high-spin) case
        for the element's valence d-count.
    """

    element: Element
    unpaired_electrons: int
    is_high_spin: bool

    @property
    def multiplicity(self) -> int:
        """Spin multiplicity 2S+1, with S = unpaired/2."""
        return self.unpaired_electrons + 1

    @property
    def spin_only_moment_bohr(self) -> float:
        """Spin-only effective magnetic moment in Bohr magnetons.

        mu = sqrt(n(n+2)) for n unpaired electrons. The classic first-order
        estimate that ignores orbital contribution (which is *not* small for 5d
        metals like Os/Ir/Pt — a known limitation of the spin-only formula)."""
        n = self.unpaired_electrons
        return (n * (n + 2)) ** 0.5

    @property
    def moment_si(self) -> float:
        """Magnetic moment in J/T."""
        return self.spin_only_moment_bohr * BOHR_MAGNETON


def max_unpaired_electrons(element: Element) -> int:
    """Maximum unpaired electrons available in the valence d shell.

    For a d^k shell (k <= 5) all electrons can be unpaired -> k. For k > 5 the
    shell is more than half full, so pairing is forced: unpaired = 10 - k. The
    s electron is treated as pairable and ignored here (a simplification).
    """
    k = element.d_electrons
    return k if k <= 5 else 10 - k


def high_spin_state(element: Element) -> SpinState:
    """The maximum-multiplicity spin state for this element."""
    return SpinState(element, max_unpaired_electrons(element), is_high_spin=True)


def low_spin_state(element: Element) -> SpinState:
    """A minimal-multiplicity (paired-as-possible) state: 0 or 1 unpaired."""
    unpaired = element.d_electrons % 2
    return SpinState(element, unpaired, is_high_spin=False)


def spin_polarization_score(state: SpinState) -> float:
    """Toy spin-polarization score in [0, 1].

    Rationale: normalize the state's unpaired-electron count against the *most*
    a d shell can offer (5, the half-filled maximum). A d^5 high-spin centre
    (5 unpaired) scores 1.0; a closed-shell singlet scores 0.0.

    This rewards exactly the configurations hypotheses 1-2 care about (many
    parallel spins) while staying bounded and monotonic. It is NOT a claim
    about which state is energetically preferred — only about how spin-polarized
    a given state is if it exists.
    """
    return min(state.unpaired_electrons / 5.0, 1.0)
