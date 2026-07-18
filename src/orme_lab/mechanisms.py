"""Mechanism-specific pairing tracks (#6).

Independent pairing-mechanism channels, each with its own necessary conditions and rejection
rules. A candidate is credited as a superconductivity lead only if **at least one complete
mechanism survives end-to-end** — partial strengths are never combined into one synthetic
score. The load-bearing separation: a static local moment *pair-breaks* singlet phonon pairing
(so a high-spin candidate has no ``M_phonon`` channel) but *enables* the magnetic channels
(``M_spin_fluctuation``/``M_triplet``) — which resolves the high-spin ⊥ singlet-EPW tension the
lab hit empirically (Tier-2 Ir moment collapse).

Honesty: ``M_phonon`` and ``M_granular_josephson`` reuse established physics (Abrikosov–Gor'kov
pair-breaking; Abeles-1977 / Ambegaokar–Baratoff granular Josephson, per
``research-wiki/prior-art/granular-josephson-network-channel.md``). The magnetic and excitonic
tracks ship as explicitly-labelled SURROGATES (``is_surrogate=True``): coarse susceptibility/
Hubbard-style stand-ins with real necessary conditions, NOT computed pairing kernels. Every
threshold is a documented constant, not tuned to pass favourites.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

from .config import ModelThresholds

# --- documented threshold constants (assumptions) -------------------------------
PB_MOMENT_MAX = 0.5   # spin_polarization at/above which a static moment pair-breaks singlet phonon SC
MOMENT_MIN = 0.2      # minimum local moment for a magnetically-mediated / triplet channel
EM_STRONG_FLOOR = 0.5 # minimum EM coherence for the (speculative) excitonic/polaritonic glue
EJEC_SCALE = 1.0      # E_J/E_C ~ EJEC_SCALE * coupling * n_atoms (derived from existing state; no free knob)


class Mechanism(str, Enum):
    PHONON = "M_phonon"
    SPIN_FLUCTUATION = "M_spin_fluctuation"
    TRIPLET = "M_triplet"
    EXCITONIC_POLARITONIC = "M_excitonic_polaritonic"
    GRANULAR_JOSEPHSON = "M_granular_josephson"
    DRIVE = "M_drive"


@dataclass(frozen=True)
class MechanismResult:
    mechanism: str
    survives: bool
    plausibility: float          # 0 unless every necessary condition passes
    is_surrogate: bool           # True for the coarse (spin-fluctuation/triplet/excitonic) tracks
    rejection: str               # "" if it survives; else why it was rejected
    note: str


def _reject(mech: Mechanism, why: str, surrogate: bool) -> MechanismResult:
    return MechanismResult(mech.value, False, 0.0, surrogate, why, "")


def _phonon(coupling: float, carrier: float, stability: float, spin_pol: float,
            th: ModelThresholds) -> MechanismResult:
    if coupling < th.min_coupling_for_bulk:
        return _reject(Mechanism.PHONON, "coupling below bulk floor", False)
    if carrier < th.min_carrier_proxy:
        return _reject(Mechanism.PHONON, "carrier proxy below floor", False)
    if stability < th.min_structural_stability:
        return _reject(Mechanism.PHONON, "structural stability below floor", False)
    if spin_pol >= PB_MOMENT_MAX:
        return _reject(
            Mechanism.PHONON,
            f"magnetic pair-breaking: local moment (spin_pol={spin_pol:.2f}) ≥ {PB_MOMENT_MAX} "
            f"pair-breaks singlet phonon pairing (Abrikosov–Gor'kov)", False)
    pb = max(0.0, 1.0 - spin_pol / PB_MOMENT_MAX)          # graded moment penalty
    return MechanismResult(Mechanism.PHONON.value, True, coupling * carrier * stability * pb,
                           False, "", f"singlet electron–phonon; moment penalty ×{pb:.2f}")


def _spin_fluctuation(coupling: float, spin_pol: float, th: ModelThresholds) -> MechanismResult:
    if spin_pol < MOMENT_MIN:
        return _reject(Mechanism.SPIN_FLUCTUATION, "no local moment to mediate fluctuations", True)
    if coupling < th.min_coupling_for_bulk:
        return _reject(Mechanism.SPIN_FLUCTUATION, "coupling below floor (no neighbours to mediate)", True)
    return MechanismResult(Mechanism.SPIN_FLUCTUATION.value, True, spin_pol * coupling, True, "",
                           "SURROGATE: magnetically-mediated (susceptibility/Hubbard-style), not a computed kernel")


def _triplet(coupling: float, spin_pol: float, th: ModelThresholds) -> MechanismResult:
    if coupling < th.min_coupling_for_bulk:
        return _reject(Mechanism.TRIPLET, "coupling below floor", True)
    if spin_pol < MOMENT_MIN:
        return _reject(Mechanism.TRIPLET, "no moment for a triplet channel", True)
    return MechanismResult(Mechanism.TRIPLET.value, True, spin_pol * coupling, True, "",
                           "SURROGATE: odd-parity triplet (moment-compatible; PGM spin–orbit assumed)")


def _excitonic(coupling: float, em_score: float | None, th: ModelThresholds) -> MechanismResult:
    if em_score is None:
        return _reject(Mechanism.EXCITONIC_POLARITONIC, "EM coherence not computed (compute_em_coherence off)", True)
    if em_score < EM_STRONG_FLOOR:
        return _reject(Mechanism.EXCITONIC_POLARITONIC, "EM coherence below strong-coupling floor", True)
    if coupling < th.min_coupling_for_bulk:
        return _reject(Mechanism.EXCITONIC_POLARITONIC, "coupling below floor", True)
    return MechanismResult(Mechanism.EXCITONIC_POLARITONIC.value, True, em_score * coupling, True, "",
                           "SURROGATE/speculative: EM coherence repurposed as excitonic/polaritonic glue "
                           "(normally the H12/H16 mundane alternative)")


def _drive(coupling: float, spin_pol: float, em_score: float | None,
           th: ModelThresholds) -> MechanismResult:
    if em_score is None:
        return _reject(Mechanism.DRIVE, "EM coherence not computed (compute_em_coherence off)", True)
    if spin_pol < MOMENT_MIN:
        return _reject(Mechanism.DRIVE, "no moment for a magnetic drive channel", True)
    if em_score < EM_STRONG_FLOOR:
        return _reject(Mechanism.DRIVE, "EM coherence below strong-coupling floor", True)
    if coupling < th.min_coupling_for_bulk:
        return _reject(Mechanism.DRIVE, "coupling below floor", True)
    return MechanismResult(Mechanism.DRIVE.value, True, em_score * spin_pol * coupling, True, "",
                           "SURROGATE: spin/magnetic AC-drive (magnon-BEC analogue), not a computed kernel")


def _granular(coupling: float, n_atoms: int, th: ModelThresholds) -> MechanismResult:
    if n_atoms < 2:
        return _reject(Mechanism.GRANULAR_JOSEPHSON, "single unit — no Josephson network", False)
    ratio = EJEC_SCALE * coupling * n_atoms               # E_J/E_C from existing state (no free knob)
    if ratio < 1.0:
        return _reject(Mechanism.GRANULAR_JOSEPHSON,
                       f"E_J/E_C={ratio:.2f} < 1 — phase-incoherent (below the percolation threshold)", False)
    return MechanismResult(Mechanism.GRANULAR_JOSEPHSON.value, True, min(1.0, ratio - 1.0), False, "",
                           f"granular Josephson network E_J/E_C={ratio:.2f} (Abeles 1977; Ambegaokar–Baratoff)")


#: is_surrogate flag per mechanism (for the global-rejection path).
_SURROGATE = {
    Mechanism.PHONON: False, Mechanism.SPIN_FLUCTUATION: True, Mechanism.TRIPLET: True,
    Mechanism.EXCITONIC_POLARITONIC: True, Mechanism.GRANULAR_JOSEPHSON: False,
    Mechanism.DRIVE: True,
}


from .magnetic_field import PairingSymmetry

#: Which pairing mechanisms a candidate may be CREDITED by, per assumed pairing symmetry.
#: UNDETERMINED credits all (default, unchanged). SINGLET: conventional singlet channels.
#: TRIPLET: moment-carrying (equal-spin) channels. This routes spin to ONE sign per hypothesis.
_CREDITABLE = {
    PairingSymmetry.UNDETERMINED: frozenset(Mechanism),
    PairingSymmetry.SINGLET: frozenset({Mechanism.PHONON, Mechanism.GRANULAR_JOSEPHSON}),
    PairingSymmetry.TRIPLET: frozenset({Mechanism.TRIPLET, Mechanism.SPIN_FLUCTUATION, Mechanism.DRIVE}),
}


def creditable_under(symmetry: PairingSymmetry) -> frozenset:
    return _CREDITABLE[symmetry]


def filter_by_symmetry(results: tuple[MechanismResult, ...],
                       symmetry: PairingSymmetry) -> tuple[MechanismResult, ...]:
    """Return only the mechanism results creditable under `symmetry`. A survivor of an
    incompatible symmetry is demoted to non-surviving (its physics is real but does not
    support THIS hypothesis's pairing assumption)."""
    ok = creditable_under(symmetry)
    out = []
    for r in results:
        if Mechanism(r.mechanism) in ok:
            out.append(r)
        else:
            out.append(MechanismResult(r.mechanism, False, 0.0, r.is_surrogate,
                                       f"not creditable under {symmetry.value} pairing", r.note))
    return tuple(out)


def evaluate_mechanisms(*, coupling: float, carrier_proxy: float, structural_stability: float,
                        field_suppression: float, observable_signal: float,
                        spin_polarization: float, em_coherence_score: float | None, n_atoms: int,
                        thresholds: ModelThresholds) -> tuple[MechanismResult, ...]:
    """Evaluate all five pairing-mechanism tracks. Order is fixed and deterministic.

    Global necessary conditions shared by EVERY mechanism (they mirror the generic SC gate's
    field/observable floors, so the mechanism attribution stays consistent with
    ``plaus.all_passed``): a candidate destroyed by an applied field, or with no measurable
    observable, has NO viable SC phase regardless of pairing channel — every track is rejected.
    """
    # A non-finite gate value (NaN/inf, e.g. a FIELD_RESPONSE backend returning a non-finite
    # critical field under a nonzero applied field) must reject too: `NaN < threshold` is False,
    # so a bare `<` would let every channel through while the generic gate's `NaN >= threshold`
    # (also False) fails `field_tolerance` — the exact survivors-vs-all_passed inconsistency this
    # global gate exists to prevent.
    if not math.isfinite(field_suppression) or field_suppression < thresholds.min_field_tolerance:
        why = (f"field-suppressed: field tolerance {field_suppression:.2f} < "
               f"{thresholds.min_field_tolerance} (no robust SC phase in any channel)")
        return tuple(_reject(m, why, _SURROGATE[m]) for m in Mechanism)
    if not math.isfinite(observable_signal) or observable_signal < thresholds.min_observable_signal:
        why = (f"no measurable observable: signal {observable_signal:.2f} < "
               f"{thresholds.min_observable_signal} (unfalsifiable in any channel)")
        return tuple(_reject(m, why, _SURROGATE[m]) for m in Mechanism)

    return (
        _phonon(coupling, carrier_proxy, structural_stability, spin_polarization, thresholds),
        _spin_fluctuation(coupling, spin_polarization, thresholds),
        _triplet(coupling, spin_polarization, thresholds),
        _excitonic(coupling, em_coherence_score, thresholds),
        _granular(coupling, n_atoms, thresholds),
        _drive(coupling, spin_polarization, em_coherence_score, thresholds),
    )


def surviving(results: tuple[MechanismResult, ...]) -> tuple[str, ...]:
    return tuple(m.mechanism for m in results if m.survives)


def summarize(results: tuple[MechanismResult, ...]) -> str:
    surv = surviving(results)
    rejected = "; ".join(f"{m.mechanism}✗ {m.rejection}" for m in results if not m.survives)
    return f"survivors: {', '.join(surv) if surv else 'NONE'} | {rejected}"
