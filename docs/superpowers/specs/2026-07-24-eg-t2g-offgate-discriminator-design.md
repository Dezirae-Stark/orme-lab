# Design — eg–t2g imbalance as a speculative off-gate against-triplet discriminator

**Date:** 2026-07-24 · **Status:** awaiting operator review
**Builds on:** the unmerged PR #27 (`orbital-order-followups`). Keeps #27's runner dedup and its
full-quadrupole-tensor gate fix; **changes eg–t2g's role from gate-internal to off-gate.**
**Reversion point:** PR #27's exact prior state (eg–t2g IN the gate) is frozen at branch
`orbital-order-followups-frozen` and tag `pr27-eg-t2g-in-gate` (`c673443`) on origin — the
operator asked to keep a recoverable copy in case this speculative line proves non-useful.

## Why this is delicate (read first)

A prior-art search (recorded in `~/.claude/research-wiki/prior-art/orbital-order-parameter.md`,
"eg-t2g split vs pairing (2026-07-24)") returned **SPECULATIVE-NOT-FOUND**: no directly-read source
states that an eg–t2g occupation imbalance favors or disfavors triplet/odd-parity Cooper pairing.
The grounded triplet mechanism (Clepkens/Lindquist/Kee, PRR 3, 013001) lives *entirely within the
t2g manifold* — eg is not even a variable — so eg–t2g is **not** an independently-citable pairing
claim, and it is **directionally redundant** with the already-grounded `P` (d-polarization)
discriminator. There is also a **conflation trap**: the d⁴/nickelate crystal-field literature uses
"singlet/triplet" for *local ionic spin multiplets*, a different object from *Cooper-pair* spin
symmetry.

The operator, with this verdict in hand, chose to ship eg–t2g as an off-gate discriminator anyway —
**explicitly labeled speculation** (the lab's magnon-drive channel is the precedent for a disclosed
speculative discriminator). Every surface therefore carries the disclosure; nothing presents it as
grounded physics.

## Honesty invariants (non-negotiable)

- No `VALIDATED`/`CONFIRMED` verdict member. Evidence stays **Level 2** — a computed descriptor is
  not a raised level.
- Anti-tautology gate authoritative and **extended, not weakened**: `eg_t2g_imbalance` is added to
  the pinned `OFF_GATE_INVARIANTS` (+ golden `tests/lab_loop/test_closure.py`) and — crucially — is
  **removed from the gate anisotropy** so it is genuinely not re-derivable from the gate's scalar
  input.
- Default path byte-identical (gated behind `LabConfig.compute_orbital_order`, default off).
- No positive scoring term, no new hypothesis (reuses `H7-triplet`). Never reads as
  pairing/SC evidence; the only effect is the *against-triplet* discriminator.
- No fabricated grounding: the speculative label is mandatory wherever the discriminator surfaces.

## Architecture

### Change 1 — gate reframe: gate = charge shape only

`OrbitalResult.anisotropy` (the gate-facing descriptor that replaces the toy `ricebean` at the
DENSITY seam) becomes the **full quadrupole tensor only** (`quadrupole_anisotropy`). Drop
`d_manifold_anisotropy = max(quadrupole, eg_t2g)` — eg–t2g leaves the gate. Consequence, stated
honestly: the gate is now **rank-2, blind to cubic (Oh) eg–t2g splitting** (fcc Ir gate anisotropy
returns to `0.0`). This reverses PR #27's gate-fix but keeps its genuine improvement (the full
tensor still catches in-plane dxz↔dyz redistribution). Reading low for a cubic site is
**conservative** (less localization penalty → never more permissive), documented as such — the same
disposition the #26 review already accepted. Physically cleaner separation: **gate = real-space
charge shape; off-gate = orbital order.**

### Change 2 — eg–t2g as a genuine off-gate signal

