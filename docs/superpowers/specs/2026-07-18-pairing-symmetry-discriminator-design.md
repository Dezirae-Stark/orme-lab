# Design — Pairing-symmetry branching + spin/magnetic drive-channel discriminator

**Date:** 2026-07-18 · **Status:** awaiting operator review
**Origin:** operator spec (remote-control), reconciled against the current code by three
exploration passes. This document records where each requested change actually attaches and
how the spec's premises were corrected to match the code.

## Purpose

Make the superconductivity screen **more discriminating** by encoding the singlet-vs-triplet
antagonism with high spin. Under conventional (singlet) pairing a magnetic moment is a
pair-breaker (Pauli/Chandrasekhar-Clogston limit; Abrikosov-Gor'kov). The only known way high
spin and superconductivity coexist is equal-spin triplet pairing, which makes the **opposite**
field-response prediction. This turns the applied-field response into a discriminating
pairing-symmetry test, and — as a corollary — turns the presence of a spin/magnetic AC-drive
channel into a second discriminator (a spin-carrying triplet condensate can be parametrically
pumped like a magnon BEC; a spin-neutral singlet cannot).

All of this is layered on the **unvalidated** PGM-SAC premise **plus** the added triplet
assumption **plus** (for the drive channel) a magnon-analogue assumption. It is a set of
**hypotheses to test, not mechanism claims**, and is marked as such everywhere it surfaces.

## Honesty invariants preserved (non-negotiable)

Verbatim from the charter and the spec; every task inherits these and no task may weaken them:

- No new verdict members; `VALIDATED`/`CONFIRMED` stays absent from the `Verdict` enum
  (`lab_loop/triage.py`).
- Everything clamped to evidence **Level 2** (`LAB_CEILING`) on the screen path. The
  decisive-measurement *predictions* may carry `LABORATORY_PREDICTION` (Level 3) via the
  already-present `PREDICTION_CEILING`, consistent with the existing prediction path — they are
  predictions, not observations.
- The anti-tautology gate (`lab_loop/closure.py`): a predictor must reference at least one
  `OFF_GATE_INVARIANT` or it is `TAUTOLOGICAL`. The pinned closure set and its golden test
  (`test_closure.py`) remain authoritative.
- Creative-generator / deterministic-judge separation, the closed `Verdict` enum, and
  independent hypothesis retirement are unchanged.
- The change must make the screen **stricter** (able to kill candidates it previously passed),
  never more permissive.

## How the six changes reconcile with the actual code

The exploration corrected several of the spec's structural premises. The corrections:

- **The "current spin-related hypothesis" is H7** — "magnetic fields stabilize / suppress /
  destroy the state depending on phase" (`docs/hypothesis_matrix.md` row H7; encoded in
  `magnetic_field.py`). The dependency chain is `H1 (spin) → … → H7 (field response)`.
- **No singlet field-suppression penalty exists today.** `pipeline.critical_field_proxy`
  (`pipeline.py:69`) is `5.0 * coupling * (0.5 + 0.5*spin)` — spin *raises* Hc **unconditionally**
  (already triplet-like, applied to every candidate). The only singlet pair-breaking is in
  `mechanisms._phonon` (hard reject at `spin_pol ≥ PB_MOMENT_MAX=0.5`, graded `pb` below). So
  Change 2 is not "make an existing singlet penalty conditional" — it is "make the field-axis
  spin-sign pairing-conditional, and de-dup the new singlet penalty against `mechanisms._phonon`."
- **Singlet/triplet already exist as mechanism tracks** (`mechanisms.Mechanism`: `M_phonon`,
  `M_triplet`, `M_spin_fluctuation`, …). Change 1 reuses this, it does not duplicate it.
- **No inter-hypothesis liveness dependency exists.** Change 4 (H16-drive live only if H7-triplet
  alive) is new machinery.
- **`PREDICTION_CEILING = LABORATORY_PREDICTION` (3) already exists** (`evidence.py:54`).
- **Three registry surfaces** (`lab_loop/hypotheses.py`, `web/hypotheses.js`,
  `docs/hypothesis_matrix.md`) plus **two JS EM reimplementations** (`web/metrics.js` labels,
  `web/sim.js` physics) with **no parity test**. Change 6 touches these; we add parity guards.
- **In-code honesty phrasing is "Toy (Level 2)" / "proxy" / "SURROGATE"**, not the literal
  "MODEL PROXY" — Change 6 matches the existing wording.

## Physics reference values (cited, representative)

