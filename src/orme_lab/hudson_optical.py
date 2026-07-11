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
from enum import Enum

from .config import ModelThresholds, SPEED_OF_LIGHT
from .electromagnetic_coherence import ElectromagneticMode, coupling_regime
from .evidence import EvidenceLevel


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
