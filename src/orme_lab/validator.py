"""Generalized adversarial validator — the decisive-experiment designer.

Lifts the ``control_experiment.py`` pattern (one IR-doublet case) to a per-candidate engine:
for a candidate it designs the experiments that would separate a genuine coherent (ORME-like)
phase from the strongest mundane alternatives, **attacking the ordinary explanations first**.
Each ``AdversarialTest`` carries the seven fields the operator specified: claimed signature,
strongest mundane alternative(s), control sample, required instrument, expected result under
each hypothesis, rejection threshold, and the evidence-level change a confirmed result permits.

The claimed signature is **mechanism-specific**: the validator reads the candidate's
``surviving_mechanisms`` (#6) and emits the decisive experiment for each surviving channel — so
a high-spin candidate (phonon pair-broken) is told to look for the triplet/granular signatures
(NMR Knight shift, Shapiro steps), NOT the phonon isotope effect. This is a Level-3 *laboratory
prediction*: the lab designs the experiment; it cannot run it.
"""
from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceLevel, PREDICTION_CEILING
from .mechanisms import Mechanism
from .pipeline import CandidateRecord

_LAB_PRED = int(EvidenceLevel(min(EvidenceLevel.LABORATORY_PREDICTION, PREDICTION_CEILING)))  # 3
_INITIAL_OBS = int(EvidenceLevel.INITIAL_OBSERVATION)                                          # 4

#: Blinded controls run alongside every measurement (operator's list).
CONTROL_SAMPLES: tuple[str, ...] = (
    "empty holder", "substrate-only blank", "ordinary PGM salt",
    "metallic PGM nanoparticles", "known diamagnet", "coded duplicate specimens",
)


@dataclass(frozen=True)
class AdversarialTest:
    measurement: str
    instrument: str
    claimed_signature: str                            # coherent-phase / mechanism prediction
    mundane_alternatives: tuple[tuple[str, str], ...]  # (alternative, expected_result) — attacked first
    control_samples: tuple[str, ...]
    rejection_threshold: str                          # the result that KILLS the claim
    evidence_level_if_confirmed: int                  # level a positive result would reach
    decisive: bool                                    # separates the claim from ALL listed alternatives?
    mechanism: str | None                             # surviving mechanism this test targets (None = generic)
    evidence_level: int                               # of THIS design = LABORATORY_PREDICTION (3)
    note: str = ""


def _test(measurement, instrument, claimed, alts, rejection, decisive, mechanism=None,
          ev_conf=_INITIAL_OBS, note=""):
    return AdversarialTest(measurement, instrument, claimed, tuple(alts), CONTROL_SAMPLES,
                           rejection, ev_conf, decisive, mechanism, _LAB_PRED, note)


def _generic_tests() -> tuple[AdversarialTest, ...]:
    """The operator's branch table: each measurement vs metallic-filament / ionic / artifact."""
    return (
        _test("R(T,B,I)", "4-probe transport (T/B/I sweeps)",
              "R→0 with a sharp/structured transition, field- and current-dependent",
              [("metallic filament/percolation", "weak metallic T-dependence, no sharp transition"),
               ("ionic conduction", "strong frequency/time dependence, electrode polarization"),
               ("contact/measurement artifact", "irreproducible, contact-dependent")],
              "finite R at all T, or no field/current dependence → not superconducting", True),
        _test("Meissner flux expulsion", "SQUID magnetometry (ZFC/FC vs field)",
              "field-dependent diamagnetic (Meissner) transition; demagnetization-corrected shielding",
              [("metallic filament", "little bulk diamagnetic shielding"),
               ("ionic conduction", "no diamagnetic screening"),
               ("artifact", "trapped flux only, no active expulsion")],
              "no diamagnetic transition despite 'zero R' → artifact / not superconducting", True),
        _test("current reversal", "I–V under current reversal",
              "symmetric voltage (ohmic- or Josephson-symmetric)",
              [("metallic filament", "symmetric"),
               ("ionic conduction", "polarization / hysteresis (asymmetric)")],
              "polarization or hysteresis → ionic, not superconducting", False,
              note="distinguishes ionic conduction; does NOT separate a metallic filament (also symmetric)"),
        _test("AC frequency sweep", "impedance vs frequency",
              "stable electronic response across frequency",
              [("metallic filament", "stable"),
               ("ionic conduction", "dispersive (strongly frequency-dependent)")],
              "dispersive response → ionic, not superconducting", False,
              note="distinguishes ionic conduction; does NOT separate a metallic filament"),
        _test("heat-capacity anomaly", "calorimetry (ΔC/γT_c at T_c)",
              "bulk anomaly if the superconducting volume fraction is sufficient",
              [("metallic filament", "absent"), ("ionic conduction", "absent")],
              "no resolvable anomaly → upper bound on the BULK SC fraction (does not alone exclude "
              "filamentary / granular / broadened SC)", True,
              note="per the corrected ΔC/γT_c gate: bounds the bulk fraction, not a universal exclusion"),
        _test("sample subdivision", "subdivide sample + re-measure",
              "characteristic coherence effect (grain-size dependence of T_c / screening)",
              [("metallic filament", "conductive path easily destroyed by subdivision"),
               ("ionic conduction", "geometry / moisture sensitive, not a coherence effect")],
              "response destroyed trivially, or geometry/moisture-driven → percolation/ionic, not "
              "bulk-coherent", True),
    )