- **Chandrasekhar-Clogston / Pauli limit:** `Bc_pauli(T) ≈ 1.86 · Tc(K)` tesla (weak-coupling BCS
  estimate; Clogston, *Phys. Rev. Lett.* 9, 266 (1962); Chandrasekhar, *Appl. Phys. Lett.* 1, 7
  (1962)). Used as the reference field; the **ratio** `Bc / Bc_pauli` is the discriminator, not an
  absolute field.
- **Abrikosov-Gor'kov** pair-breaking by magnetic moments (singlet) — already encoded as the
  `mechanisms._phonon` moment penalty; the field-axis penalty is reconciled with it, not stacked.
- **Magnon-BEC parametric pumping** (Demokritov et al., *Nature* 443, 430 (2006)) — the analogy
  motivating the spin/magnetic AC-drive channel; used only as a *hypothesis* framing, not a
  mechanism claim. `Tc` for `Bc_pauli` comes from `sc_tc_kelvin` (EPW path); `None` on the toy
  path, in which case the prediction is surfaced without a number (honest absence).

## Design — module by module

### Change 1 — branch H7 on pairing symmetry (`lab_loop/hypotheses.py`, +web +docs)

Split the registry id `H7` into **`H7-singlet`** and **`H7-triplet`** (mechanically like the
H1/H3 scoped split — separate ids ⇒ independent retirement via `Ledger._killed`). Unlike H1/H3
these are **not** element/geometry-scoped (both apply to the same high-spin candidate); they are
distinguished by **opposite falsification conditions** on the field-response ratio (Change 3), so
they need no `SCOPE_PREDICATES` entry. Update `HYPOTHESES`, add statements to `web/hypotheses.js`
and `docs/hypothesis_matrix.md`. Naming follows the existing `H<n>-<scope>` convention.

### Change 2 — pairing-symmetry-dependent spin sign (`superconductivity.py`, `pipeline.py`, `mechanisms.py`, `magnetic_field.py`)

Introduce a `PairingSymmetry` enum (`SINGLET`, `TRIPLET`) threaded into the field/critical-field
computation. **Spin has exactly one sign per hypothesis:**

- **Under SINGLET:** critical field is Pauli-limited; rising spin *suppresses* the field-tolerance
  margin (pair-breaking). This is the single singlet pair-breaking effect — reconciled with
  `mechanisms._phonon` so the same spin scalar does **not** apply two independent singlet penalties
  to one candidate's score.
- **Under TRIPLET:** high spin is field-robust / enhancing (the current `critical_field_proxy`
  behavior), and incurs **no** singlet suppression.

The coupling/carrier path (`carrier_coherence_proxy`, geometry-only coupling) is unchanged and
pairing-independent. The **double-counting guard** is the acceptance test: within a single
hypothesis evaluation, the spin scalar cannot simultaneously feed a positive coupling/triplet
contribution and a singlet suppression penalty — each hypothesis has a clean, monotonic spin sign.

### Change 3 — Pauli-limit reference + relative field-response scoring (`magnetic_field.py`)

Fill the existing `TODO(physics)` (`magnetic_field.py:20-22`): add
`pauli_limit_tesla(tc_kelvin) → 1.86*tc` and score field response as the ratio
`Bc_candidate / Bc_pauli`, not an absolute scale. Ratio `> 1` (enhancement/robustness beyond
Pauli) → evidence **for** triplet, **against** singlet; ratio `≤ 1` (suppression at/below Pauli) →
evidence **against** triplet. Surface this as a **decisive-measurement prediction** in the
registry / research dossier: *"measure critical field vs the Pauli limit — the ratio discriminates
singlet from triplet."* When `sc_tc_kelvin is None` (toy path) the prediction is stated without a
numeric Bc_pauli.

### Change 4 — spin/magnetic drive-channel hypothesis (`electromagnetic_coherence.py`, `lab_loop/*`, +web)

Add **`H16-drive-triplet`** to the EM-coherence branch (H12/H16), **live only when `H7-triplet` is
alive**:

- **New liveness-dependency machinery.** Add `LIVENESS_DEPENDENCIES: dict[str,str]` in
  `hypotheses.py` (`"H16-drive-triplet" → "H7-triplet"`) + a `validate_liveness(avenue,
  open_hypotheses)` helper. Evaluate it at **run/triage time** (`loop.py` ~:222 and/or `triage.py`),
  **not** at intake — the parent can be killed mid-run; a dependent avenue whose parent is dead is
  judged `INCONCLUSIVE` (no orphaned drive-channel finding).
- **Killable toy drive-response proxy** in `electromagnetic_coherence.py`: a bounded
  `magnetic_drive_response(...)` observable (magnon-BEC-analogue parametric response to an AC
  magnetic drive), labeled a MODEL PROXY, Level 2. Its **falsification condition**: no modeled
  drive response above baseline (or indistinguishable from the singlet/no-drive case) → a reachable
  `KILLED_HYPOTHESIS`.
