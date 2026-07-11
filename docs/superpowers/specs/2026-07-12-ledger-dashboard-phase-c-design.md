# Ledger Dashboard — Phase C Design Spec

**Date:** 2026-07-12
**Status:** approved design (Phase C of 3 — the final piece); building end-to-end.
**Depends on:** Phases A + B (merged, master `27b48bc`) — `web/ledger.js`, the Ledger tab, the focused-material + evidence state, the parity harness, and the two-branch gates.

## 1. Purpose

Phase C adds the **3D material-state stage as the overarching header of the Ledger tab** — the "spine" the operator asked for, to which the two-branch flow, matrix, cards, and controls all relate. It renders the *focused material* in 3D with a six-gate ring and an O_H polariton, and wires click-to-focus + a lineage breadcrumb so the whole dashboard becomes one live surface driven by a single focus.

It is **additive and degrades gracefully**: no WebGL → a fallback note in the 3D region and the Phase A/B 2D dashboard works untouched (honoring #22's decoupling). The 3D makes **no new claim** — it renders the ledger's existing, parity-locked verdicts.

## 2. Placement & isolation

- A dedicated 3D region at the **top of the Ledger tab**, above the roll-up cards, in a **new `web/ledger3d.js`** module with its **own small THREE renderer/scene/canvas** (not the Lab's shared stage).
- Guarded exactly like `app.js` post-#22: `let stage3d = false; try { renderer = new THREE.WebGLRenderer(...); stage3d = true } catch { show fallback note }`. Every renderer/loop use is gated on `stage3d`. No WebGL → the 2D dashboard is unaffected.
- Reuses the CDN `three` importmap already loaded for the Lab stage — **no new network egress**.
- A single owned `requestAnimationFrame` loop drives the polariton + controls damping; it no-ops when `stage3d` is false or the Ledger tab is not visible (to avoid a hidden background render).

## 3. 3D content (the focused material, live-linked)

- **Schematic cluster** for the focused lineage's `element` — atoms + a light rice-bean shell, in the site palette. Honest: a material-state *icon*, not a computed structure (same schematic honesty as `vibration.js`).
- **Six-gate ring** — six nodes orbiting the cluster, each lit (emissive/teal) iff its gate is open for the focused material, read from the **parity-locked gate functions**:
  1. `identity-established` (`gIdentityEstablished`)
  2. `material-state` (`gHudsonMaterialState`)
  3. `transport` (`gCandidateOptical` — optical energy-transport, persistent-gated)
  4. `magnetism` (`opticalMagneticCausality` — ∂M/∂P)
  5. `replication` (`replicationGate`)
  6. `mechanism` (`gHudsonMechanism` — the keystone; opens only when material-state ∧ transport ∧ magnetism ∧ replication all do)
  Each node carries a small HTML label overlay (billboarded or a 2D legend beside the canvas) naming the gate + open/closed. Conventional SC stays in the two-branch flow below — the ring is the Hudson-mechanism progression.
- **O_H polariton** — when the focused material has a coherent optical mode (Branch B `coherentMode`), a schematic pulse/wave orbits the cluster: **steady and self-sustaining at `persistent`** ring-down, **decaying/dim at `driven_dissipative`**, intermediate at `metastable`. Absent when there is no optical mode. Schematic, flagged.

## 4. Navigation

- A **lineage breadcrumb** atop the region: `family ▸ batch ▸ aliquot ▸ [treatment…]` for the focused material's lineage.
- **Click-to-focus:** clicking a matrix column already sets `_state.focusedLineageId` (Phase A); the 3D stage reads the same focus and re-renders on every focus/evidence change (it joins `_renderDash`). A breadcrumb node is also clickable to refocus.

## 5. Parity & honesty

- The ring's six booleans are the **same gate functions** Phases A/B parity-lock — no new decision logic. `tests/test_ledger_parity.py` gains a case asserting the ring states (via an exported `gateRing(material, doublet, th)` helper) equal the Python gates for fixtures.
- The 3D never renders "HUDSON CLAIM VALIDATED"; the mechanism node reads CLOSED (DEFAULT-BLOCK) until its conjunction is met; the cluster/polariton are labelled schematic.
- Determinism: the *state* the 3D reads is deterministic (parity-locked); the animation uses a time delta for the polariton pulse (rendering only — not a produced/serialized value, so `performance.now()` for the render loop is acceptable exactly as the Lab stage already uses it; no `Math.random`/`Date` in any computed gate state).

## 6. Reuse & file plan

- **Create:** `web/ledger3d.js` — the guarded 3D stage: renderer/scene setup, `buildMaterialStage(material, flow, ring)` (cluster + ring + polariton), `gateRing(material, doublet, th)` (the six states), the rAF loop, and `mountLedger3d(container, getFocusedMaterial)` / `updateLedger3d()` entry points.
- **Modify:** `web/ledger.js` — insert the 3D region container + breadcrumb at the top of `_renderDash`; call `ledger3d.update(focusedMaterial, ...)` in the recompute; export the gate helpers `ledger3d` needs (already exported: `gIdentityEstablished`, `gCandidateOptical`, `opticalMagneticCausality`, `replicationGate`; add `gateRing` here or in `ledger3d.js`).
- **Modify:** `web/index.html` — the 3D region container markup + a CSS block (region, breadcrumb, gate-label legend, fallback note) in the existing idiom.
- **Modify:** `tests/test_ledger_parity.py` — the `gateRing` parity case.

No changes to the Lab stage (`app.js`), no Python change.

## 7. Verification

- **Parity (self):** the `gateRing` case locks the six ring states to `hudson_ledger.py`.
- **Fallback path (self, headless):** headless Chrome has no WebGL — verify that the 3D region shows the fallback note and the 2D dashboard renders and recomputes unchanged (the real tab-click flow, post-#22).
- **The 3D visual + polariton animation (operator + bot):** headless cannot render WebGL, so the cluster/ring/polariton look and motion are verifiable **only in the operator's browser**. Phase C is built correct-by-construction and parity-locked; the operator's live-site check + Codex bot are the loop for the 3D itself. I will not claim the 3D visual verified from code alone.

## 8. Out of scope

- Any change to the Lab tab's shared THREE stage.
- Ab-initio structure in the cluster (it stays a schematic icon).
- Export/record of the 3D state; Python/ledger-logic changes.
- (Phase C is the final dashboard phase — nothing follows it.)
