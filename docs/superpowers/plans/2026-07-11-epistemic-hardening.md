# Epistemic Hardening — Implementation Plan

Spec: `docs/superpowers/specs/2026-07-11-epistemic-hardening-design.md`. Two PRs.

**Constraints:** deterministic (seeded RNG, fixed default seed; no time/unseeded RNG/order-dependent iteration); evidence ≤ 2; every threshold range carries a documented assumption; commit as Dezirae.

## PR A — `G_identity` gate (branch `identity-gate`)

### A1 — `src/orme_lab/identity.py`
`IdentityVerdict(Enum)` = ESTABLISHED/UNESTABLISHED/CONTRADICTED. `IdentityWitness` frozen dataclass (composition, phase, morphology, oxidation_state, instruments). `IdentityResult` (verdict, established, missing, note). `evaluate_identity(target_metal, witness)`:
- `witness is None` → UNESTABLISHED, missing = all four.
- witness present but composition != target_metal, OR phase not in {"metallic", None-if-witnessed}, OR oxidation_state not ~0 → CONTRADICTED (it's a different material).
- composition == target_metal AND phase == "metallic" AND oxidation_state ≈ 0 AND morphology present AND len(instruments) ≥ 1 → ESTABLISHED; else UNESTABLISHED with the missing sub-gates.
TDD: `tests/test_identity.py` — None→UNESTABLISHED; full metallic→ESTABLISHED; oxide/oxidation>0→CONTRADICTED; partial witness→UNESTABLISHED w/ missing.

### A2 — pipeline + closure integration
`evaluate_candidate(..., identity=None)`. Compute `IdentityResult`. Add `CandidateRecord` fields `identity_verdict: str`, `identity_established: bool`, `credited_sc_lead: bool` (= identity_established AND not ruled_out AND sc_plausibility > 0). Add identity fields to `OFF_GATE_INVARIANTS` in `closure.py` and fix the `test_closure.py` golden. Routing: `predict_observables` (or the pipeline) prepends "establish phase identity (XRD/XPS/ICP-MS/EXAFS)" when not established. TDD: a candidate that passes all 5 SC gates but has no witness → `credited_sc_lead` False; with a metallic witness → True; contradicted witness → credited False + verdict CONTRADICTED. Full suite green (closure golden updated).

### A3 — verify + PR (docs-only validation_tests.md gate note already in PR #10; here update the in-doc "not yet code-enforced" line if PR #10 merged, else leave). PR, no merge.

## PR B — uncertainty propagation (branch `uncertainty-propagation`, after A)

### B1 — `src/orme_lab/uncertainty.py`
`THRESHOLD_RANGES` (± documented fraction, default ±30%, per ModelThresholds floor). `propagate_mc(base_candidates, ranges, n=512, seed=0)` — `random.Random(seed)`; N draws of perturbed thresholds; re-score; collect `sc_plausibility` per candidate → `ScoreDistribution(mean,std,p5,p50,p95,rank1_fraction,rank_p5,rank_p95,n,seed)`. `rank_stability` across draws. `analytic_interval(candidate, ranges)` first-order cross-check. `missing_data_penalty` widens interval for under-constrained candidates. TDD: `tests/test_uncertainty.py` — reproducible (same seed identical); dominant candidate rank1≈1.0; two close → split; analytic brackets MC p5–p95; missing-data widens; determinism (two runs identical).

### B2 — verify + PR.
