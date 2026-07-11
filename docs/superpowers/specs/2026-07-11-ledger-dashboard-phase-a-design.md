# Ledger Dashboard — Phase A Design Spec

**Date:** 2026-07-11
**Status:** approved design (Phase A of 3); pending spec review
**Depends on:** `hudson_ledger.py`, `hudson_optical.py`, `identity.py`, `structure.py`, `lineage.py`, `branch_verdict.py` (all merged, master `a291334`).

## 1. Purpose and phasing

The Hudson Claim Ledger and Branch B shipped Python-only; the website does not surface any of it. This builds the **first web view of the ledger** so the operator — who works visually and kinetically — can *see* the research and its outcomes live.

The full dashboard (design approved) is a composite unified by a 3D material-state stage. It ships in three dependency-ordered phases, each shippable:
- **Phase A (this spec):** the ledger data core (a parity-locked JS port) + the 2D dashboard — claim matrix, two roll-up cards, status ladder, HC-02 detail, and interactive evidence controls. Delivers the honest, anti-Frankenstein dashboard on its own.
- **Phase B (later):** the two-branch flow — Branch A / Branch B animated pipelines converging at a locked `G_Hudson`.
- **Phase C (later):** the 3D material-state stage as the overarching view (reuses the THREE renderer; focused cluster + gate ring + O_H polariton; lineage-breadcrumb navigation; click-to-focus).

Phase A is the foundation both later phases render over.

## 2. The data spine — `web/ledger.js` (parity-locked)

A faithful JS port of the ledger's decision logic, exactly as `sim.js` mirrors the toy models and `vibration.js` mirrors `control_experiment.py`. It ports:
- `ClaimStatus` ladder (`CANDIDATE < LEAD < ANOMALOUS < PROVISIONALLY_SUPPORTED < SUPPORTED < INDEPENDENTLY_REPLICATED`), `Route`, `HudsonClaimId` (HC-01…HC-08).
- The eight per-claim assessors' *verdict logic* (given a material's witness, structural distribution, candidate flags, and measured evidence → a `ClaimStatus` + route + note). HC-02 as the fraction/upper-bound/PGM–PGM policy over `f1`/`P(n)`/`R`.
- The six gates (`g_identity_established`, `g_hudson_material_state`, `g_conventional_superconductivity`, `g_candidate_optical` [persistent-only], `optical_magnetic_causality`, `replication_gate`).
- The two roll-ups: claim-level best-of and integrated `max_lineage(min_claim)` with the forbidden `min_claim(max_candidate)` **never computed**; lineage grouping by `family/batch[/processing_history]`.
- The interim-verdict ladder; the invariant that no output string is `"HUDSON CLAIM VALIDATED"`.

**Parity lock — `tests/test_ledger_parity.py` (new).** For a fixed set of `(material, evidence)` fixtures, run the JS port via `node` (the pattern `test_vibration_parity.py` / `test_recorder.py` already use) and assert its claim statuses, gate booleans, roll-up statuses, and interim verdict match `hudson_ledger.evaluate_hudson_ledger` exactly. The dashboard **cannot drift** from the Python authority. Skips cleanly if `node` is absent (as the other parity tests do).

Determinism: pure functions, fixed claim/lineage order, no `Date`/`Math.random` in computed output. No network egress.

## 3. The dossier — seed material states (`web/ledger.js` data block)

Two clearly-separated groups, both frozen:
- **Conducted research (findings).** Our actual results mapped onto claims: the IR-doublet contaminant/control work → HC-04 (a `lead`/`candidate` with the carboxylate mundane alternative), the Meissner screen → HC-06 (a `lead`, conventional route). These carry provenance strings and doc links exactly like `research.js` entries, and are **parity-locked** — a finding's status is whatever `hudson_ledger` computes for it.
- **Illustrative material states (demonstration, clearly labelled).** A small number of synthetic lineages (e.g. `demo/batch-7`, a treated `demo/batch-7▸anneal`) carrying partial measured evidence, so the interactive gates have something to move and the anti-Frankenstein contrast is visible (e.g. one demo lineage that clears HC-07 optically but not HC-06, and a *separate* one that clears HC-06 — portfolio green, integrated not). Every illustrative state renders with a **`demo` badge** and the copy "demonstration, not a finding." They are never presented as evidence.

## 4. The UI — a new **Ledger** tab

A fifth tab (`data-tab="ledger"`) rendering into a `reg-overlay` panel (same pattern as Registry/Research/Loop), matching the existing dark aesthetic (navy, teal/gold, monospace, `chip`/panel classes). Layout, top to bottom:

