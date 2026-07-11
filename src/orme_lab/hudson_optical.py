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
from dataclasses import dataclass
from enum import Enum, IntEnum

from .config import ModelThresholds, SPEED_OF_LIGHT
from .electromagnetic_coherence import ElectromagneticMode, coupling_regime, evaluate_em_coherence
from .evidence import EvidenceLevel, LAB_CEILING


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


@dataclass(frozen=True)
class OpticalOrderParameter:
    """O_H = {omega0, Q, g, tau_coh, L_coh, f_ph, f_el} — the Hudson optical order
    parameter. All quantities are toy/surrogate and bounded; f_photon + f_electron
    == 1 by construction."""

    omega0_ev: float        # bare resonance energy
    quality_factor: float   # Q = omega / kappa
    coupling_ev: float      # light-matter coupling g
    tau_coh_fs: float       # temporal coherence lifetime
    l_coh_nm: float         # spatial coherence length (surrogate)
    f_photon: float         # photonic (Hopfield) fraction of the lower polariton
    f_electron: float       # electronic fraction (= 1 - f_photon)


def order_parameter_from_mode(mode, matter_ev: float,
                              thresholds: ModelThresholds) -> OpticalOrderParameter:
    """Assemble O_H for one coupled mode.

    The spatial coherence length is a flagged surrogate L_coh = frac * c * tau_coh
    (a propagating coherent mode travels ~v_g * tau before dephasing; v_g is
    unknown here, so ``hudson_group_velocity_fraction`` stands in for v_g/c).
    """
    f_ph, f_el = mode_composition(matter_ev, mode.mode_energy_ev, mode.coupling_energy_ev)
    tau_s = mode.coherence_lifetime_fs * 1e-15 if math.isfinite(mode.coherence_lifetime_fs) else math.inf
    if math.isinf(tau_s):
        l_coh_nm = math.inf
    else:
        l_coh_m = thresholds.hudson_group_velocity_fraction * SPEED_OF_LIGHT * tau_s
        l_coh_nm = l_coh_m * 1e9
    return OpticalOrderParameter(
        omega0_ev=mode.mode_energy_ev,
        quality_factor=mode.quality_factor,
        coupling_ev=mode.coupling_energy_ev,
        tau_coh_fs=mode.coherence_lifetime_fs,
        l_coh_nm=l_coh_nm,
        f_photon=f_ph,
        f_electron=f_el,
    )


class Persistence(str, Enum):
    """Post-drive ring-down class of the coherent mode."""
    DRIVEN_DISSIPATIVE = "driven_dissipative"   # decays on the mode timescale; needs pumping
    METASTABLE = "metastable"                   # long-lived but not self-sustaining
    PERSISTENT = "persistent"                   # effectively self-sustaining (Hudson's claim)


@dataclass(frozen=True)
class PersistenceResult:
    persistence: Persistence
    ratio: float | None            # measured / model-predicted decay time (None if unmeasured)
    predicted_fs: float            # driven-dissipative expectation (~ mode lifetime)
    measured_fs: float | None      # externally supplied ring-down time
    evidence_level_if_confirmed: int
    note: str


def classify_persistence(o_h: OpticalOrderParameter, *,
                         measured_ringdown_fs: float | None,
                         thresholds: ModelThresholds) -> PersistenceResult:
    """Classify the mode's post-drive ring-down.

    Persistence is Hudson's EXTRAORDINARY claim, so it is default-blocked: the model's
    predicted decay time is the mode lifetime (driven-dissipative expectation), and
    without an external measured ring-down the result is DRIVEN_DISSIPATIVE. A supplied
    measurement is compared to the prediction; a genuinely self-sustaining mode
    (ratio >= persistent_ratio) is the only path to a Level-4 observation.
    """
    predicted = o_h.tau_coh_fs
    if measured_ringdown_fs is None:
        return PersistenceResult(
            Persistence.DRIVEN_DISSIPATIVE, None, predicted, None,
            int(EvidenceLevel.LABORATORY_PREDICTION),
            "no measured ring-down; conservative driven-dissipative null. Persistence "
            "requires an external post-drive ring-down measurement (a lab input).")
    if not math.isfinite(predicted) or predicted <= 0:
        # a lossless model prediction is degenerate; refuse to credit persistence from it
        return PersistenceResult(
            Persistence.DRIVEN_DISSIPATIVE, None, predicted, measured_ringdown_fs,
            int(EvidenceLevel.LABORATORY_PREDICTION),
            "model predicts no finite decay (degenerate); cannot ratio a measurement against it.")
    ratio = measured_ringdown_fs / predicted
    if ratio >= thresholds.hudson_persistent_ratio:
        cls, note = Persistence.PERSISTENT, "measured ring-down >> mode lifetime: effectively self-sustaining."
    elif ratio >= thresholds.hudson_metastable_ratio:
        cls, note = Persistence.METASTABLE, "measured ring-down long but finite: metastable, not self-sustaining."
    else:
        cls, note = Persistence.DRIVEN_DISSIPATIVE, "measured ring-down ~ mode lifetime: driven-dissipative."
    ev = int(EvidenceLevel.INITIAL_OBSERVATION) if cls is Persistence.PERSISTENT \
        else int(EvidenceLevel.LABORATORY_PREDICTION)
    return PersistenceResult(cls, ratio, predicted, measured_ringdown_fs, ev, note)


