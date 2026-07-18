"""Electromagnetic / polaritonic coherence -- the charitable translation of
Hudson's "light flows through it" (hypotheses H12 and H16).

Read literally, "electrons become light" is incompatible with condensed-matter
physics: Cooper pairs are composite bosons of two electrons; photons are massless
gauge bosons. They are different objects. But there is a defensible reframing
(see ``docs/terminology_translation.md``):

    electrons  -->  photons                              (literal, unphysical)
    electrons  -->  phase-coherent, strongly coupled     (recognizable modern
                    to an electromagnetic field           quantum-materials physics)

This module models that second statement. It asks a question that is **distinct
from superconductivity**:

    "Is this an unusual *coherent quantum material* -- one that supports
     long-lived collective electronic oscillations (plasmons) or light-matter
     hybrid modes (polaritons)?"

That matters because of **H12 (electromagnetic-coherence misidentification)**: a
material could show striking optical/coherence phenomena -- which an observer
without modern vocabulary might call "light flowing through it" -- while having
**no** DC superconductivity at all (no zero resistance, no Meissner effect). So a
high coherence score here is NOT evidence of superconductivity; if anything it is
the model's way of offering a mundane-r alternative explanation to rule out.

Physics encoded (all toy, all bounded, all flagged):

* **Plasmon energy** hw_p = h * sqrt(n e^2 / (eps0 m*)) -- the collective
  oscillation energy of the electron gas, set by carrier density.
* **Anisotropic plasmon splitting** -- an elongated ('rice-bean') particle has
  distinct longitudinal and transverse plasmon resonances (standard nanoplasmonics,
  e.g. gold nanorods). This links H14/H20 to a concrete optical observable.
* **Light-matter coupling** g, Rabi splitting Omega_R = 2g, cooperativity
  C = 4g^2/(kappa*gamma), and the strong/ultrastrong-coupling criteria.
* **Coherence lifetime** tau = hbar / (matter dephasing), and quality factor
  Q = w / kappa.

    TODO(dft/rpa): replace the free-electron plasmon estimate with a computed
    dielectric function eps(q, w) (RPA / TDDFT), and the coupling g with a real
    cavity/near-field mode overlap. Only then do these become ab-initio numbers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .config import (
    ELECTRON_MASS,
    ELEMENTARY_CHARGE,
    EV_IN_JOULES,
    HBAR,
    ModelThresholds,
    VACUUM_PERMITTIVITY,
)


def plasmon_energy_ev(number_density_m3: float, effective_mass_ratio: float = 1.0) -> float:
    """Bulk plasmon energy hw_p in electron-volts.

    hw_p = hbar * sqrt(n e^2 / (eps0 m*)), with m* = effective_mass_ratio * m_e.
    For a metal-like density (~6e28 /m^3) this lands in the few-to-~15 eV range,
    matching measured bulk-plasmon energies of real metals.

    Parameters
    ----------
    number_density_m3:
        Free-carrier number density (electrons per cubic metre).
    effective_mass_ratio:
        m*/m_e. Heavier carriers lower the plasmon energy.
    """
    if number_density_m3 <= 0 or effective_mass_ratio <= 0:
        return 0.0
    m_star = effective_mass_ratio * ELECTRON_MASS
    omega_p = math.sqrt(
        number_density_m3 * ELEMENTARY_CHARGE**2 / (VACUUM_PERMITTIVITY * m_star)
    )
    return HBAR * omega_p / EV_IN_JOULES


def free_electron_density(element) -> float:
    """Free-electron carrier density n (electrons per cubic metre), toy estimate.

    n = conduction_electrons / V_atom, with conduction_electrons = the valence
    s-electron count (the nearly-free carriers of the free-electron model) and
    V_atom the volume of a sphere of the covalent radius.

    This is the textbook metal plasmon density: Au (s=1, r=1.36 A) -> ~9.5e28 /m^3
    -> plasmon ~9 eV, matching real gold.

    HONEST LIMITATION: a d-band metal with no valence s-electron (Pd, [Kr]4d10)
    returns n = 0 -> the EM channel is dark for it, because the free-electron
    model genuinely does not apply. That is a real caveat, not a fudge. Flagged
    toy, like every model in this package.
    """
    conduction_electrons = element.s_electrons
    if conduction_electrons <= 0:
        return 0.0
    radius_m = element.covalent_radius_ang * 1e-10
    v_atom = (4.0 / 3.0) * math.pi * radius_m**3
    if v_atom <= 0:
        return 0.0
    return conduction_electrons / v_atom


def anisotropic_plasmon_energies(
    base_energy_ev: float, anisotropy_score: float
) -> tuple[float, float]:
    """Split one plasmon energy into (longitudinal, transverse) branches.

    An isotropic (spherical) particle has a single resonance; an elongated
    ('rice-bean') particle splits into a lower-energy **longitudinal** mode
    (oscillation along the long axis) and a higher-energy **transverse** mode.
    This is a real, measured effect in anisotropic nanoparticles.

    We model the split as proportional to the anisotropy score (0 -> no split).
    Toy functional form, but the *direction* of the effect is physical:
    longitudinal shifts down, transverse shifts up.

    Returns
    -------
    (longitudinal_ev, transverse_ev)
    """
    split = 0.5 * anisotropy_score * base_energy_ev
    longitudinal = max(0.0, base_energy_ev - split)
    transverse = base_energy_ev + 0.5 * split
    return longitudinal, transverse


@dataclass(frozen=True)
class ElectromagneticMode:
    """A collective EM mode and its coupling to light, all energies in eV.

    Attributes
    ----------
    mode_energy_ev:
        Energy of the bare collective mode (e.g. plasmon energy).
    coupling_energy_ev:
        Light-matter coupling hg (half the Rabi splitting).
    cavity_loss_ev:
        Photon/mode dissipation rate as an energy, h*kappa.
    matter_loss_ev:
        Electronic dephasing rate as an energy, h*gamma.
    """

    mode_energy_ev: float
    coupling_energy_ev: float
    cavity_loss_ev: float
    matter_loss_ev: float

    @property
    def rabi_splitting_ev(self) -> float:
        """Vacuum Rabi splitting Omega_R = 2g."""
        return 2.0 * self.coupling_energy_ev

    @property
    def cooperativity(self) -> float:
        """C = 4 g^2 / (kappa * gamma). The cavity-QED figure of merit; C > 1 is
        the standard strong-coupling threshold."""
        denom = self.cavity_loss_ev * self.matter_loss_ev
        if denom <= 0:
            return math.inf if self.coupling_energy_ev > 0 else 0.0
        return 4.0 * self.coupling_energy_ev**2 / denom

    @property
    def quality_factor(self) -> float:
        """Q = mode_energy / cavity_loss. How many oscillations before decay."""
        if self.cavity_loss_ev <= 0:
            return math.inf
        return self.mode_energy_ev / self.cavity_loss_ev

    @property
    def coherence_lifetime_fs(self) -> float:
        """Coherence lifetime tau = hbar / (matter dephasing), in femtoseconds."""
        if self.matter_loss_ev <= 0:
            return math.inf
        gamma_rate = self.matter_loss_ev * EV_IN_JOULES / HBAR  # 1/s
        return (1.0 / gamma_rate) * 1e15


DRIVE_BASELINE = 0.1   # below this modeled response, a drive-channel hypothesis is falsified


def magnetic_drive_response(coherence_score: float, spin_polarization: float,
                            symmetry: "PairingSymmetry") -> float:
    """Toy [0,1] proxy for parametric response to an AC MAGNETIC drive (magnon-BEC analogue).

    MODEL PROXY, Level 2. Speculation on the PGM-SAC premise + triplet assumption +
    magnon-analogue drive assumption -- a hypothesis to test, not a mechanism claim. Nonzero
    ONLY for a spin-carrying (triplet) coherent condensate: needs coherence AND a moment AND
    equal-spin pairing. A spin-neutral singlet has no clean magnetic drive channel -> 0.
    """
    from .magnetic_field import PairingSymmetry as _PS
    if symmetry is not _PS.TRIPLET:
        return 0.0
    if coherence_score <= 0.0 or spin_polarization <= 0.0:
        return 0.0
    return max(0.0, min(1.0, coherence_score * spin_polarization))


def is_strong_coupling(mode: ElectromagneticMode) -> bool:
    """Strong coupling: Rabi splitting exceeds the mean loss rate.

    Omega_R > (kappa + gamma) / 2 -- the polariton branches are resolvable
    rather than washed out by dissipation."""
    mean_loss = 0.5 * (mode.cavity_loss_ev + mode.matter_loss_ev)
    return mode.rabi_splitting_ev > mean_loss


def coupling_regime(mode: ElectromagneticMode, thresholds: ModelThresholds) -> str:
    """Classify as 'weak' | 'strong' | 'ultrastrong' coupling.

    * weak       -- losses dominate; no resolvable polaritons.
    * strong     -- resolvable Rabi splitting (C > 1 and Omega_R beats losses).
    * ultrastrong-- Rabi splitting is a large fraction of the mode energy.
    """
    if mode.mode_energy_ev > 0:
        ratio = mode.rabi_splitting_ev / mode.mode_energy_ev
        if ratio >= thresholds.ultrastrong_coupling_ratio and is_strong_coupling(mode):
            return "ultrastrong"
    if is_strong_coupling(mode) and mode.cooperativity >= thresholds.min_cooperativity_for_coherence:
        return "strong"
    return "weak"


def polariton_coherence_score(mode: ElectromagneticMode, thresholds: ModelThresholds) -> float:
    """Toy electromagnetic-coherence score in [0, 1].

    Combines two bounded factors, both required:

    * cooperativity saturation  C / (1 + C)  -- rewards strong light-matter
      coupling relative to losses, saturating at 1.
    * quality-factor saturation  tanh(Q / 100) -- rewards a long-lived mode.

    The score is only credited in the strong/ultrastrong regime; in the weak
    regime it is forced to 0 (no coherent polariton to speak of). Geometric mean
    keeps it honest: BOTH strong coupling AND a decent Q are needed.
    """
    if coupling_regime(mode, thresholds) == "weak":
        return 0.0
    c = mode.cooperativity
    coop_factor = c / (1.0 + c) if math.isfinite(c) else 1.0
    q_factor = math.tanh(mode.quality_factor / 100.0)
    return (coop_factor * q_factor) ** 0.5


@dataclass(frozen=True)
class CoherenceResult:
    """Outcome of an electromagnetic-coherence evaluation.

    Deliberately kept separate from ``PlausibilityResult`` in
    ``superconductivity.py``: this is a *different question*. A material can score
    high here and still not be a superconductor (that is exactly hypothesis H12).
    """

    mode: ElectromagneticMode
    regime: str
    coherence_score: float
    plasmon_longitudinal_ev: float
    plasmon_transverse_ev: float
    magnetic_drive_response: float = 0.0

    @property
    def predicted_observables(self) -> dict[str, float]:
        """Optical/THz signatures an experimentalist could actually chase."""
        return {
            "rabi_splitting_ev": self.mode.rabi_splitting_ev,
            "coherence_lifetime_fs": self.mode.coherence_lifetime_fs,
            "quality_factor": self.mode.quality_factor,
            "plasmon_longitudinal_ev": self.plasmon_longitudinal_ev,
            "plasmon_transverse_ev": self.plasmon_transverse_ev,
            "magnetic_drive_response": self.magnetic_drive_response,  # MODEL PROXY (Level 2)
        }

    def explain(self) -> str:
        """Verdict -- always careful to distinguish coherence from SC."""
        if self.regime == "weak":
            return (
                "WEAK coupling: no resolvable polariton; losses dominate. No "
                "'light flows through it' signature under this model."
            )
        drive_note = (
            f" MODEL PROXY (Level 2) magnetic-drive response={self.magnetic_drive_response:.3f} "
            f"(triplet-only, magnon-BEC analogue; a hypothesis to test, not a mechanism claim)."
            if self.magnetic_drive_response > 0.0
            else ""
        )
        return (
            f"{self.regime.upper()} light-matter coupling "
            f"(coherence={self.coherence_score:.3f}). This is a candidate "
            f"COHERENT QUANTUM MATERIAL (polaritonic/plasmonic) -- a possible "
            f"H12 explanation for 'light flows through it'. It is NOT evidence "
            f"of superconductivity (no DC transport or Meissner claim follows)."
            f"{drive_note}"
        )


def evaluate_em_coherence(
    number_density_m3: float,
    anisotropy_score: float,
    thresholds: ModelThresholds,
    coupling_fraction: float = 0.05,
    cavity_loss_ev: float = 0.10,
    matter_loss_ev: float = 0.05,
    effective_mass_ratio: float = 1.0,
    spin_polarization: float = 0.0,
    symmetry: "PairingSymmetry" = None,
) -> CoherenceResult:
    """Full electromagnetic-coherence screen for one candidate.

    Parameters
    ----------
    number_density_m3:
        Free-carrier density driving the plasmon energy.
    anisotropy_score:
        Density anisotropy in [0,1] (from ``electron_density.py``). Drives the
        longitudinal/transverse plasmon split (the rice-bean optical signature).
    thresholds:
        Model thresholds (strong/ultrastrong boundaries).
    coupling_fraction:
        Light-matter coupling as a fraction of the plasmon energy (g = frac*hw_p).
        A stand-in for oscillator strength / mode overlap. `TODO(dft)`: compute.
    cavity_loss_ev, matter_loss_ev:
        Photon and electronic dephasing rates (as energies).
    effective_mass_ratio:
        m*/m_e for the carriers.
    spin_polarization:
        Moment proxy in [0,1], drives the triplet-only magnetic-drive-response
        MODEL PROXY (Level 2). Default 0.0 keeps existing callers byte-identical.
    symmetry:
        Assumed ``PairingSymmetry``; ``None`` is treated as UNDETERMINED (no
        magnetic-drive channel credited), keeping the toy path byte-identical.
    """
    from .magnetic_field import PairingSymmetry as _PS

    hw_p = plasmon_energy_ev(number_density_m3, effective_mass_ratio)
    long_ev, trans_ev = anisotropic_plasmon_energies(hw_p, anisotropy_score)

    mode = ElectromagneticMode(
        mode_energy_ev=hw_p,
        coupling_energy_ev=coupling_fraction * hw_p,
        cavity_loss_ev=cavity_loss_ev,
        matter_loss_ev=matter_loss_ev,
    )
    regime = coupling_regime(mode, thresholds)
    score = polariton_coherence_score(mode, thresholds)
    sym = _PS.UNDETERMINED if symmetry is None else symmetry
    drive = magnetic_drive_response(score, spin_polarization, sym)

    return CoherenceResult(
        mode=mode,
        regime=regime,
        coherence_score=score,
        plasmon_longitudinal_ev=long_ev,
        plasmon_transverse_ev=trans_ev,
        magnetic_drive_response=drive,
    )
