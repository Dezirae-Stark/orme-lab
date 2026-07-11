# Design — Structural distribution: "monatomic" as a measured mixture

**Date:** 2026-07-11 · **Status:** approved (operator review #7). First sub-cycle of the
mechanism-tracks arc (feeds #6). Operator chose "both — expectation + population breakdown."

## Purpose

Replace the categorical monomer/cluster *label* with a measured **structural distribution**:
`f₁` (fraction of isolated PGM sites), `P(n)` (cluster-size distribution), `R_PGM–PGM`
(nearest-neighbour distances). A real sample is a *mixture* — "82% dispersed Pt, 14% dimers,
4% larger" — not one geometry. The screen consumes the distribution two ways: a
**coverage-weighted expected coupling** (aggregate) AND a **per-population verdict breakdown**
(which fraction of the material actually survives the SC gate). This is far more useful than
"monatomic," and it is the structural input the #6 coupling/mechanism models will consume.

## Architecture (additive — does not touch `evaluate_candidate`/`run_screen`)

New `src/orme_lab/structure.py`:

```python
@dataclass(frozen=True)
class Population:
    geometry: ClusterGeometry
    fraction: float                       # 0..1, normalized across the distribution

@dataclass(frozen=True)
class StructuralDistribution:
    populations: tuple[Population, ...]
    def f1(self) -> float                 # Σ fraction where n_atoms == 1 (isolated sites)
    def size_distribution(self) -> dict[int, float]   # P(n): n_atoms -> total fraction
    def nn_distances(self) -> tuple[tuple[float, float], ...]  # (nn_distance, fraction), R_PGM–PGM
    def expected_coupling(self, thresholds) -> float  # Σ fraction · inter_unit_coupling_score(geom)

def make_distribution(pairs: list[tuple[ClusterGeometry, float]]) -> StructuralDistribution
    # normalizes fractions to sum to 1; the existing geometries are the distribution's support.

@dataclass(frozen=True)
class PopulationVerdict:
    geometry: str; n_atoms: int; fraction: float; sc_plausibility: float; ruled_out: bool

@dataclass(frozen=True)
class SampleRecord:
    element: str; spin_label: str
    f1: float
    expected_coupling: float
    surviving_fraction: float             # Σ fraction of populations NOT ruled out
    populations: tuple[PopulationVerdict, ...]
    note: str                             # honest one-line summary

def evaluate_sample(element, distribution, spin_label, state, config=DEFAULT_CONFIG) -> SampleRecord
    # per population: evaluate_candidate -> PopulationVerdict; aggregate expected_coupling,
    # surviving_fraction, f1. Reuses the existing per-candidate scoring, unchanged.
```

**Honest output.** For a mostly-monomer sample (`f₁ = 0.82`), `expected_coupling` is low and
`surviving_fraction` is only the large-cluster tail (e.g. 0.04) — i.e. *96% of the material is
ruled out as isolated/small; only the 4% cluster tail is even a candidate.* That directly
encodes the operator's "vastly more useful than 'monatomic'."

## Determinism / invariants

Deterministic (no time/RNG; `evaluate_candidate` is deterministic; dict/tuple order from the
input population order). Additive — no change to existing pipeline outputs. Evidence discipline
unchanged (per-population records carry the same clamped evidence). The uncertainty layer (#3)
can wrap `expected_coupling` over threshold draws later.

## Testing

`test_structure.py`: `make_distribution` normalizes; `f1`/`size_distribution`/`nn_distances`
correct; `expected_coupling` monomer-only → 0, cluster-only → the cluster's coupling, mixture →
weighted; `evaluate_sample` on a mostly-monomer mixture → `surviving_fraction` = the cluster
fraction (monomers ruled out), per-population breakdown correct; determinism (two runs identical).

## Open items for writing-plans

- Whether `note` names the dominant population or just the fractions (default: fractions + f₁ +
  surviving).
- A convenience `dispersed_sample(element, f1)` factory that builds a plausible mixture from a
  single dispersion fraction (default: yes, for ergonomics — monomer f₁, remainder split
  dimer/cluster).