#: Representative center energies (eV) for each band of the broadband survey.
#: Hudson described RF tuning while calling the internal state "light"; photons
#: span the whole spectrum, so the survey must not start at visible. Values are
#: order-of-magnitude band centers (RF ~ MHz-GHz ... near-UV ~ 3.5 eV).
SURVEY_BANDS: tuple[tuple[str, float], ...] = (
    ("RF", 4.0e-6),
    ("microwave", 4.0e-4),
    ("THz", 4.0e-3),
    ("IR", 1.0e-1),
    ("visible", 2.3),
    ("near-UV", 3.5),
)


@dataclass(frozen=True)
class BandResult:
    band: str
    center_ev: float
    regime: str
    cooperativity: float


def resonance_survey(coupling_fraction: float, cavity_loss_ev: float,
                     matter_loss_ev: float,
                     thresholds: ModelThresholds) -> tuple[BandResult, ...]:
    """Sweep every survey band, classifying the coupling regime and cooperativity.

    Each band is a mode at that center energy with g = coupling_fraction * center.
    Order is fixed (``SURVEY_BANDS``) and deterministic.
    """
    out = []
    for name, center in SURVEY_BANDS:
        mode = ElectromagneticMode(mode_energy_ev=center,
                                   coupling_energy_ev=coupling_fraction * center,
                                   cavity_loss_ev=cavity_loss_ev,
                                   matter_loss_ev=matter_loss_ev)
        out.append(BandResult(name, center, coupling_regime(mode, thresholds), mode.cooperativity))
    return tuple(out)


def strongest_band(results: tuple[BandResult, ...]) -> BandResult | None:
    """The non-weak band with the highest cooperativity, or None if all are weak.

    Ties resolve to the earliest band in ``SURVEY_BANDS`` order (deterministic)."""
    non_weak = [r for r in results if r.regime != "weak"]
    if not non_weak:
        return None
    best = non_weak[0]
    for r in non_weak[1:]:
        if r.cooperativity > best.cooperativity:
            best = r
    return best


@dataclass(frozen=True)
class CausalLink:
    """The C(omega) = dM/dP_drive test: does the magnetic response track the optical
    resonance? An optical anomaly with NO linked magnetic anomaly does not support
    full Hudson."""
    tracks: bool
    dM_dP: float | None
    on_resonance: bool | None
    evidence_level_if_confirmed: int
    note: str


def magnetism_tracks_resonance(*, measured_dM_dP: float | None = None,
                               on_resonance: bool | None = None,
                               min_response: float = 1e-9) -> CausalLink:
    """Default-blocked causal-magnetism gate.

    Requires an externally measured dM/dP that (a) is measured ON resonance and
    (b) exceeds ``min_response``. Absent a measurement, or off resonance, the link is
    unestablished. A confirmed on-resonance magnetic response is a Level-4 observation.
    """
    if measured_dM_dP is None or on_resonance is None:
        return CausalLink(False, measured_dM_dP, on_resonance,
                          int(EvidenceLevel.LABORATORY_PREDICTION),
                          "unestablished: requires a measured dM/dP taken while sweeping "
                          "through the optical/RF resonance (a lab input).")
    tracks = bool(on_resonance) and abs(measured_dM_dP) >= min_response
    ev = int(EvidenceLevel.INITIAL_OBSERVATION) if tracks else int(EvidenceLevel.LABORATORY_PREDICTION)
    if not on_resonance:
        note = "magnetic response measured off resonance: does not support the causal link."
    elif not tracks:
        note = "magnetic response at/below the noise floor on resonance: no anomaly."
    else:
        note = "magnetic response appears/strengthens on resonance: causal link supported."
    return CausalLink(tracks, measured_dM_dP, on_resonance, ev, note)


class HudsonClaim(IntEnum):
    """Hudson optical-coherence claim hierarchy (Branch B). Each level is an
    INDEPENDENT finding: a supported level does NOT imply the one below it. Levels
    9 (independent reproduction) and 10 (practical transduction) require real labs
    and are out of this module's scope."""
    RESONANCE_DETECTED = 1        # an EM resonance exists
    RESONANCE_ASSIGNED = 2        # assigned to the candidate material
    STRONG_COUPLING = 3           # strong light-matter coupling (hybrid mode)
    MACRO_COHERENCE = 4           # macroscopic optical coherence
    LOW_LOSS_TRANSPORT = 5        # low-loss coherent energy transport (persistence)
    ELECTRONIC_COUPLING = 6       # electronic coupling to the coherent mode
    MAGNETISM_COUPLED = 7         # magnetic response coupled to the coherent mode
    HUDSON_PHASE = 8              # full Hudson-type optical superconductive phase


