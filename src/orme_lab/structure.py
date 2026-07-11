"""Structural distribution — "monatomic" as a measured mixture, not a categorical label.

A real preparation is a *distribution* over structural populations — isolated atoms, dimers,
sub-nanometre clusters, larger particles — not a single geometry. This module represents that
mixture and consumes it two ways (operator review #7):

- a **coverage-weighted expected coupling** ``E[coupling] = Σ fraction · coupling(geometry)``,
  the aggregate the SC gate sees; and
- a **per-population verdict breakdown** — which *fraction of the material* actually survives
  the gate, so "82% dispersed, 14% dimers, 4% larger" turns into "96% ruled out as
  isolated/small; only the 4% cluster tail is even a candidate."

The existing per-candidate scoring (``evaluate_candidate``) is reused unchanged; this is a
sample-level layer on top of it. Feeds the #6 mechanism/coupling models.
"""
from __future__ import annotations

from dataclasses import dataclass

from .config import DEFAULT_CONFIG, LabConfig, ModelThresholds
from .coupling import inter_unit_coupling_score
from .elements import Element
from .geometry import ClusterGeometry, make_compact_cluster, make_dimer, make_monomer
from .identity import IdentityWitness
from .pipeline import evaluate_candidate
from .spin_states import SpinState


@dataclass(frozen=True)
class Population:
    geometry: ClusterGeometry
    fraction: float                      # 0..1, normalized across the distribution


@dataclass(frozen=True)
class StructuralDistribution:
    """A normalized mixture of structural populations (fractions sum to 1)."""
    populations: tuple[Population, ...]

    def f1(self) -> float:
        """Fraction of isolated PGM sites (monatomic, n_atoms == 1)."""
        return sum(p.fraction for p in self.populations if p.geometry.n_atoms == 1)

    def size_distribution(self) -> dict[int, float]:
        """P(n): cluster-size (n_atoms) → total fraction."""
        out: dict[int, float] = {}
        for p in self.populations:
            out[p.geometry.n_atoms] = out.get(p.geometry.n_atoms, 0.0) + p.fraction
        return out

    def nn_distances(self) -> tuple[tuple[float, float], ...]:
        """R_PGM–PGM: (nearest-neighbour distance, fraction) per population."""
        return tuple((p.geometry.nearest_neighbor_distance, p.fraction) for p in self.populations)

    def expected_coupling(self, thresholds: ModelThresholds) -> float:
        """Coverage-weighted expected inter-unit coupling over the mixture."""
        return sum(p.fraction * inter_unit_coupling_score(p.geometry, thresholds) for p in self.populations)


def make_distribution(pairs: list[tuple[ClusterGeometry, float]]) -> StructuralDistribution:
    """Build a normalized distribution from (geometry, weight) pairs. The existing geometries
    (monomer/dimer/cluster) are the distribution's support; weights are normalized to sum to 1."""
    if any(f < 0.0 for _, f in pairs):
        raise ValueError("structural population weights must be non-negative "
                         "(a fraction of the material cannot be negative)")
    total = sum(f for _, f in pairs)
    if total <= 0.0:
        # Degenerate / all-zero weights: fall back to uniform over the given geometries so the
        # 'fractions sum to 1' invariant holds (an empty input yields an empty distribution).
        n = len(pairs)
        return StructuralDistribution(tuple(Population(g, 1.0 / n) for g, _ in pairs) if n else ())
    return StructuralDistribution(tuple(Population(g, f / total) for g, f in pairs))


def dispersed_sample(element: Element, f1: float) -> StructuralDistribution:
    """Convenience: a plausible mixture from a single dispersion fraction ``f1`` (isolated
    sites), splitting the remainder between dimers and sub-nm clusters. For ergonomics only —
    a real sample's P(n) would come from EXAFS/STEM/PDF."""
    f1 = min(1.0, max(0.0, f1))
    rest = 1.0 - f1
    return make_distribution([
        (make_monomer(element), f1),
        (make_dimer(element), rest * 0.6),
        (make_compact_cluster(element, 13), rest * 0.4),
    ])


@dataclass(frozen=True)
class PopulationVerdict:
    geometry: str
    n_atoms: int
    fraction: float
    sc_plausibility: float
    ruled_out: bool
    credited_sc_lead: bool               # carries the G_identity dimension (False w/o a witness)
    identity_verdict: str


@dataclass(frozen=True)
class SampleRecord:
    element: str
    spin_label: str
    f1: float
    expected_coupling: float
    surviving_fraction: float            # Σ fraction of populations NOT ruled out
    credited_fraction: float             # Σ fraction CREDITED as SC leads (needs identity; 0 w/o)
    populations: tuple[PopulationVerdict, ...]
    note: str

    def explain(self) -> str:
        return self.note


def evaluate_sample(element: Element, distribution: StructuralDistribution, spin_label: str,
                    state: SpinState, config: LabConfig = DEFAULT_CONFIG,
                    identity: IdentityWitness | None = None) -> SampleRecord:
    """Score a heterogeneous sample: per-population verdicts + coverage-weighted aggregate.

    ``identity`` (one characterization witness for the whole sample) threads into every
    population's G_identity gate. Without it, no population is *credited* — ``credited_fraction``
    is 0 even where the SC proxies pass, consistent with the per-candidate layer.
    """
    verdicts = []
    surviving = 0.0
    credited = 0.0
    for p in distribution.populations:
        rec = evaluate_candidate(element, p.geometry, spin_label, state, config, identity=identity)
        verdicts.append(PopulationVerdict(
            geometry=p.geometry.label, n_atoms=p.geometry.n_atoms, fraction=p.fraction,
            sc_plausibility=rec.sc_plausibility, ruled_out=rec.ruled_out,
            credited_sc_lead=rec.credited_sc_lead, identity_verdict=rec.identity_verdict))
        if not rec.ruled_out:
            surviving += p.fraction
        if rec.credited_sc_lead:
            credited += p.fraction

    f1 = distribution.f1()
    # NOTE: expected_coupling recomputes coupling from geometry; identical to the per-population
    # values on the toy path. If a backend is ever threaded through, reuse rec.coupling here.
    exp_c = distribution.expected_coupling(config.thresholds)
    note = (f"f1={f1:.2f} isolated; expected coupling {exp_c:.3f}; surviving (not-ruled-out) "
            f"{surviving:.2f}; CREDITED {credited:.2f}. Surviving ≠ credited — crediting needs an "
            f"identity witness (characterization is the decisive next step); the rest are ruled "
            f"out as isolated/small.")
    return SampleRecord(element.symbol, spin_label, f1, exp_c, surviving, credited,
                        tuple(verdicts), note)