- `orbital_order.eg_t2g_imbalance(occ)` already exists (from #27). Keep it as a pure function.
- `OrbitalResult` gains `eg_t2g_imbalance: float | None`; `from_occupations` sets it (mean over
  metal atoms), while `anisotropy` now uses `quadrupole_anisotropy` only.
- `CandidateRecord` gains `eg_t2g_imbalance: float | None` (default None → toy path byte-identical),
  set in the same `compute_orbital_order` gated block that sets `orbital_order_param`.
- Off-gate wiring, mirroring `orbital_order_param` / `field_response_ratio` exactly:
  `OFF_GATE_INVARIANTS` (+ golden test); `METRIC_RANGES["max_eg_t2g_imbalance"] = (0.0, 1.0)`;
  `runner._METRIC_KEYS` + `_NONE_WHEN_UNMEASURED` + `_max_or_none`; `validate_runnable` requires the
  compute flag (else the metric is perpetually unmeasured).
- **Anti-tautology (now genuine):** because eg–t2g is *removed from the gate*, it is a distinct
  contraction not recoverable from the gate's scalar `anisotropy`. Pinned by a test: two candidates
  with equal gate anisotropy but different eg–t2g yield divergent `H7-triplet` outcomes.

### Change 3 — the speculative against-triplet discriminator

High `eg_t2g_imbalance` → evidence **against `H7-triplet`**, via an `H7-triplet` falsifier
`max_eg_t2g_imbalance > θ` (θ fixed in the plan). The avenue's provenance, the module docstring, the
registry/UI, and the changelog all carry the disclosure verbatim:

> *SPECULATIVE — an unverified extrapolation from the t2g-manifold requirement of the Hund's
> interorbital-triplet mechanism (Clepkens-Kee); NOT an independently-grounded pairing rule, and
> directionally redundant with the grounded P discriminator. "Triplet" here means Cooper-pair spin
> symmetry, NOT a local ionic spin multiplet.*

Killable (`KILLED_HYPOTHESIS` reachable), Level 2, never a positive score.

### Change 4 — UI honesty label

`web/metrics.js` gains an `eg_t2g_imbalance` entry: title "eg–t2g imbalance (model-derived,
SPECULATIVE)", the disclosure above, Level-2 wording, and the ionic-vs-Cooper disambiguation.
Provenance mirrors the orbital-order label (computed / absent).

## Test contract (acceptance)

1. Gate reframe: `OrbitalResult.anisotropy` == `quadrupole_anisotropy` (no eg–t2g); Ir fixture gate
   anisotropy back to `0.0`; the in-plane full-tensor test still passes.
2. eg–t2g is off-gate: in `OFF_GATE_INVARIANTS`, not in `GATE_INPUT_CLOSURE`, `is_independent` true;
   golden closure test updated.
3. Anti-tautology: two candidates, equal gate anisotropy, different eg–t2g → divergent H7-triplet
   triage outcome (not re-derivable from gate inputs).
4. Against-triplet falsification: `max_eg_t2g_imbalance > θ` fires KILLED_HYPOTHESIS on H7-triplet;
   unmeasured (None) → INCONCLUSIVE (never fires on absent evidence).
5. Speculative label present on every surface (module docstring, avenue provenance, metrics.js) and
   the Cooper-vs-ionic disambiguation present.
6. Guardrail: eg–t2g never contributes a positive SC/pairing score; toggling the flag moves no
   positive field.
7. No VALIDATED; Level-2 on every path; default path (flag off) byte-identical.

## Non-goals

- No claim of grounded eg–t2g↔pairing physics (it is speculative and labeled so).
- No new hypothesis; no change to `P` or the pairing-symmetry discriminators beyond adding eg–t2g as
  a second (speculative) off-gate signal.
- No separate non-eg–t2g cubic term re-added to the gate (the gate is honestly rank-2, conservative).

## Changelog note

- Moved eg–t2g imbalance from the gate anisotropy (PR #27) to a **speculative off-gate against-
  triplet discriminator**; the gate reverts to full-quadrupole-only (rank-2, cubic-blind =
  conservative). Prior state preserved at `orbital-order-followups-frozen` / tag
  `pr27-eg-t2g-in-gate` for reversion. Anti-tautology gate extended (eg–t2g genuinely off-gate now),
  no invariant weakened, evidence unchanged (Level 2), physics disclosed as speculation.

## Open items for the writing-plans step

- The `H7-triplet` falsification threshold θ on `max_eg_t2g_imbalance`.
- Whether `d_manifold_anisotropy` is deleted outright or kept as an alias of `quadrupole_anisotropy`
  (default: delete; the gate calls `quadrupole_anisotropy` directly).
- Exact `metrics.js` copy for the disclosure.