- **Header + status-ladder legend.** The `Candidate → Lead → Anomalous → Provisionally Supported → Supported → Independently Replicated` scale as a horizontal legend with the palette used everywhere else, and a one-line neutrality banner ("triage, not proof; the lab never asserts a validated verdict").
- **Two roll-up cards, side by side.**
  - *Portfolio claim coverage* — best-of: how many claims have any supporting material, with the count and the supporting material named per claim.
  - *Best coherent same-material candidate* — integrated `max_lineage(min_claim)`: the strongest single lineage and its weakest-link status, plus the two branch results (`g_conventional_superconductivity`, `g_hudson_mechanism`) as separate readouts.
  - The cards visibly diverge; when they do, the integrated card shows the plain-language reason ("no single material clears the core set — HC-04 on Ir·Os, HC-06 on Os, HC-07 on demo/batch-7"). **This divergence is the anti-Frankenstein rule made visible.**
- **Claim matrix — HC-01…HC-08 rows × material-state columns.** Each cell a status dot in the ladder palette. **Every cell at `PROVISIONALLY_SUPPORTED` or above shows the material state that earned it** (column header + an inline label); a green claim never appears without naming its material. Route (conventional/optical) shown as a small glyph on HC-06/HC-07 cells. Clicking a row opens the claim detail (§below).
- **HC-02 detail (on the HC-02 row / its detail).** Rendered as **isolated-site fraction `f1` + a confidence band + the cluster-size evidence P(n) + the PGM–PGM coordination readout**, against the policy thresholds — never a bare checkmark. A compact bar (isolated vs clustered) makes the margin visual.
- **Interactive evidence controls.** For the *focused* material/lineage, toggles and sliders for the measured inputs the ledger consumes: persistent ring-down (a slider through driven-dissipative → metastable → persistent, so the Branch-B gate visibly stays shut until *persistent*), on-resonance ∂M/∂P (toggle), flux exclusion / zero-R / critical behavior / artifact-excluded (toggles), replication (batches + labs), HC-01/HC-02/HC-04 measured confirmations. Every change recomputes `ledger.js` and re-renders the matrix + cards + HC-02 detail **live** — the kinetic payoff.

Transitions animate (status-dot color/scale, card count, HC-02 bar) using CSS transitions already in the site's idiom; no animation library.

## 5. Interactivity model

Pure and deterministic: UI state = `{ focusedLineageId, measuredEvidenceByLineage }`. On any control change, recompute the whole ledger from the dossier + current measured evidence via `ledger.js`, diff nothing, re-render. Researcher text (lineage names, notes) renders via `textContent`/`createElement`, never `innerHTML` (the Phase-3 recorder security posture). No persistence in Phase A beyond in-memory session state (export/record is a later concern).

## 6. Evidence discipline (carried from the Python)

- `credited_sc_lead` renders as **Lead**, never Supported.
- Transport / magnetism / replication gates are **default-blocked**: with the controls at their defaults (no measured evidence) they read closed, and no interaction can make the simulation *self-assert* the mechanism — only the explicit "measured" toggles open them, and they are labelled as *measured lab input*, visually distinct from computed screen values.
- The dashboard never renders the string "HUDSON CLAIM VALIDATED"; the strongest state shown is `Independently Replicated`, reachable only with the replication controls set to real cross-lab metadata.
- Evidence-level stamps stay honest (screen ≤ L2, designs L3, measured L4, replication L5), reusing the existing evidence-badge styling.

## 7. Reuse and file plan

- **Create:** `web/ledger.js` (data spine + dossier + render), `tests/test_ledger_parity.py`.
- **Modify:** `web/index.html` (the 5th tab button + `#ledger` reg-overlay container), `web/app.js` (tab wiring — mount/unmount `renderLedger`, same as Research/Loop), and a small CSS block for the matrix/cards/legend (in the existing `<style>` idiom).
- **Reuse:** the `reg-overlay`, `chip`, panel, and evidence-badge classes; the `research.js` frozen-entry + provenance-link + parity-lock pattern; the tab show/hide logic already in `app.js`.

No new dependencies; no THREE usage in Phase A (that is Phase C).

## 8. Verification

- **Parity:** `test_ledger_parity.py` locks every rendered status/gate/roll-up to `hudson_ledger.py`.
- **Visual (self):** serve `web/` locally and screenshot the Ledger tab with headless Chrome (`--headless --screenshot`), Read the PNG, and confirm layout/palette/labels render and that a scripted evidence change moves the cells/cards. This is now available in-environment.
- **Visual (loop):** because scripted screenshots can't fully exercise live animation/interaction, the **Codex PR bot review + the operator's live-site check** remain in the loop for the web change (per the standing visual-review commitment). No claim of visual correctness from code alone.
- Determinism + no-egress asserted by the parity test and a static check that `ledger.js` performs no `fetch`/network and uses no `Date`/`Math.random` in computed output.

## 9. Out of scope (Phase A)

- The two-branch flow diagram (Phase B).
- The 3D material-state stage, gate ring, O_H polariton, lineage-tree navigation in 3D (Phase C).
- Export/record of ledger sessions (a later extension of the Phase-3 recorder).
- Any change to the Python ledger, Branch B, or the screen — Phase A is a view layer only.
