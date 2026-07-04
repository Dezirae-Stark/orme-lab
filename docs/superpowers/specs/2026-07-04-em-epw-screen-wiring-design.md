# EM + EPW Screen Wiring — Design Spec

**Date:** 2026-07-04
**Status:** Approved design, pre-plan. Next: `writing-plans`.
**Author:** ORME Lab (operator: Desirae Stark)
**Scope decision:** EM coherence (real) + EPW seam (plumbing) THIS cycle. Coupling-channels
deferred to a separate prior-art cycle (charter forbids inventing channel physics without sources).

---

## 1. Goal and the real unlock

Wire two of the three ab-initio seams into the screen so avenue action flags actually change
the result:

- **`use_em`** → the screen computes electromagnetic (plasmon/polariton) coherence per candidate
  and exposes it as observables.
- **`use_epw`** → the screen routes through `EPWBackend` (injectable runner), honestly labeled
  when binaries are absent.

**The unlock:** electromagnetic coherence is a genuinely *off-gate* signal (the
`electromagnetic_coherence` module is explicit that coherence ≠ superconductivity — that is the
whole H12 point). So wiring EM gives **H12/H16 a real, varying, independent signal** — the first
hypotheses whose lab-loop independence claim stops being formal (unlike the EPW `sc_*` block,
which stays 0 without QE binaries). An avenue targeting H12 can declare
`predictor_invariants=["em_coherence_score"]` and it is both genuinely independent *and* non-zero.

## 2. Scope

**In:** EM coherence computed in the core pipeline (config-gated) with EM observables on
`CandidateRecord`, in `OFF_GATE_INVARIANTS`, and as a lab-loop falsification metric; a groundable
free-electron carrier density; the EPW seam (route `use_epw` → `EPWBackend`, injectable runner,
honest `unavailable` surfacing).

**Out (deferred):** coupling-channel models (nanocluster / granular-Josephson / oxide-salt /
light-matter) — each needs prior-art before any formula. A backend-computed dielectric function
(RPA/TDDFT) — the toy free-electron plasmon stands until then. Producing *validated* EPW numbers —
requires installed, validated QE/EPW binaries (absent here).

## 3. Architecture

Three options were weighed for where EM lives: (1) core pipeline, config-gated; (2) lab_loop-only;
(3) core pipeline, always-on. **Chosen: (1)** — EM is a core physics channel (the web app already
surfaces the concept), belongs in the screen not the loop, and the flag keeps the default toy path
byte-identical in value when off.

Data flow (EM): `run_avenue(use_em)` → `replace(config, compute_em_coherence=True)` →
`pipeline.evaluate_candidate` → `free_electron_density(element)` + already-computed `anisotropy` →
`evaluate_em_coherence(...)` → `em_*` fields on `CandidateRecord` → runner reduces to
`max_em_coherence_score` metric.

Data flow (EPW): `run_avenue(use_epw, epw_backend)` → `run_screen(backend=epw_backend)` →
`pipeline` SC_GAP block (`provides ∧ available`) → `EPWResult` → existing `sc_*` fields; runner
sets `AvenueResult.epw_status`.

## 4. EM half (real, grounded)

### 4.1 Carrier density (the one modeling gap), sourced honestly

New `free_electron_density(element) -> float` (home: `electromagnetic_coherence.py` or
`electron_density.py`):

```
n = conduction_electrons / V_atom
conduction_electrons = element.s_electrons          # free-electron-model carriers
V_atom = (4/3) * pi * (element.covalent_radius_ang * 1e-10)**3   # m^3
```

Textbook metal plasmon density. Au (s=1, r=1.36 Å) → n ≈ 9.5e28 /m³ → plasmon ≈ 9 eV (matches
real Au). **Honest limitation, documented in-code:** d-band metals with `s_electrons == 0` (Pd,
`[Kr]4d10`) → n = 0 → EM channel dark, because the free-electron model genuinely does not apply.
All screened PGMs except Pd have s ≥ 1, so EM is broadly active. Flagged toy, like every other
model here; no fabricated physics.

### 4.2 Pipeline integration

- New frozen `LabConfig` field `compute_em_coherence: bool = False`.
- When true, `evaluate_candidate` computes `free_electron_density(element)`, passes it and the
  existing `anisotropy` to `evaluate_em_coherence(n, anisotropy, thresholds)` (anisotropy drives
  the longitudinal/transverse plasmon split — ties H14/H20 rice-bean to a real optical observable).
- If a backend `provides(DIELECTRIC_FUNCTION)`, use `backend.plasmon_energy(n)` for the plasmon
  energy instead of the toy estimate (existing `provides()` pattern); else toy.

