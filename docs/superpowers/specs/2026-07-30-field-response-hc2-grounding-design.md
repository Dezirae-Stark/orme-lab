# Design — Ground the field-response discriminator in heavy-fermion Hc2 / Pauli-limit methodology

**Date:** 2026-07-30 · **Status:** awaiting operator review
**Precondition:** MET — the singlet/triplet pairing branch (`H7-singlet`/`H7-triplet`) and the
field-response discriminator (`pauli_limit_tesla`, `field_response_ratio`, `pairing_critical_field`
in `magnetic_field.py`) already exist on master (`b5a4bbe`). This ENRICHES that discriminator; it
adds NO new hypothesis.

## Citation gate — PASSED (all six verified; two corrections)

All six operator-supplied references were audited against CrossRef DOI metadata + direct
abstract/preprint fetches (record: `~/.claude/research-wiki/prior-art/heavy-fermion-hc2-pauli-limit.md`).
No fabrications, no misattributions. Two corrections folded in below:

- **CeSiI — Shi, Cheng et al., *Nature Physics* (2026), DOI 10.1038/s41567-026-03392-3** — REAL
  (published 2026-07-28, 13 authors incl. Tong Shi … Jinguang Cheng). Bc₂ = 4–7× Pauli limit, NFL
  transport, effective-mass divergence, Tc ≈ 240 mK all confirmed. **Correction:** pressure is
  **6 GPa (SC dome max) / 7 GPa (QCP)** — NOT "7.5–8 GPa" as drafted. Template case.
- **CeSb₂ — Squire et al., *PRL* 131, 026001 (2023)** — VERIFIED ("Pauli limit exceeded ~8×").
- **CeCoIn₅ FFLO — Miclea et al., *PRL* 96, 117001 (2006)** — VERIFIED (generic FFLO citation; note
  the *original* discovery is Radovan/Bianchi 2003 — Miclea is fine for pressure-dependent FFLO).
- **CeRh₂As₂ — Khim et al., *Science* 373, 1012 (2021), DOI 10.1126/science.abe7518** — VERIFIED.
- **LiFeAs — Khim et al., *PRB* 84, 104502 (2011)** — VERIFIED (clean, Pauli-limited benchmark).
- **Schossmann & Carbotte, *PRB* 39, 4210 (1989)** — VERIFIED as general Pauli-limiting Hc2 theory.
  **Correction:** the specific `1.86·Tc` coefficient originates in **Clogston, *PRL* 9, 266 (1962)**
  / **Chandrasekhar, *APL* 1, 7 (1962)** — cite those for the coefficient; Schossmann-Carbotte is
  the strong-coupling/impurity generalization.
- **Formulas:** `Bp ≈ 1.86·Tc` (Clogston-Chandrasekhar) and `α = √2·Borb/Bp` with FFLO admissible
  only in the clean limit and `α ≳ 1.8` — confirmed standard.

## Honesty invariants (non-negotiable)

- No `VALIDATED` verdict member. **A grounded threshold sharpens the model proxy; it does NOT raise
  the evidence level — everything stays Level 2.**
- Anti-tautology gate preserved: the field-response signal (`field_response_ratio`/R_Pauli) stays
  off-gate; no gate-input closure change.
- Creative-generator / deterministic-judge separation; the change makes the discriminator MORE
  precise and MORE able to kill, never more permissive.
- **The reference table adds NO score to any PGM candidate** — calibration/anchor only.
- **R_Pauli > 1 is *consistent-with* triplet, not *proof*** — one necessary signature inside the
  AND-gate, never a positive standalone score.
- Heavy-fermion physics is methodology/template grounding, NEVER evidence for the PGM-SAC premise
  (Ce 4f, millikelvin, GPa — a different material class).

## Design — change by change

### Change 1 — R_Pauli, Maki parameter, clean-limit gate (`magnetic_field.py`)

Enrich the existing field-response functions (do not duplicate):
- `pauli_limit_tesla(tc)` unchanged (`1.86·Tc`); update its comment to credit Clogston 1962 /
  Chandrasekhar 1962 for the coefficient (Schossmann-Carbotte for the general theory).
- Add `pauli_violation_ratio(hc2_0_t, tc_kelvin) -> float | None` = `Hc2(0) / Bp` — **R_Pauli**, the
  core scored quantity. `None` when Tc unknown (toy path). This is the physically-named refinement
  of the existing `field_response_ratio` (which is retained as-is / aliased so the pairing-branch
  wiring is untouched); R_Pauli ≤ 1 → singlet/Pauli-limited; > 1 → unconventional signature.
