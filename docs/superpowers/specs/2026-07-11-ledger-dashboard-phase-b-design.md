# Ledger Dashboard — Phase B Design Spec

**Date:** 2026-07-11
**Status:** approved design (Phase B of 3); pending spec review
**Depends on:** Phase A (merged, master `6a49ca9`) — `web/ledger.js`, the Ledger tab, the evidence-control state, and the parity harness.

## 1. Purpose and place

Phase A shipped the claim matrix, the two roll-up cards, and the interactive evidence controls. Phase B adds the **two-branch flow** — the kinetic view the operator asked for: Branch A (conventional superconductivity) and Branch B (Hudson optical coherence) as **parallel pipelines whose gate-nodes fill as evidence loads**, kept visually independent and each terminating in its own result. This makes the branch-independence architecture *legible at a glance* and gives the evidence controls an immediate, animated payoff.

It is a **new section inside the Ledger tab**, inserted between the two roll-up cards and the claim matrix, reflecting the **focused material** (the same focus the evidence controls already drive). It reuses Phase A's data spine and recompute cycle entirely — no new controls, no Python change, no THREE (that is Phase C).

## 2. The two pipelines (kept independent — never merged)

The reviewer's endorsed rule: *"Keep conventional superconductivity and Hudson optical coherence visually separate — parallel tracks with separate gate diagrams, converging only at the full-mechanism level."* So the section renders **two parallel tracks**, each ending in its **own** result node. They never merge — a candidate may clear one without the other.

**Branch A — conventional superconductivity** (stages fill from the focused material's measured evidence):
```
[zero-R] → [Meissner flux] → [critical behavior] → [artifact excluded] ──▶ ⬢ G_conventional_superconductivity
```
Each stage node is filled iff its `MeasuredEvidence` field is set (`zeroResistance` / `fluxExclusion` / `criticalBehavior` / `artifactExcluded`). The result node opens iff `gConventionalSuperconductivity` (all four).

**Branch B — Hudson optical coherence** (stages from the focused material's optical result + persistence):
```
[coherent mode] → [material coupling] → [energy transport] → [causal magnetism] ──▶ ⬢ G_hudson_mechanism
                                                                                   ▲
                                        [Hudson material state] ── [replication] ──┘
```
- **coherent mode** = `STRONG_COUPLING (L3) ∧ MACRO_COHERENCE (L4)` in `optical.supported`
- **material coupling** = `ELECTRONIC_COUPLING (L6)`
- **energy transport** = `gCandidateOptical(opt)` — **stays shut until the ring-down is PERSISTENT** (reuses the Phase A gate; a metastable ring-down does not fill it)
- **causal magnetism** = `opticalMagneticCausality(opt)` (measured ∂M/∂P, L7)
- The **G_hudson_mechanism** result node also takes the **material-state gate** (`gHudsonMaterialState`) and **replication** as prerequisite inputs (rendered as a joining feeder), and opens iff `material-state ∧ gCandidateOptical ∧ causality ∧ replication` — exactly the ledger's existential mechanism gate for the focused lineage.

Both result nodes read **CLOSED (DEFAULT-BLOCK)** with a lock glyph until their conjunction is met, and are labelled as **separate, independent results**.

## 3. Kinetics

CSS-only (the site idiom; no animation library):
- A **stage node** transitions color + a soft glow/scale when it fills (evidence present) — the immediate response to toggling a control.
- **Connectors** between two consecutive *filled* stages carry a subtle animated flow (a slow gradient/pulse along the line); connectors into an unfilled stage stay dim/static.
- A **result node** shows a lock that opens (icon + color) the moment its full conjunction is met; while blocked it reads CLOSED (DEFAULT-BLOCK).
- `prefers-reduced-motion` disables the flow animation (static filled/unfilled states remain).

Because the section reads the focused material's live evidence, dragging the ring-down slider from metastable → persistent visibly fills Branch B's energy-transport stage; toggling flux/zero-R/critical/artifact fills Branch A's stages one by one; setting replication + the attestations opens the G_hudson_mechanism feeder.

## 4. Data + parity

No new decision logic. The per-stage booleans are exactly the gate *inputs* Phase A already exposes and parity-locks:
- Branch A stages = the four `measured.*` fields; the result = `gConventionalSuperconductivity(measured)`.
- Branch B stages = `HudsonClaim` membership in `optical.supported` + `gCandidateOptical` + `opticalMagneticCausality`; the result = `gHudsonMaterialState ∧ gCandidateOptical ∧ opticalMagneticCausality ∧ replicationGate` for the focused lineage.

A small exported helper `branchFlow(material, th)` returns the structured stage/result states `{ conventional: {zeroR, flux, critical, artifact, result}, hudson: {coherentMode, materialCoupling, energyTransport, causalMagnetism, materialState, replication, result} }`, computed purely from the already-parity-locked gate functions. `tests/test_ledger_parity.py` gains a case asserting `branchFlow`'s result booleans equal the Python `g_conventional_superconductivity` / the mechanism conjunction for the same fixtures — so the flow can never diverge from the authority.

## 5. Reuse and file plan

- **Modify:** `web/ledger.js` — add `branchFlow(material, th)` and `_buildBranchFlow(focusedMaterial, th)`; insert the section in `renderLedger` between the roll-up cards and the matrix; hook it into the existing recompute (the evidence-control `onChange` already re-renders).
- **Modify:** `web/index.html` — a CSS block for the flow (nodes, connectors, the flow keyframes, the reduced-motion guard, lock glyph), in the existing idiom.
- **Modify:** `tests/test_ledger_parity.py` — the `branchFlow` parity case.
- **Reuse:** the exported gate functions, `_state.focusedLineageId` + the overlay evidence, the recompute cycle, the status/route palette, the `_el` DOM helpers, the MEASURED-LAB-INPUT/badge styling.

No new dependencies; no THREE; no new evidence controls; no Python change.

## 6. Honesty + constraints (carried from Phase A)

- Default-block visible: both result nodes CLOSED at control defaults; nothing the simulation does opens them — only measured toggles do.
- The two branches are labelled **independent**; the section never implies one branch's evidence advances the other, and never renders "HUDSON CLAIM VALIDATED".
- Determinism (no `Date`/`Math.random` in computed state), no network egress, researcher text via `textContent`.
- Aesthetic: reuse the dark palette + classes; do not restyle the rest of the site or the Phase A sections.

## 7. Verification

- **Parity:** the `branchFlow` case in `test_ledger_parity.py` locks the result booleans to Python.
- **Visual (self):** serve `web/` and headless-screenshot the Ledger tab (now with WebGL-decoupled boot from #22, the real tab-click flow renders headless) at default and after a scripted evidence change (metastable→persistent), Read the PNGs, confirm the Branch B energy-transport stage fills only at persistent and the result nodes stay CLOSED at defaults.
- **Visual (loop):** the Codex PR bot + the operator's live-site check remain in the loop for the animation/flow feel.

## 8. Out of scope (Phase B)

- The 3D material-state stage, gate ring, O_H polariton, lineage-tree navigation (Phase C — the overarching integrator).
- Any new evidence controls or Python/ledger-logic change.
- Export/record of the flow state.