### 4.3 New `CandidateRecord` fields (all `None` when EM not computed)

`em_coherence_score: float | None`, `em_regime: str | None`,
`em_rabi_ev: float | None`, `em_lifetime_fs: float | None`.

### 4.4 Closure + loop metric

- Add the four `em_*` names to `OFF_GATE_INVARIANTS` (independent signal); update the pinned
  closure golden test; confirm still disjoint from `GATE_INPUT_CLOSURE`.
- `runner._metrics` adds `max_em_coherence_score` (max over records, None→skip, empty→0.0);
  `METRIC_RANGES` adds `"max_em_coherence_score": (0.0, 1.0)`.
- `run_avenue` threads `avenue.action.use_em → replace(config, compute_em_coherence=True)`.

## 5. EPW seam half (plumbing + honesty, no new physics)

- New optional `epw_backend` param on `run_avenue` (and threaded through `run_loop`). When
  `avenue.action.use_epw` is true and `epw_backend` is supplied, it is passed to
  `screen_fn(backend=epw_backend)` for that avenue only.
- The backend is `EPWBackend(config, runner)` with the runner **injectable**. Tests supply a
  `FakeEPWRunner` returning a synthetic `.a2f` that flows through the real `spectral→allen_dynes`
  path and yields genuine `sc_lambda`/`sc_tc_kelvin` — proving the plumbing end-to-end without
  binaries. **The mock lives under `tests/`, never shipped as production.**
- **Honest surfacing.** `AvenueResult` gains `epw_status: str ∈ {"not_requested","ran","unavailable"}`.
  `run_avenue` sets it: no `use_epw` → `not_requested`; a record has `sc_source` starting `"epw"`
  → `ran`; `use_epw` set but no `epw` source produced (binaries absent / `available()` False) →
  `unavailable`. The digest gets a dedicated line — "EPW requested but binaries unavailable — sc_*
  not computed" — so a run never implies EPW produced values it did not.

## 6. Schema / determinism impact (stated, not hidden)

`CandidateRecord` gains `em_*` fields (None default) — the CSV schema widens. The "backend=None →
byte-identical output" guarantee holds for *values* (EM off by default; EM computation is pure, no
RNG), but the column set grows. Update the determinism docstring and any CSV-column-exact tests to
the wider-but-still-deterministic schema.

## 7. Honesty guards (load-bearing)

- EM coherence is the H12 *mundane alternative*, explicitly **not** superconductivity. The module
  already frames this; the digest and metric labels must keep `em_coherence_score` read as
  coherence, never as SC evidence.
- EPW `unavailable` surfaced honestly; the mock is test-only; no mock numbers on any production
  path.
- `number_density` is a flagged toy free-electron estimate with the Pd-dark caveat in-code.
- Evidence ceiling unchanged (`LAB_CEILING = 2`); EM/EPW results still clamped.
- Coupling-channels explicitly out of scope; no channel physics invented this cycle.

## 8. Test strategy (TDD)

1. `free_electron_density(Au)` in metal range; `Pd` (s=0) → 0.0 (dark caveat as behavior).
2. `evaluate_candidate` with `compute_em_coherence=True` populates `em_*`; default False → all None.
3. EM values deterministic across two identical runs.
4. Closure golden test: the four `em_*` names in `OFF_GATE_INVARIANTS`, disjoint from gate closure.
5. `max_em_coherence_score` present in metrics and in `METRIC_RANGES`; `run_avenue(use_em=True)`
   yields a non-None, varying value (Au active, Pd 0.0).
6. Keystone: an H12 avenue with `predictor_invariants=["em_coherence_score"]` is judged
   non-tautological AND a falsification on `max_em_coherence_score` fires on a Pd-only (dark) panel
   and survives on an Au/Ag panel — a genuine, independent kill/survive.
7. EPW: `FakeEPWRunner` → `run_avenue(use_epw=True, epw_backend=...)` → `sc_source="epw"`,
   `epw_status="ran"`, real `sc_lambda`.
8. EPW unavailable: no-binaries backend → `epw_status="unavailable"`, digest line present, `sc_*`
   None.
9. `use_epw=False` → `epw_status="not_requested"`.
10. Full existing suite stays green (schema-widening test updates included).

## 9. Open questions for the plan

- Exact home of `free_electron_density` (`electromagnetic_coherence.py` vs `electron_density.py`).
- Whether `em_regime` (a string) needs a companion numeric loop metric or the score suffices.
- Whether to also thread `epw_backend` construction into the CLI (`__main__`) or keep it
  loop-API-only for v1.