- Add `maki_alpha(b_orb_t, bp_t) -> float | None` = `√2 · Borb / Bp`.
- Add `clean_limit_admits_unconventional(maki_alpha, is_clean) -> bool` = `maki_alpha is not None and
  maki_alpha >= MAKI_FFLO_MIN (1.8) and is_clean is True`. An unconventional/FFLO signature is
  **admissible only** when this returns True. `MAKI_FFLO_MIN = 1.8` (documented constant).
All are labeled model proxies computed from candidate parameters.

### Change 2 — Borb / clean-limit as optional candidate inputs (the one design fork, approved)

Borb (orbital critical field) and the clean/dirty limit (mean-free-path vs coherence length) are not
in the toy model. Add them as **optional inputs** (`CandidateRecord.b_orb_tesla: float | None`,
`is_clean_limit: bool | None`, defaulting `None`), settable via `LabConfig`/a backend seam later.
**When absent (default toy path), the clean-limit gate cannot confirm, so the unconventional
signature is NOT registered regardless of R_Pauli** — conservative, and it directly satisfies the
acceptance test "a dirty-limit (or unknown) candidate cannot register an unconventional signature."
No fabricated Borb. The discriminator instead emits the decisive-measurement spec (Change 3).

### Change 3 — decisive-measurement block for the Registry (Level-3 handoff)

For any candidate the discriminator flags as possibly-unconventional (R_Pauli trending > 1 under the
model), emit a structured decisive-measurement block (a small dataclass / dict serialized into the
registry) naming the real experiment, modeled on CeSiI:
- Measure angle- and T-resolved Hc2 → compute `R_Pauli = Hc2(0)/Bp`.
- Corroborating off-gate companions from the heavy-fermion literature: NFL resistivity exponent
  (`ρ = ρ0 + A·T^n`, `n < 2`) and effective-mass enhancement near the magnetic instability.
- Explicit falsification: `R_Pauli ≤ 1` with Pauli-limited suppression ⇒ **against** equal-spin
  triplet (and against high-spin-compatible SC); `R_Pauli > 1` in the clean limit ⇒ **consistent
  with** unconventional/triplet.
Carries the `PREDICTION_CEILING` (Level 3) tag as a *prediction* (not an observation), tied to the
SAC-stack "Method 5 (Hc2-vs-Pauli-limit)" decisive measurement.

### Change 4 — CeSiI reference table + Ledger entry (grounding, honestly scoped)

- **`field_response_refs`** (a cited data module, e.g. `src/orme_lab/field_response_refs.py`): a
  frozen tuple of benchmark rows — `material`, `r_pauli` (or Hc2-vs-Bp behavior), `clean` (bool),
  `pairing_class` ("unconventional"/"Pauli-limited"), `citation`. The six verified benchmarks, CeSiI
  as template (R_Pauli ≈ 4–7, clean, unconventional). Used ONLY to (a) document the R_Pauli=1 boundary
  and (b) drive a calibration test asserting the discriminator classifies each benchmark correctly.
  Never contributes a score to a PGM candidate.
- **Ledger entry** for CeSiI: a real, rigorous "superconductivity emerges when magnetic order is
  suppressed at a pressure-tuned QCP" instance (Baskaran "latent SC deconfined by perturbation"
  cross-reference), with explicit honest scoping recorded verbatim: *Ce 4f heavy-fermion, ~240 mK,
  6–7 GPa — NOT a PGM single-atom system, NOT room temperature, NOT evidence for the ORME premise;
  methodology/conceptual-template reference only.*

### Change 5 — guardrails (enforced by test)

No new hypothesis; no positive score term (heavy-fermion refs never add to a PGM score); no evidence
level raised (grounded thresholds stay Level 2); `R_Pauli > 1` treated as consistent-with (necessary,
not sufficient) inside the AND-gate — never standalone proof of triplet.

## Test contract (acceptance)

1. `pauli_violation_ratio` and `maki_alpha` computed correctly; a candidate with R_Pauli ≤ 1 scores
   toward singlet/against triplet, R_Pauli > 1 in the clean limit toward unconventional — matching
   the reference-table calibration.
2. The clean-limit gate actually gates: a dirty-limit (or `is_clean=None`) candidate cannot register
   an unconventional/FFLO signature regardless of R_Pauli.
3. The discriminator can WORSEN standing: a candidate under Pauli-limited suppression (R_Pauli ≤ 1)
   scores against triplet (previously-passable now fails on the field axis).
4. Field-response stays off-gate (anti-tautology passes); the decisive-measurement block is emitted
   for flagged candidates and carries the falsification condition + companions.
5. No `VALIDATED`; everything Level 2; the CeSiI Ledger entry carries the not-PGM / cryogenic /
   not-evidence scoping text.