@dataclass(frozen=True)
class HudsonOpticalResult:
    order_parameter: OpticalOrderParameter
    regime: str
    persistence: PersistenceResult
    causal_link: CausalLink
    strongest_band: "BandResult | None"
    supported: frozenset            # frozenset[HudsonClaim]
    evidence_level: int             # clamped to LAB_CEILING

    @property
    def highest_supported(self) -> int:
        return max((int(c) for c in self.supported), default=0)

    def explain(self) -> str:
        levels = ", ".join(str(int(c)) for c in sorted(self.supported)) or "none"
        return (
            f"Branch B (Hudson optical coherence): {self.regime} coupling; supported "
            f"claim levels {{{levels}}}. Persistence={self.persistence.persistence.value}; "
            f"causal magnetism tracks resonance={self.causal_link.tracks}. This is NOT "
            f"evidence of DC superconductivity (Branch A); a coherent optical mode without "
            f"a linked persistent, magnetically-coupled state remains an ordinary "
            f"driven-dissipative response. All quantities are toy/surrogate."
        )


def evaluate_hudson_optical(*, number_density_m3: float, anisotropy_score: float,
                            thresholds: ModelThresholds, matter_ev: float | None = None,
                            coupling_fraction: float = 0.05, cavity_loss_ev: float = 0.10,
                            matter_loss_ev: float = 0.05, effective_mass_ratio: float = 1.0,
                            measured_ringdown_fs: float | None = None,
                            measured_dM_dP: float | None = None,
                            dM_dP_on_resonance: bool | None = None) -> HudsonOpticalResult:
    """Full Branch-B evaluation for one candidate.

    Simulation-supportable levels (1-4, 6) come from the mode algebra; levels 5
    (transport/persistence) and 7 (causal magnetism) are default-blocked and require
    the optional measured inputs. Level 8 (full Hudson phase) is the conjunction of
    the strong-coupling, coherence, transport, electronic, and magnetism levels — a
    top-level PREDICTION, never a crediting verdict. ``evidence_level`` is what the
    SIMULATION produces and is clamped to LAB_CEILING regardless of folded lab inputs.
    """
    coh = evaluate_em_coherence(number_density_m3, anisotropy_score, thresholds,
                                coupling_fraction=coupling_fraction, cavity_loss_ev=cavity_loss_ev,
                                matter_loss_ev=matter_loss_ev, effective_mass_ratio=effective_mass_ratio)
    mode = coh.mode
    mev = mode.mode_energy_ev if matter_ev is None else matter_ev   # None -> on resonance
    o_h = order_parameter_from_mode(mode, mev, thresholds)
    persistence = classify_persistence(o_h, measured_ringdown_fs=measured_ringdown_fs, thresholds=thresholds)
    link = magnetism_tracks_resonance(measured_dM_dP=measured_dM_dP, on_resonance=dM_dP_on_resonance)
    survey = resonance_survey(coupling_fraction, cavity_loss_ev, matter_loss_ev, thresholds)
    best = strongest_band(survey)

    s: set = set()
    if mode.mode_energy_ev > 0:
        s.add(HudsonClaim.RESONANCE_DETECTED)
        s.add(HudsonClaim.RESONANCE_ASSIGNED)           # assigned to this candidate's carriers
    strong = coh.regime != "weak"
    if strong:
        s.add(HudsonClaim.STRONG_COUPLING)
    # macroscopic coherence: a genuine hybrid (photon fraction above floor) in a
    # non-weak regime with a positive coherence score.
    if strong and o_h.f_photon >= thresholds.hudson_min_photon_fraction and coh.coherence_score > 0:
        s.add(HudsonClaim.MACRO_COHERENCE)
    # electronic coupling to the mode: a non-negligible electronic (matter) fraction.
    if strong and o_h.f_electron >= thresholds.hudson_min_photon_fraction:
        s.add(HudsonClaim.ELECTRONIC_COUPLING)
    # transport (level 5) requires a persistent (or at least metastable) measured ring-down.
    if persistence.persistence in (Persistence.PERSISTENT, Persistence.METASTABLE):
        s.add(HudsonClaim.LOW_LOSS_TRANSPORT)
    # magnetism (level 7) requires the measured causal link.
    if link.tracks:
        s.add(HudsonClaim.MAGNETISM_COUPLED)
    # full Hudson phase (level 8): conjunction at the top — the coherent, transporting,
    # electronically-coupled, magnetically-coupled state.
    if {HudsonClaim.STRONG_COUPLING, HudsonClaim.MACRO_COHERENCE, HudsonClaim.LOW_LOSS_TRANSPORT,
        HudsonClaim.ELECTRONIC_COUPLING, HudsonClaim.MAGNETISM_COUPLED}.issubset(s):
        s.add(HudsonClaim.HUDSON_PHASE)

    ev = int(min(EvidenceLevel(int(LAB_CEILING)),
                 EvidenceLevel.SIMULATION_CANDIDATE if s else EvidenceLevel.CONCEPT))
    return HudsonOpticalResult(o_h, coh.regime, persistence, link, best, frozenset(s), ev)
