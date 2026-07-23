# Design — Computed orbital-order descriptor (QE projwfc) + pairing off-gate discriminator

**Date:** 2026-07-23 · **Status:** awaiting operator review
**Origin:** operator remote-control spec (descriptor upgrade), reconciled against the code by two
exploration passes and a prior-art search. Records where the spec's premises were corrected to
match the code and the literature.

## Precondition (the spec's hard gate) — MET

The spec forbids building an orbital-order parameter on the toy model; it must derive from real
DFT orbital-resolved output, else ship inert behind `TODO(backend)`. **This session QE 7.3.1 with
`pw.x` and `projwfc.x` (Löwdin population analysis) plus Ir/Os/Pt ONCV pseudopotentials is live**
(`/opt/qe/q-e-qe-7.3.1/bin`, `/opt/orme-epw/pseudo`), so the computed path is real and will be
validated end-to-end against an actual QE run (Ir). The changelog will confirm the precondition was
met (not shipped inert).

## Honesty invariants preserved (non-negotiable)

- No `VALIDATED`/`CONFIRMED` verdict member. The `Verdict` enum is unchanged.
- **Upgrading a descriptor's physical definition does NOT raise the evidence level.** A computed
  orbital-order parameter is still **Level 2** (`LAB_CEILING`). Everything stays clamped.
- Anti-tautology gate authoritative: an off-gate predictor must reference ≥1 `OFF_GATE_INVARIANT`
  and must not be re-derivable from the AND-gate's static scalar inputs. New off-gate fields are
  ADDED to the pinned set and the golden `tests/lab_loop/test_closure.py` updated in lockstep.
- Creative-generator / deterministic-judge separation; the change makes the screen **more**
  discriminating (able to kill), never more permissive.
- Default path byte-identical: gated behind `LabConfig.compute_orbital_order` (default **off**) and
  `backend.provides(...) AND available()`; with the flag off / backend absent, every existing
  `CandidateRecord` field and metric is unchanged.

## Prior-art grounding (all direct-read unless noted; full record in
`~/.claude/research-wiki/prior-art/orbital-order-parameter.md`)

- **Orbital-order parameter = occupation imbalance.** Tokura & Nagaosa, *Science* 288, 462 (2000):
  pseudospin `T^z = ±½` for which orbital is occupied. Fernandes & Chubukov (arXiv:1607.00865):
  Pomeranchuk bilinear `⟨d†_μ d_ν⟩`, B1g ferro-orbital `= Δ_xz,xz − Δ_yz,yz`. Fernandes, Chubukov &
  Schmalian, *Nature Physics* 10, 97 (2014): `n_xz − n_yz`. → an occupation-difference construction.
