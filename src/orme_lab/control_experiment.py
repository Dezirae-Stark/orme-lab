"""IR-doublet control experiment — decisive-measurement predictor (Level 3).

Triage becomes a prediction. The contaminant screen (``ir_contaminant.py``) found the
patent's 1400-1600 cm^-1 doublet (DE3920144A1) *plausibly* a carboxylate surface
contaminant, with metal-metal bonding excluded — but a reachability match cannot decide
ORIGIN. This module computes, for each of three controls, what two competing hypotheses
predict and flags where they differ (= decisive):

  H_contaminant  — the doublet is a light-atom (C-O carboxylate) surface species.
  H_intrinsic    — the doublet is intrinsic to the metal (metal-metal / high-spin ORME state).

Neutral by construction: it predicts the outcome under BOTH hypotheses and decides neither.
These are the lab's first Level-3 (LABORATORY_PREDICTION) artifacts — the rung ``evidence.py``
already defines and ``candidate_evidence_level`` already returns. The lab *designs* the
experiment; it cannot *run* it (Level 4+ needs a real instrument).

Physics, all textbook and cited:
  - harmonic diatomic nu ~ 1/sqrt(mu)  (isotope shift)          — Herzberg; Atkins
  - Raman/IR mutual-exclusion rule for centrosymmetric species  — Atkins; Harris
  - band area A ~ N absorbers (Beer-Lambert) x coverage (Langmuir 1918)
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, PREDICTION_CEILING
from .ir_signature import _reduced_mass

DETECTION_FLOOR_CM = 2.0  # conservative FTIR peak-position resolution (cm^-1)

# Dominant-isotope masses (amu), CODATA/CRC — specific isotopes, not natural averages.
_ISO = {"C": 12.000000, "O": 15.994915, "N": 14.003074, "Rh": 102.905, "Ir": 192.217}
# label -> (element substituted, substituted-isotope mass amu)
_LABEL = {
    "13C": ("C", 13.003355),
    "18O": ("O", 17.999160),
    "15N": ("N", 15.000109),
}


def _pred_level() -> EvidenceLevel:
    return EvidenceLevel(min(EvidenceLevel.LABORATORY_PREDICTION, PREDICTION_CEILING))


@dataclass(frozen=True)
class Prediction:
    measurement: str
    expected_under_contaminant: str
    expected_under_intrinsic: str
    decisive: bool
    evidence_level: EvidenceLevel
    note: str = ""


def _shift_for_bond(nu_cm: float, bond: tuple[str, str], label: str) -> float:
    """Isotopic red-shift (cm^-1) of a line at ``nu_cm`` for a diatomic ``bond`` under
    ``label``. Returns 0.0 if the labelled element is not in the bond (the label does
    not apply — e.g. 15N on a C-O bond, or any C/O/N label on a metal-metal bond)."""
    elem, iso_mass = _LABEL[label]
    if elem not in bond:
        return 0.0
    masses = [_ISO[bond[0]], _ISO[bond[1]]]
    for i, sym in enumerate(bond):
        if sym == elem:
            masses[i] = iso_mass  # substitute the first matching atom
            break
    mu_old = _reduced_mass(_ISO[bond[0]], _ISO[bond[1]])
    mu_new = _reduced_mass(masses[0], masses[1])
    return nu_cm * (math.sqrt(mu_old / mu_new) - 1.0)


def predict_isotope_shift(lines_cm: tuple[float, ...], label: str,
                          contaminant_bond: tuple[str, str] = ("C", "O"),
                          intrinsic_bond: tuple[str, str] = ("Rh", "Rh")) -> Prediction:
    """Predict the isotopic-substitution shift of the doublet's upper line under each
    hypothesis. A light-atom bond shifts; a metal-metal bond (no C/O/N) does not."""
    hi = max(lines_cm)
    sc = _shift_for_bond(hi, contaminant_bond, label)
    si = _shift_for_bond(hi, intrinsic_bond, label)
    decisive = abs(sc - si) > DETECTION_FLOOR_CM
    return Prediction(
        measurement=f"{label} isotopic substitution, re-measure the ~{hi:.0f} cm^-1 line",
        expected_under_contaminant=f"red-shift ~{sc:.0f} cm^-1 ({'-'.join(contaminant_bond)} bond)",
        expected_under_intrinsic=f"~{si:.0f} cm^-1 ({'-'.join(intrinsic_bond)} bond — label absent)",
        decisive=decisive,
        evidence_level=_pred_level(),
        note=("decisive: the label distinguishes the two origins beyond FTIR resolution"
              if decisive else
              f"NOT decisive: {label} does not test this bond (shift below the "
              f"{DETECTION_FLOOR_CM:.0f} cm^-1 floor) — pick an isotope of an atom in the bond"),
    )
