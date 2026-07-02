"""End-to-end screening pipeline.

Ties the modules together into a single reproducible screen:

    element -> geometry -> spin state -> density anisotropy -> coupling
            -> carrier proxy -> field response -> observables
            -> superconductivity plausibility -> ranked record

The output is a list of :class:`CandidateRecord` (and a CSV writer), ranked so
the most plausible-but-not-ruled-out candidates surface first. Nothing here
proves anything; it prioritizes *which candidates deserve real computation and
measurement*, and — just as importantly — records which are already ruled out
and why.

Determinism: given the same :class:`~orme_lab.config.LabConfig`, a screen
produces byte-identical output. No wall-clock, no unseeded RNG. Records are
sorted by a total, tie-broken key so ordering is stable.
"""

from __future__ import annotations

import csv
import math
from dataclasses import asdict, dataclass, field

from .config import DEFAULT_CONFIG, LabConfig
from .coupling import inter_unit_coupling_score, is_electronically_isolated
from .evidence import badge as evidence_badge, candidate_evidence_level
from .electron_density import ricebean_score
from .elements import Element, core_screen_elements
from .geometry import (
    ClusterGeometry,
    make_compact_cluster,
    make_dimer,
    make_linear_chain,
    make_monomer,
)
from .magnetic_field import magnetic_field_suppression_factor
from .observables import ObservableSet, predict_observables
from .spin_states import SpinState, high_spin_state, low_spin_state, spin_polarization_score
from .superconductivity import (
    PlausibilityResult,
    carrier_coherence_proxy,
    superconductivity_plausibility_score,
)


def structural_stability_proxy(geometry: ClusterGeometry) -> float:
    """Toy structural-stability proxy in [0, 1] from mean coordination.

    More neighbours -> a more bulk-like, less fragile arrangement. Normalized
    against close-packed coordination (~12). A monomer (coordination 0) scores 0
    and cannot clear the stability gate. Not an energy calculation.
    """
    return math.tanh(geometry.mean_coordination / 8.0)


def critical_field_proxy(spin_score: float, coupling_score: float) -> float:
    """Toy critical field (tesla) for the candidate SC phase.

    Heuristic: a stronger, better-coupled candidate tolerates a larger field.
    Scaled to a few tesla so that typical screening fields probe the transition.
    This is an assumption purely for ranking, not a computed Hc2.
    """
    return 5.0 * coupling_score * (0.5 + 0.5 * spin_score)


@dataclass(frozen=True)
class CandidateRecord:
    """One fully-scored candidate (element x geometry x spin state)."""

    element: str
    geometry: str
    n_atoms: int
    spin_label: str
    unpaired_electrons: int
    spin_polarization: float
    anisotropy: float
    is_ricebean: bool
    coupling: float
    isolated: bool
    carrier_proxy: float
    field_suppression: float
    structural_stability: float
    observable_signal: float
    resistance_regime: str
    meissner_screening: float
    susceptibility: float
    sc_plausibility: float
    ruled_out: bool
    evidence_level: int
    verdict: str

    def as_csv_row(self) -> dict[str, object]:
        row = asdict(self)
        # round floats for stable, readable CSV output
        for k, v in row.items():
            if isinstance(v, float):
                row[k] = round(v, 6)
        return row


# The default geometry set spans the isolated -> connected axis so hypothesis 5
# is always exercised (a monomer should be ruled out; a compact cluster may not).
def default_geometries(element: Element) -> list[ClusterGeometry]:
    return [
        make_monomer(element),
        make_dimer(element),
        make_linear_chain(element, 4),
        make_compact_cluster(element, 13),
    ]


def _spin_states(element: Element) -> list[tuple[str, SpinState]]:
    return [("high_spin", high_spin_state(element)), ("low_spin", low_spin_state(element))]


def evaluate_candidate(
    element: Element,
    geometry: ClusterGeometry,
    spin_label: str,
    state: SpinState,
    config: LabConfig,
) -> CandidateRecord:
    """Run one candidate through the full scoring chain."""
    th = config.thresholds

    spin_pol = spin_polarization_score(state)
    anisotropy, ricebean = ricebean_score(state, th)

    coupling = inter_unit_coupling_score(geometry, th)
    isolated = is_electronically_isolated(coupling, th)

    carrier = carrier_coherence_proxy(coupling, anisotropy)

    crit_field = critical_field_proxy(spin_pol, coupling)
    suppression = magnetic_field_suppression_factor(config.applied_field_t, crit_field)

    stability = structural_stability_proxy(geometry)

    obs: ObservableSet = predict_observables(
        state=state,
        coupling_score=coupling,
        carrier_proxy=carrier,
        temperature_k=config.temperature_k,
        applied_field_t=config.applied_field_t,
        critical_field_t=crit_field,
    )
    # Strongest single observable magnitude, clamped to [0,1] for the gate.
    observable_signal = min(1.0, max(obs.meissner_screening, math.tanh(abs(obs.molar_susceptibility))))

    plaus: PlausibilityResult = superconductivity_plausibility_score(
        coupling_score=coupling,
        carrier_proxy=carrier,
        field_suppression=suppression,
        structural_stability=stability,
        observable_signal=observable_signal,
        thresholds=th,
    )

    return CandidateRecord(
        element=element.symbol,
        geometry=geometry.label,
        n_atoms=geometry.n_atoms,
        spin_label=spin_label,
        unpaired_electrons=state.unpaired_electrons,
        spin_polarization=spin_pol,
        anisotropy=anisotropy,
        is_ricebean=ricebean,
        coupling=coupling,
        isolated=isolated,
        carrier_proxy=carrier,
        field_suppression=suppression,
        structural_stability=stability,
        observable_signal=observable_signal,
        resistance_regime=obs.resistance_regime,
        meissner_screening=obs.meissner_screening,
        susceptibility=obs.molar_susceptibility,
        sc_plausibility=plaus.score,
        ruled_out=not plaus.all_passed,
        evidence_level=int(candidate_evidence_level(not plaus.all_passed)),
        verdict=f"{plaus.explain()} [{evidence_badge(candidate_evidence_level(not plaus.all_passed))}]",
    )


def _sort_key(rec: CandidateRecord) -> tuple:
    """Stable ranking key: plausible first, then by supporting scores, then by
    a deterministic tie-break on identity so output never depends on input order
    or dict iteration."""
    return (
        -rec.sc_plausibility,
        -rec.coupling,
        -rec.spin_polarization,
        rec.element,
        rec.geometry,
        rec.spin_label,
    )


def run_screen(
    elements: list[Element] | None = None,
    config: LabConfig = DEFAULT_CONFIG,
    geometry_factory=default_geometries,
) -> list[CandidateRecord]:
    """Screen a set of elements across geometries and spin states.

    Returns records sorted best-candidate-first (deterministically). Defaults to
    the six spec elements (Au, Pt, Pd, Ir, Rh, Os).
    """
    els = elements if elements is not None else core_screen_elements()
    records: list[CandidateRecord] = []
    for el in els:
        for geom in geometry_factory(el):
            for spin_label, state in _spin_states(el):
                records.append(evaluate_candidate(el, geom, spin_label, state, config))
    records.sort(key=_sort_key)
    return records


def write_csv(records: list[CandidateRecord], path: str) -> str:
    """Write ranked records to ``path`` as CSV. Returns the path written."""
    if not records:
        raise ValueError("no records to write")
    fieldnames = list(records[0].as_csv_row().keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow(rec.as_csv_row())
    return path