- **projwfc.x** (QE PP User's Guide §4.4, direct-read): Löwdin population analysis, per-atom,
  (l,m)-resolved occupations + PDOS. An occupation imbalance is directly constructible.
- **Separability is a real problem; clean DFT separation is UNVERIFIED.** Orbital/magnetic/lattice
  order are symmetry-locked via bilinear Landau couplings (FCS 2014: in strong coupling "who is in
  the driver's seat becomes meaningless"; Tokura-Nagaosa: nonzero orbital order carries the JT
  distortion; corroborated Oleś cond-mat/0303113, Böhmer & Meingast, *C. R. Physique* 17, 90 (2016)).
  **No source supports "static DFT cleanly separates the channels."** Honest framing below.
- **Orbital order ↔ triplet pairing: partially grounded, narrow.** Ramires & Sigrist, *PRB* 94,
  104501 (2016): orbital polarization is generically pair-breaking (Sr₂RuO₄ triplet). Clepkens,
  Lindquist & Kee, *PRR* 3, 013001 (2021) and Zegrodnik/Bünemann/Spałek (arXiv:1305.2806):
  orbital-degeneracy lifting suppresses the Hund's interorbital-triplet mechanism. Supports a narrow
  "high orbital polarization → against the triplet channel"; a general singlet-vs-triplet selection
  rule is **speculative** and labeled so. (Böhmer et al., *Nat. Phys.* 18, 1412 (2022): metadata
  only, paywalled — not cited for content.)

## Architecture

One QE run (`pw.x` SCF → `projwfc.x`) yields Löwdin (l,m)-resolved d-occupations, from which **two
distinct quantities** are computed. The distinctness is what lets the off-gate discriminator pass
the anti-tautology gate even though the gate-facing descriptor is upgraded from the same data.

### Backend host & projwfc stage

Host on **`QuantumEspressoBackend`** (requires only `pw.x`; add `projwfc.x` to `binary_requires`) —
NOT `EPWBackend` (which also requires `ph.x`/`epw.x`, unnecessary here). New pieces mirror the EPW
pattern exactly:

- `epw/qe_input.py`: `projwfc_input(approx, cfg, prefix)` — `&projwfc` namelist, `prefix`,
  `outdir='./'`, `filproj`; reuses `_control`/`_atomic_blocks` idioms. Runs after `pw.x scf`.
- `epw/config.py`: `EPWConfig.projwfc_x: str = "projwfc.x"`.
- Runner stage: after the SCF `_run`, a `_run(cfg.projwfc_x, projwfc_input(...), converge=False)`,
  then read the projwfc **file** (`filproj`/`.projwfc_up`) from the workdir (file-read pattern, like
  `.a2f`; projwfc writes files, not a stdout table).
- `epw/parse_projwfc.py`: `parse_projwfc(text) -> OrbitalOccupations` (per-atom d-orbital occupations).
- `epw/orbital_result.py`: frozen `OrbitalResult` with `source`/`provenance` and
  `toy_absent`/`not_applicable`/`failed` null-object constructors (one candidate's failure never
  raises — same discipline as `EPWResult`).
- `backends.py`: `QuantumEspressoBackend` gains `@implemented(Capability.DENSITY_ANISOTROPY)` (the
  gate-facing seam, already checked in `pipeline.py`) AND a new `Capability.ORBITAL_ORDER` with a
  matching `orbital_order(...)` method; `binary_requires` gains `projwfc.x`. Injectable runner/parser
  for fixture tests.

### Quantity 1 (gate-facing, Change 2) — computed density anisotropy

Occupation-weighted d-orbital **quadrupole** tensor (each d-orbital contributes a known angular
quadrupole; weight by its Löwdin occupation), diagonalized to a fractional-anisotropy scalar in
[0,1] — the same shape the toy `electron_density.ricebean_score` estimates, now from real
occupations. Replaces the toy anisotropy that feeds `carrier_coherence_proxy` → the SC AND-gate,
**only** when `compute_orbital_order` is on and the backend provides it; the toy value is the
explicit fallback. Honestly labeled a **d-manifold approximation to the charge-density shape** (not a
full density cube; s/p and radial contributions omitted). *(A `pp.x` density-cube route was
considered for strict independence and rejected for scope — one live stage over two; revisit if the
d-manifold approximation proves inadequate.)*

### Quantity 2 (off-gate, Change 3) — orbital-order parameter

**Frame-robust d-occupation polarization** `P ∈ [0,1]`: a normalized measure of how far the five
d-orbital occupations depart from equal filling (0 = degenerate/equal, 1 = one orbital dominant),
well-defined for any geometry including a monomer (no crystal-frame assumption). PLUS
**dominant-orbital symmetry metadata** (which d-orbital dominates) recorded as non-scoring
provenance. `P` is a *different* contraction of the occupation vector than the quadrupole-anisotropy
(dispersion vs shape), so two candidates can share the gate `anisotropy` yet differ in `P` — this is
what makes `P` genuinely off-gate (not recoverable from the gate's scalar inputs), pinned by the
anti-tautology test. Exact `P` formula fixed in the plan (with the round-trip test); the design
commitment is: normalized, in [0,1], 0 at equal filling, monotone in occupation imbalance,
deterministic.

### Separability — stated honestly

`P` is computed at **fixed lattice geometry and fixed magnetic configuration** (the SCF deck pins
both), which suppresses cross-channel *feedback* by construction. This is a **computational
restriction, not physical separability** — orbital/magnetic/lattice order are symmetry-locked
(prior-art above). The descriptor therefore does **not** establish that an observed order is
orbital-driven vs lattice/magnetic-driven; that caveat rides `P` everywhere it surfaces, and
strongly-intertwined cases are treated as reduced-confidence, never as clean signal.

## Off-gate discriminator wiring (Change 3)

New nullable `CandidateRecord.orbital_order_param: float | None` and `orbital_order_source: str`
("toy" has no meaning here — the field is `None`/"computed"/"absent"; provenance mirrors `sc_source`).
Wired exactly like `field_response_ratio`:

- Added to `lab_loop/closure.py OFF_GATE_INVARIANTS` (+ golden test). Comment notes it comes from the
  computed orbital-resolved density, not the gate's static properties.
- `avenue.py METRIC_RANGES`: `max_orbital_order: (0.0, 1.0)`; `runner.py` `_METRIC_KEYS` +
  `_NONE_WHEN_UNMEASURED` + `_max_or_none`; `validate_runnable` requires the compute flag (else the
  metric is perpetually unmeasured → the avenue can decide nothing).
- **Discriminator semantics (grounded, narrow):** high `P` → evidence **against `H7-triplet`**
  (Ramires-Sigrist pair-breaking; Clepkens-Kee degeneracy-lifting). An `H7-triplet` falsifier
  `max_orbital_order > θ` (θ fixed in the plan) can fire → worsens/kills triplet standing. Low `P` →
  triplet *not excluded on orbital grounds* (weak reverse; never "supports triplet"). Framed as a
  **hypothesis-linking predictor, not a mechanism claim**, with explicit provenance/uncertainty text
  on the avenue and in the registry/UI.

## Guardrails (Change 4)

- Orbital order is a descriptor upgrade + discriminator, **not a new hypothesis** and **not a
  standalone positive SC/pairing scoring term** on the toy path — enforced by test.
- "Orbital order" (a normal-state ordering) never reads as pairing/superconductivity evidence; the
  only score effect is the *against-triplet* off-gate discriminator.
- No evidence level raised; everything Level 2. No fabricated value when the backend is absent
  (field stays `None`, provenance "absent").

## Test contract (acceptance)

1. Backend absent / flag off → orbital-order descriptor inert, no score change, toy-fallback used
   and flagged; default path byte-identical.
2. Backend present (fixture-emulated projwfc) → computed anisotropy drives the gate descriptor and
   differs from the toy value on ≥1 candidate.
3. `orbital_order_param` passes the anti-tautology gate: two candidates with equal gate `anisotropy`
   (and other gate inputs) but different `P` yield different pairing-branch outcomes — i.e. it moves
   a score in a way not re-derivable from static gate inputs.
4. The descriptor can **worsen** a candidate's standing (an `H7-triplet` avenue killed by high `P`) —
   not uniformly permissive.
5. No `VALIDATED` member; every path Level 2; provenance flags (computed vs toy-fallback vs absent)
   correct on every path.
6. Guardrail: orbital order contributes **no** positive SC/pairing score on the toy path.
7. Golden closure test passes with the extended off-gate set.
8. **Live validation (final task):** a real `pw.x`+`projwfc.x` run on Ir produces Löwdin
   occupations; the parser round-trips and the computed `P` and gate anisotropy are finite and in
   [0,1]. This is the end-to-end proof the precondition is met.

## Non-goals (YAGNI)

- No `pp.x` density cube (the gate anisotropy uses the projwfc d-manifold quadrupole).
- No new hypothesis, no new positive scoring term, no evidence-level change.
- No general singlet-vs-triplet selection rule (unverified); only the grounded against-triplet link.
- No change to the pairing-symmetry field discriminator (PR #25) beyond adding `P` as a second
  off-gate signal.

## Changelog note (to accompany the merge)

- **Precondition:** MET — QE `projwfc.x` live; computed path validated end-to-end on Ir (not shipped
  inert).
- **Upgraded:** toy density-anisotropy → computed d-manifold anisotropy (gate-facing) + a new
  off-gate orbital-order parameter (d-occupation polarization) as a grounded against-triplet pairing
  discriminator.
- **Invariant confirmation:** no verdict member added, evidence level unchanged (still Level 2),
  anti-tautology gate extended not weakened, no positive scoring term added, honest separability
  framing (computational isolation, not physical separability) — the screen is more discriminating,
  never more permissive.

## Result (Task 9 — live validation, 2026-07-23)

Precondition MET. `pw.x` + `projwfc.x` (QE 7.3.1) ran live on the Ir `compact_cluster`
periodic approximant (SG15 ONCV pseudo, `n_semicore_bands=4`, same recipe as
`docs/epw-ir-lambda-run.md`): SCF converged in 11 iterations (`total energy
-230.30536826 Ry`), `projwfc.x` reached `JOB DONE` with spilling parameter 0.0118.
Through `evaluate_candidate(..., compute_orbital_order=True, backend=QuantumEspressoBackend(...))`:
`orbital_order_source == "computed"`, `orbital_order_param (P) = 0.03966`, gate
`anisotropy = 0.0` — both finite, both in `[0,1]`, both cross-checked by hand against
`orbital_order.py`'s pure functions from the real Löwdin d-occupations
`(1.6892, 1.4823, 1.4823, 1.4823, 1.6892)`. The zero anisotropy is a genuine
consequence of the fcc site's cubic point symmetry, not a degenerate/fabricated value.
Full log: `docs/epw-orbital-order-run.md`. All 8 acceptance criteria pass
(`tests/test_orbital_acceptance.py` for 1–7, live run above for 8); full suite green.
No evidence-level change (Level 2); anti-tautology gate extended, not weakened
(golden `tests/lab_loop/test_closure.py` pin includes `orbital_order_param`); default
path (`compute_orbital_order=False`) byte-identical.

## Open items for the writing-plans step

- Exact `P` formula (normalized d-occupation imbalance) + the quadrupole-anisotropy arithmetic, each
  with a hand-worked round-trip test.
- The `H7-triplet` falsification threshold θ on `max_orbital_order`.
- The `projwfc_input` namelist specifics + the `filproj`/`.projwfc_up` parse format (fix against a
  real Ir projwfc output captured in the live task, distilled to `tests/fixtures/sample.projwfc`).
- Per-atom aggregation for multi-atom clusters (average over symmetry-inequivalent metal atoms vs
  max) — default: mean over metal atoms, documented.