6. The reference table is used only for threshold calibration; a golden test asserts it never adds a
   direct score to any PGM candidate (guards Change 5), and that each benchmark row classifies on the
   correct side of R_Pauli=1.

## Non-goals

- No new hypothesis, no positive scoring term, no evidence-level raise.
- No fabricated Borb / clean-limit values (absent → conservative non-registration + measurement spec).
- No treating heavy-fermion unconventional pairing as support for PGM-SAC.

## Changelog note

- Grounded the field-response discriminator in the heavy-fermion Hc2/Pauli-limit methodology:
  R_Pauli = Hc2(0)/Bp, Maki α = √2·Borb/Bp, clean-limit admissibility gate; a cited benchmark table
  (CeSiI template, all six verified) calibrating the R_Pauli=1 boundary; a Level-3 decisive-
  measurement handoff (SAC Method 5); CeSiI logged as a methodology/template with explicit
  not-PGM/not-evidence scoping. No invariant weakened, no evidence level raised (Level 2), no new
  hypothesis, no positive score term. Citations verified (CeSiI 6/7 GPa correction; 1.86 coefficient
  attributed to Clogston/Chandrasekhar 1962).

## Open items for the writing-plans step

- Whether `field_response_ratio` is aliased to `pauli_violation_ratio` or kept separate (default:
  keep `field_response_ratio` untouched for the pairing-branch wiring; add `pauli_violation_ratio`
  as the physically-named entry point that the enriched path uses).
- The exact benchmark `r_pauli` values / ranges to encode per row (from the audit: CeSiI 4–7,
  CeSb₂ ~8, CeCoIn₅ FFLO clean α~5, CeRh₂As₂, LiFeAs ≤1) with per-row citations.
- The decisive-measurement block's storage/serialization shape in the registry.

## Result (Task 5 — acceptance contract, 2026-07-30)

All 8 test-contract acceptance criteria (`tests/test_field_response_grounding_acceptance.py`) pass
against the implementation landed in Tasks 1-4 on this branch (`magnetic_field.py`, `config.py` +
`pipeline.py`, `field_response_refs.py`, `validator.py` + `web/hypotheses.js`):

1. `pauli_violation_ratio` reproduces the R_Pauli=1 boundary direction (`<=1` singlet-side, `>1`
   unconventional-side), and every cited `BENCHMARKS` row classifies correctly against it
   (`test_1_r_pauli_boundary_matches_benchmark_table`).
2. The clean-limit gate actually gates: a dirty-limit candidate with a huge `b_orb_tesla` cannot
   register `unconventional_admissible`, and neither can a clean-limit candidate with an unknown
   Maki α (no `b_orb_tesla`) — both conservative, non-registered
   (`test_2_clean_limit_gate_actually_gates`).
3. The discriminator can WORSEN standing on a real triage run: a Pauli-limited measurement
   (`max_field_response_ratio=0.6 <= 1.0`) kills `H7-triplet` outright
   (`test_3_pauli_limited_ratio_can_worsen_standing_against_triplet`).
4. `field_response_ratio` still passes `closure.is_independent` — off-gate, unweakened
   (`test_4_field_response_stays_off_gate`).
5. `validator._mech_test(Mechanism.TRIPLET)` names R_Pauli, the explicit against/consistent-with
   falsification, and both quantum-critical companions (NFL exponent, effective-mass enhancement),
   at `evidence_level == 3` (a prediction, not an observation)
   (`test_5_decisive_measurement_block_names_falsification_and_companions`).
6. No `Verdict.VALIDATED` member exists; `evaluate_candidate` stays `evidence_level <= 2` under all
   three pairing-symmetry branches; `CESII_ANCHOR.scoping`/`conditions` carry the not-PGM/~240 mK/
   GPa scoping text verbatim (`test_6_no_validated_level_2_everywhere_cesii_scoped`).
7. `field_response_refs` exposes no `score_candidate` and no callable in the module mentions
   `CandidateRecord` in its docstring — the reference table cannot score a PGM candidate
   (`test_7_refs_module_never_scores_a_pgm_candidate`).
8. Default `LabConfig` (no `b_orb_tesla`/`is_clean_limit`) round-trips through `evaluate_candidate`
   byte-identical on the three new fields: both `None`, `unconventional_admissible is False`
   (`test_8_default_path_byte_identical`).

Full suite green (`python3 -m pytest -q`). No evidence-level change (Level 2 everywhere); anti-
tautology gate unweakened; no new hypothesis; no positive score term; no fabricated citation
(Baskaran recorded as conceptual framing only, per the citation gate above).
