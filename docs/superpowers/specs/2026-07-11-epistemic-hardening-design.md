# Design — Epistemic hardening: phase-identity gate + uncertainty propagation

**Date:** 2026-07-11 · **Status:** approved for implementation planning (operator scientific
review, priorities #2 and #3). Priority #1 (gap-relation correction) shipped in PR #10 (docs).
Two features, implemented as two PRs; this spec covers both.

## Purpose

Two independent hardenings of the lab's epistemic honesty, both from the operator's review:

- **Feature A — `G_identity` gate.** No candidate may be credited as a superconductivity lead
  until phase identity is established. In a lab with no real specimens the gate **default-blocks**
  and is discharged only by an *injected* characterization witness — mirroring the existing
  `.cube` bridge (inject real data, else stay honest about the limit).
- **Feature B — uncertainty propagation + rank stability.** Replace single deterministic scores
  with distributions: seeded Monte-Carlo over the tunable thresholds (with an analytic interval
  cross-check), reported as `score ± interval` plus rank-stability, so a poorly-constrained input
  cannot masquerade as precision.

Both preserve the charter invariants: deterministic (seeded RNG only), evidence clamped ≤ 2, no
network, no fabricated data.

---

## Feature A — `G_identity` gate

### Semantics

```
G_identity = G_composition ∧ G_phase ∧ G_morphology ∧ G_oxidation
```

A candidate cannot enter the superconductivity **crediting** path until all four sub-gates are
witnessed. Because the pure-simulation lab has no characterization data, `G_identity` is
**unestablished by default** → a candidate is routed to "establish phase identity first"
regardless of how well the SC proxies score. This is the honest stance: *the lab cannot claim
superconductivity of the metal until something proves the specimen IS the metal.*

### `src/orme_lab/identity.py` (new)

```python
class IdentityVerdict(str, Enum):
    ESTABLISHED = "established"       # all four sub-gates witnessed as the target metal
    UNESTABLISHED = "unestablished"  # default: no witness -> blocked, route to characterization
    CONTRADICTED = "contradicted"    # a witness says it is NOT the target metal (oxide/salt/...) -> hard fail

@dataclass(frozen=True)
class IdentityWitness:
    # each field: the witnessed value + the instrument that established it (provenance).
    composition: str | None       # e.g. "Ir" (target metal) | "IrO2" | "IrCl3" | None
    phase: str | None             # "metallic" | "oxide" | "hydroxide" | "salt" | "complex" | None
    morphology: str | None        # "monatomic" | "sub-nm-cluster" | "nanoparticle" | "bulk" | None
    oxidation_state: float | None # 0 for metal; >0 implies a compound
    instruments: tuple[str, ...]  # e.g. ("XRD","XPS","ICP-MS","EXAFS") — the witnessing methods

@dataclass(frozen=True)
class IdentityResult:
    verdict: IdentityVerdict
    established: bool
    missing: tuple[str, ...]       # which sub-gates lack a witness
    note: str

def evaluate_identity(target_metal: str, witness: IdentityWitness | None) -> IdentityResult
```

Logic: `witness is None` → `UNESTABLISHED`, `missing = (composition, phase, morphology, oxidation)`.
A witness whose composition/phase/oxidation indicates a non-metal (compound, oxidation > 0, phase
≠ metallic) → `CONTRADICTED` (route away from SC entirely — it's a different material). All four
sub-gates witnessed as the target metal (composition == target, phase metallic, oxidation ≈ 0,
morphology present, with ≥1 instrument) → `ESTABLISHED`.

### Pipeline integration (`pipeline.evaluate_candidate`)

Add parameter `identity: IdentityWitness | None = None`. Compute `IdentityResult`. Add
`CandidateRecord` fields: `identity_verdict: str`, `identity_established: bool`, and a top-level
**`credited_sc_lead: bool`** = `identity_established and (not ruled_out) and sc_plausibility > 0`.
By default (no witness) `credited_sc_lead` is **always False** — the honest outcome. The SC
proxy scores are still computed and reported (nothing is hidden); what changes is that *crediting*
now requires identity. Routing: when identity is unestablished, `predict_observables` prepends the
decisive next step — **"establish phase identity (XRD/XPS/ICP-MS/EXAFS)"** — ahead of the Meissner
measurement, because characterization is upstream.

`G_identity` is an **off-gate** input (it is not re-derivable from the SC AND-gate's five inputs),
so it joins `OFF_GATE_INVARIANTS` in `closure.py` (identity is genuinely independent signal).

### Tests

`test_identity.py`: default (no witness) → UNESTABLISHED, `credited_sc_lead` False even when all
five SC gates pass (construct a passing candidate, assert not credited); a full metallic witness →
ESTABLISHED → credited when proxies pass; an oxide/oxidation>0 witness → CONTRADICTED; the
closure golden test (`test_closure.py`) updated for the new off-gate field; routing prepends
characterization when unestablished.

---

## Feature B — uncertainty propagation + rank stability

### `src/orme_lab/uncertainty.py` (new)

Parameters that carry uncertainty: the `ModelThresholds` decision floors
(`min_coupling_for_bulk`, `min_carrier_proxy`, `min_field_tolerance`, `min_structural_stability`,
`min_observable_signal`, and the anisotropy band + coupling distance scale). Each gets a plausible
range (± a documented fraction of its default, e.g. ±30%, cited as an assumption).

- **Seeded Monte Carlo (primary).** `propagate_mc(candidates_fn, ranges, n=512, seed=0)` — draw N
  seeded samples of the thresholds (stdlib `random.Random(seed)` — deterministic), re-score every
  candidate under each draw, collect the `sc_plausibility` distribution → mean, std, and
  percentiles (p5/p50/p95). Fixed default seed ⇒ byte-reproducible (determinism charter).
- **Rank stability.** Across the N draws, record each candidate's rank; report `rank1_fraction`
  (fraction of draws where it ranks #1) and the rank interval (p5–p95 of its rank). "First in 51%
  of draws" vs "first in 99.9%" become visible.
- **Analytic cross-check.** First-order interval propagation (∂score/∂threshold × Δthreshold,
  summed) on a handful of candidates, asserted consistent with the MC spread — a sanity leg, not
  the primary. Documented as a cross-check.
- **Missing-data penalty.** A candidate whose inputs are unconstrained (e.g. no EPW value, only a
  proxy) gets a widened interval / an explicit penalty term, so under-constrained candidates read
  as *less* precise, not falsely sharp.

Output: `ScoreDistribution(mean, std, p5, p50, p95, rank1_fraction, rank_p5, rank_p95, n, seed)`
per candidate; a `UncertainRanking` aggregating them. Pure/deterministic; no pipeline mutation —
it *wraps* `evaluate_candidate` over threshold draws.

### Tests

`test_uncertainty.py`: MC is reproducible (same seed → identical distribution; different seed →
different draws but stable mean within tolerance); rank-stability correct on a hand-built toy set
(a dominant candidate → rank1_fraction ≈ 1.0; two close candidates → split); analytic interval
brackets the MC p5–p95 on a sample; missing-data widens the interval; determinism (two runs
identical).

## Invariants preserved

Deterministic (seeded RNG, fixed default seed; no `time`/unseeded RNG/order-dependent iteration);
evidence clamped ≤ 2; `credited_sc_lead` gated by identity (which defaults blocked); no network,
no fabricated data; every threshold range carries a documented assumption.

## Open items for the writing-plans step

- Exact threshold ranges (default ±30% unless a field has a tighter justification).
- MC sample count N (default 512) and default seed (0).
- Whether `credited_sc_lead` also requires the Meissner/`meissner_screening` proxy explicitly, or
  inherits it via `sc_plausibility` (default: inherit — the AND-gate already includes it).