# One decisive experiment per pairing mechanism (emitted only for SURVIVING mechanisms).
def _mech_test(mech: str) -> AdversarialTest | None:
    if mech == Mechanism.PHONON.value:
        return _test("isotope effect", "T_c vs isotopic mass",
                     "T_c ∝ M^−α with α≈0.5 (phonon-mediated pairing)",
                     [("non-phononic pairing", "no isotope shift"), ("artifact", "no transition")],
                     "absent isotope shift → non-phononic (or artifact)", True, mech)
    if mech == Mechanism.GRANULAR_JOSEPHSON.value:
        return _test("Shapiro steps", "I–V under microwave (RF) drive",
                     "Shapiro steps at V = n·h·f/2e (ac-Josephson phase locking)",
                     [("ordinary metal", "no steps"), ("ionic conduction", "no steps; dispersive")],
                     "no Shapiro steps under RF drive → no phase-locked Josephson network", True, mech)
    if mech == Mechanism.TRIPLET.value:
        return _test("NMR Knight shift + H_c2", "NMR through T_c; H_c2 vs the Pauli limit",
                     "Knight shift unchanged through T_c (spin-triplet); H_c2 exceeds the Pauli limit",
                     [("singlet SC", "Knight shift drops below T_c; H_c2 ≤ Pauli limit"),
                      ("no SC", "no transition")],
                     "Knight-shift drop through T_c → singlet, not triplet", True, mech)
    if mech == Mechanism.SPIN_FLUCTUATION.value:
        return _test("magnetic-QCP tuning", "resistivity vs T; T_c vs pressure/field near a magnetic instability",
                     "non-Fermi-liquid resistivity; T_c peaks near a magnetic instability (spin-fluctuation glue)",
                     [("ordinary metal", "Fermi-liquid T² far from any instability"),
                      ("no SC", "no transition")],
                     "ordinary Fermi-liquid with no T_c enhancement near the instability → not "
                     "spin-fluctuation SC", True, mech)
    if mech == Mechanism.EXCITONIC_POLARITONIC.value:
        return _test("optical/THz vs DC", "ultrafast/optical + THz spectroscopy vs DC transport",
                     "coherent optical-frequency response distinct from (not reducible to) DC transport",
                     [("ordinary Drude metal", "conventional Drude optical response"),
                      ("H12/H16 EM coherence (mundane)", "optical coherence WITHOUT DC superconductivity")],
                     "optical coherence with no DC-SC counterpart → EM coherence (mundane), not SC", True,
                     mech, ev_conf=_LAB_PRED,
                     note="flagged: excitonic SC is speculative; a coherent optical response is normally "
                          "the H12/H16 mundane alternative, NOT superconductivity")
    return None


@dataclass(frozen=True)
class ValidationSuite:
    element: str
    surviving_mechanisms: tuple[str, ...]
    tests: tuple[AdversarialTest, ...]
    decisive_count: int

    def explain(self) -> str:
        routed = ", ".join(sorted({t.mechanism for t in self.tests if t.mechanism})) or "none"
        return (f"{len(self.tests)} decisive-experiment designs for {self.element} "
                f"({self.decisive_count} decisive); mechanism-routed tests for: {routed}. "
                f"Level-3 laboratory prediction — the lab designs these; running them needs a real "
                f"instrument and blinded controls.")


def design_validation(record: CandidateRecord, *,
                      observed_doublet: tuple[float, ...] | None = None) -> ValidationSuite:
    """Design the adversarial decisive-experiment suite for a candidate: the generic branch table
    plus one test per surviving pairing mechanism (#6), plus the IR-doublet control if a doublet
    is supplied."""
    tests = list(_generic_tests())
    for mech in record.surviving_mechanisms:
        t = _mech_test(mech)
        if t is not None:
            tests.append(t)

    if observed_doublet is not None:
        from .control_experiment import design_control_experiment
        ce = design_control_experiment(tuple(observed_doublet), metal_symbol=record.element)
        for p in ce.predictions:
            tests.append(AdversarialTest(
                measurement=p.measurement, instrument="IR/Raman spectroscopy",
                claimed_signature=p.expected_under_intrinsic,        # metal-intrinsic (the ORME reading)
                mundane_alternatives=(("carboxylate contaminant (H_contaminant)", p.expected_under_contaminant),),
                control_samples=CONTROL_SAMPLES,
                rejection_threshold="matches the contaminant prediction → mundane surface species, not intrinsic",
                evidence_level_if_confirmed=_LAB_PRED, decisive=p.decisive,
                mechanism=Mechanism.EXCITONIC_POLARITONIC.value, evidence_level=int(p.evidence_level),
                note="IR-doublet control (folded from control_experiment.py)"))

    tests_t = tuple(tests)
    return ValidationSuite(record.element, record.surviving_mechanisms, tests_t,
                           sum(1 for t in tests_t if t.decisive))