- **Off-gate:** add the new field (e.g. `em_drive_response`) to the pinned `OFF_GATE_INVARIANTS`
  (`closure.py`) **and update `test_closure.py`** — otherwise the tautology check (first in triage)
  fires before the liveness gate. Provenance text: *"speculation on the PGM-SAC premise + triplet
  assumption + magnon-analogue drive assumption — a hypothesis to test, not a mechanism claim."*

### Change 5 — backend seam: pairing channel AND drive channel as parameters (`backends.py`, `mechanisms.py`)

`mechanisms.py` already treats pairing as a 5-way enum — make the pairing-channel selection explicit
and add a `_drive` track. In `backends.py`, add `Capability` members for (b) a non-phonon
pairing-channel route and (c) a spin/magnetic drive-response route, as **no-number stubs** raising
via the existing `_nyi(...)` / `TODO(backend)` pattern. **Do not** fabricate a triplet Tc or a
backend drive number (the *toy* drive proxy of Change 4 lives in the EM branch, clearly separate
from the ab-initio seam).

### Change 6 — UI honesty labels + parity (`web/metrics.js`, `web/sim.js`, `web/hypotheses.js`, new parity tests)

Label the new magnetic-drive-response output (and re-affirm "carrier proxy" / "resistance regime")
as **"Toy (Level 2)" / proxy**, matching existing wording. Mirror the new hypotheses and the drive
field into `web/hypotheses.js` and `web/sim.js`. **Add Python↔JS parity tests** (following
`test_ledger_parity.py` / `test_research_parity.py`) tying the hypothesis registry and the EM-drive
constants across the three surfaces — closing a pre-existing silent-divergence gap.

## Test contract (acceptance criteria)

1. `H7-singlet` and `H7-triplet` retire independently — killing one leaves the other's standing
   unchanged.
2. `H16-drive-triplet` is live **only** under `H7-triplet` — a test proves it cannot score
   (returns `INCONCLUSIVE`) once `H7-triplet` is killed (no orphaned finding).
3. Spin is **not double-counted** within one hypothesis — a test proves the same spin value cannot
   both raise the coupling/triplet contribution and apply the singlet suppression penalty in one
   hypothesis (clean monotonic sign per hypothesis).
4. Both the **field-response** signal and the **magnetic-drive-response** signal are off-gate — a
   test proves each passes the anti-tautology gate (references an `OFF_GATE_INVARIANT`; changes the
   score in a way not re-derivable from the AND-gate's static inputs).
5. The hypotheses **diverge under the same inputs** — field enhancement scores for triplet / against
   singlet; field suppression scores against triplet; a strong magnetic-drive response scores for
   triplet / against singlet.
6. **Stricter, not more permissive** — a test demonstrates at least one candidate whose standing
   *worsens* under the branched logic, and at least one `H16-drive-triplet` `KILLED_HYPOTHESIS`
   outcome.
7. `VALIDATED` absent; every screen verdict clamped ≤ Level 2; `test_closure.py` golden test still
   passes with the extended off-gate set.
8. Python↔JS parity tests pass for the new hypotheses and the drive field.

## Non-goals (YAGNI)

- No real triplet Tc, no real ab-initio drive-response number (backend stays a stub).
- No new EPW/DFT compute; the drive response is a bounded toy proxy.
- No change to the coupling/carrier geometry path beyond threading the pairing parameter.
- No weakening of any existing gate, verdict, or clamp.

## Changelog note (to accompany the merge)

- **Added:** pairing-symmetry branch of H7 (singlet vs equal-spin triplet) with a Pauli-limit
  field-response discriminator, and an H7-triplet-gated spin/magnetic AC-drive-channel hypothesis in
  the EM-coherence branch.
- **Why:** high spin is a singlet pair-breaker but triplet-compatible, so the critical-field-vs-Pauli
  ratio and the magnetic-drive-response-vs-baseline are two decisive discriminators the screen
  previously could not apply.
- **Invariant confirmation:** no verdict member added, everything clamped to Level 2, anti-tautology
  gate extended (not weakened), independent retirement preserved — the screen is strictly more able
  to kill candidates, never more permissive.

## Open items for the writing-plans step

- Exact functional form of the singlet Pauli suppression on the field-tolerance margin, and the
  precise reconciliation arithmetic with `mechanisms._phonon` (so the double-counting test passes).
- The toy `magnetic_drive_response` functional form and its baseline/falsification threshold.
- Whether the liveness gate lives in `loop.py` (run-time skip → `INCONCLUSIVE`) or `triage.py`
  (judge-time) — default: `triage.py`, so a run still produces an honest `INCONCLUSIVE` record.
