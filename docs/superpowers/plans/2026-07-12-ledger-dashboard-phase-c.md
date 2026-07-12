# Ledger Dashboard — Phase C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the **3D material-state stage** atop the Ledger tab — the focused material's schematic cluster + a six-gate ring + an O_H polariton, with a lineage breadcrumb and click-to-focus — additive and WebGL-degrading, parity-locked, making no new claim.

**Architecture:** A new guarded `web/ledger3d.js` (own THREE renderer, reusing the CDN importmap), a `gateRing()` helper that reuses the parity-locked `branchFlow` + `gIdentityEstablished`, and an insertion at the top of `_renderDash`. No Lab-stage change, no Python change.

**Tech Stack:** ES modules, THREE (pre-existing `three` importmap — no new egress), the existing CSS idiom, pytest + node for parity.

## Global Constraints

- **Additive + WebGL-degrading.** Guard the renderer creation (try/catch → `stage3d` flag) exactly like `app.js` post-#22. No WebGL → a fallback note in the 3D region; the Phase A/B 2D dashboard renders and recomputes unchanged. The rAF loop no-ops when `!stage3d` or the Ledger tab is hidden.
- **Parity, no new logic.** The six ring states come only from `branchFlow(material,doublet,th)` + `gIdentityEstablished(material.witness)` — both already parity-locked. `tests/test_ledger_parity.py` gains a `gateRing` case.
- **Honesty.** The cluster/polariton are schematic (a material-state icon, flagged). The mechanism ring node reads CLOSED until its conjunction is met. Never render "HUDSON CLAIM VALIDATED". No `Math.random`/`Date` in any computed gate state (`performance.now()` for the render loop only is fine — the Lab stage already does this).
- **No new egress** (reuse the `three` importmap); text via `textContent`/`createElement`, never `innerHTML`.
- **Aesthetic reuse:** the dark palette + Phase A/B classes; do not restyle the rest of the site.
- **Commits:** author as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c ...`. NEVER emit AI-identity trailers.
- **Verification:** headless Chrome has NO WebGL, so the 3D visual/polariton is verifiable only in a real browser. Each task verifies what it can: the `gateRing` parity (node), and the **fallback path** headless (no WebGL → note shown, 2D dashboard intact and recomputing). Do NOT claim the 3D visual verified from code alone — the operator's live check + Codex bot are the loop for the 3D itself.

---

## File Structure

- `web/ledger3d.js` **(create)** — guarded renderer/scene, `gateRing(material, doublet, th)`, `buildMaterialStage(...)` (cluster + ring + polariton), the rAF loop, `mountLedger3d(container)` + `updateLedger3d(material)`.
- `web/ledger.js` **(modify)** — export `gateRing` (or import from ledger3d); insert the 3D region + breadcrumb at the top of `_renderDash`; call `updateLedger3d(focusedMaterial)` in the recompute.
- `web/index.html` **(modify)** — the 3D region container + CSS (region, breadcrumb, gate-label legend, fallback note).
- `tests/test_ledger_parity.py` **(modify)** — the `gateRing` parity case.
- `README.md` **(modify, Task 4)** — one line noting the 3D material-state stage.

---

### Task 1: `gateRing` helper + parity

**Files:** Modify `web/ledger.js`, `tests/test_ledger_parity.py`.

**Interfaces:** `export function gateRing(material, doublet, th)` returning `{ identity, materialState, transport, magnetism, replication, mechanism }` (all booleans), reusing `branchFlow` + `gIdentityEstablished` — no new logic.

- [ ] **Step 1: Write the failing parity test.** Append to `tests/test_ledger_parity.py`:
```python
def test_gatering_matches_python_gates():
    # the six ring states are the parity-locked ledger gates for a single focused material
    from orme_lab.hudson_ledger import (evaluate_hudson_ledger, MeasuredEvidence, ReplicationEvidence)
    from orme_lab.hudson_optical import evaluate_hudson_optical
    from orme_lab.identity import IdentityWitness
    from orme_lab.structure import dispersed_sample
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate
    from orme_lab.lineage import singleton_lineage
    el = get_element("Ir")
    opt = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                  matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                  matter_loss_ev=0.02, measured_ringdown_fs=1e30,
                                  measured_dM_dP=1.0, dM_dP_on_resonance=True)
    cand = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)
    m = MeasuredEvidence(optical_result=opt, replication=ReplicationEvidence(3, 2, True, True, True))
    w = IdentityWitness("Ir", "nonmetallic-elemental", "monatomic", 0.0)
    led = evaluate_hudson_ledger([cand], witnesses=[w], distributions=[dispersed_sample(el, 0.95)],
                                 lineages=[singleton_lineage("m1")], measured={"m1/m1": m},
                                 observed_doublet=(1429.53, 1490.99), thresholds=TH)
    py = dict(identity=led.gate.g_identity_established,
              materialState=led.gate.g_hudson_material_state,
              mechanism=led.gate.g_hudson_mechanism)
    matjs = dict(lineage=dict(familyId="m1", batchId="m1", aliquotId="m1", processing=[]), element="Ir",
                 witness=dict(composition="Ir", phase="nonmetallic-elemental", morphology="monatomic", oxidation=0.0),
                 distribution=dict(f1=0.95, sizeDist={"1": 0.95, "2": 0.03, "13": 0.02},
                                   nnDistances=[[float("inf"), 0.95], [2.82, 0.03], [2.82, 0.02]]),
                 optical=dict(supported=[3, 4, 5, 6, 7], persistence="persistent"),
                 measured=dict(hc01NonmetallicConfirmed=True, hc02DispersionConfirmed=True,
                               replication=dict(nBatches=3, nLabs=2, preregistered=True, rawRetained=True, blindedOk=True)),
                 demo=True)
    js = (f'import {{gateRing}} from "{_JS.as_posix()}";'
          f'const r=gateRing({json.dumps(matjs)},[1429.53,1490.99],{json.dumps(_th_js())});'
          f'console.log(JSON.stringify([r.identity, r.materialState, r.mechanism, r.transport, r.magnetism, r.replication]));')
    got = _node(js)
    assert got[0] == py["identity"] and got[1] == py["materialState"] and got[2] == py["mechanism"]
    assert got[3] is True and got[4] is True and got[5] is True   # transport/magnetism/replication all open here
```
(As with the branchFlow test, mirror `dispersed_sample(el, 0.95)`'s exact P(n)/nn values into `matjs.distribution` so HC-02 clears identically on both sides.)

- [ ] **Step 2: Run → fail.** `python3 -m pytest tests/test_ledger_parity.py -k gatering -q`.
- [ ] **Step 3: Implement** in `web/ledger.js` (near `branchFlow`):
```js
export function gateRing(material, doublet, th) {
  const bf = branchFlow(material, doublet, th);
  return {
    identity: gIdentityEstablished(material.witness),
    materialState: bf.hudson.materialState,
    transport: bf.hudson.energyTransport,
    magnetism: bf.hudson.causalMagnetism,
    replication: bf.hudson.replication,
    mechanism: bf.hudson.result,
  };
}
```
- [ ] **Step 4: Run → pass + full suite.**
- [ ] **Step 5: Commit** (`feat(web): gateRing helper — six-gate states for the 3D stage, parity-locked`).

---

### Task 2: `web/ledger3d.js` — the guarded 3D stage

**Files:** Create `web/ledger3d.js`.

**Interfaces:** `import * as THREE from "three"`; `import { OrbitControls } from "three/addons/controls/OrbitControls.js"`; `import { gateRing, branchFlow } from "./ledger.js?v=__BUILD__"`. Exports `mountLedger3d(container)` (creates the guarded renderer into `container`, returns `{ ok: boolean }`; on no-WebGL appends a `.ledger3d-nowebgl` note and returns `{ ok:false }`) and `updateLedger3d(material, doublet, th)` (rebuilds the cluster + ring + polariton for the focused material; no-ops if `!stage3d`).

- [ ] **Step 1: Implement** `ledger3d.js`:
  - Module-scope `let renderer=null, controls=null, scene=null, camera=null, stage3d=false, ringGroup, clusterGroup, polaritonGroup, current=null`.
  - `mountLedger3d(container)`: `try { renderer = new THREE.WebGLRenderer({antialias:true, alpha:true}); stage3d = true } catch(e){ append a `.ledger3d-nowebgl` note textContent "3D material-state stage unavailable (WebGL required); the dashboard below is fully usable." ; return {ok:false} }`. If ok: set size to the container, build scene/camera/lights/OrbitControls (damping, no autorotate by default), add `clusterGroup`/`ringGroup`/`polaritonGroup`, start the rAF loop, add a resize observer on the container. Return `{ok:true}`.
  - `updateLedger3d(material, doublet, th)`: if `!stage3d` return; clear the three groups; build the **schematic cluster** for `material.element` (a few atoms as spheres + a translucent rice-bean shell, site palette — reuse the geometry approach from `app.js` lines ~137-168 but simplified and self-contained); build the **six-gate ring** — six small nodes evenly on a circle around the cluster, each colored teal/emissive when its `gateRing(material,doublet,th)` state is true, muted when false, the `mechanism` node visually distinct (keystone); build the **polariton** from `branchFlow(...).hudson.coherentMode` + `material.optical.persistence` (a ring/torus or particle wave whose amplitude/opacity encodes persistence: persistent = bright steady, metastable = medium, driven_dissipative/absent = none). Store `current = { material, ring, coherent, persistence }` for the loop to animate.
  - The **rAF loop**: `if (!stage3d || !_visible()) { requestAnimationFrame(loop); return; }` — `controls.update()`, animate the polariton (pulse via `performance.now()`), `renderer.render(scene, camera)`. `_visible()` checks the `#ledger` overlay is not hidden (avoid rendering a hidden tab).
  - Guard EVERY renderer/controls/scene use behind `stage3d`.
  - Schematic honesty comment at the top (a material-state icon, not a computed structure).
- [ ] **Step 2: Node smoke.** A tiny node check that `ledger3d.js` parses and exports `mountLedger3d`/`updateLedger3d` (import under `--input-type=module`; it will not create a real renderer under node but the module must load and the functions must be defined). Add to the render-smoke test or a `node --check`.
- [ ] **Step 3: Commit** (`feat(web): ledger3d.js — guarded 3D material-state stage (cluster + gate ring + O_H polariton)`).

---

### Task 3: Integrate into the Ledger tab + CSS + fallback

**Files:** Modify `web/ledger.js`, `web/index.html`.

- [ ] **Step 1: Region + breadcrumb in `_renderDash`.** At the **top** of `_renderDash` (before the legend), build a `.ledger3d-region` containing: a `.ledger3d-crumb` breadcrumb (`family ▸ batch ▸ aliquot ▸ …processing`) for the focused material's lineage (clickable nodes call the same focus setter), a `.ledger3d-canvas` host div, and a `.ledger3d-legend` naming the six ring gates with their open/closed state (so the meaning is readable even in 3D and available as the text fallback). On first render call `mountLedger3d(canvasHost)` once (guard against re-mount on re-render — mount once, then `updateLedger3d` on each render); every render calls `updateLedger3d(focusedMaterial, doublet, th)`.
- [ ] **Step 2: Wire the recompute.** The existing focus/evidence changes already call `_renderDash`; ensure `updateLedger3d` is called there with the current focused material. Keep the renderer mounted across re-renders (do not tear down the canvas each time).
- [ ] **Step 3: CSS** in `index.html`: `.ledger3d-region` (a bordered panel, ~360px tall canvas), `.ledger3d-canvas`, `.ledger3d-crumb` (+ clickable `.crumb-node`), `.ledger3d-legend` (the six gate chips, open=teal/closed=muted), `.ledger3d-nowebgl` (centered note). Dark palette.
- [ ] **Step 4: Verify (fallback path, headless).** Serve `web/`; headless-Chrome (NO WebGL) → click the Ledger tab; confirm: the `.ledger3d-nowebgl` note is present, the `.ledger3d-legend` shows the six gate states as text, and the 2D dashboard (cards/flow/matrix/controls) renders and a scripted evidence toggle still recomputes. Read the PNG. (The 3D canvas itself will be the fallback note in headless — that's expected; the WebGL render is the operator's live check.)
- [ ] **Step 5: Commit** (`feat(web): mount the 3D stage atop the Ledger tab + breadcrumb + CSS + fallback`).

---

### Task 4: a11y, hygiene, README

**Files:** Modify `web/ledger3d.js`, `web/ledger.js`, `web/index.html`, `README.md`, `tests/test_ledger_parity.py`.

- [ ] **Step 1: a11y.** The 3D region has a heading; the breadcrumb nodes are buttons with `aria-label`; the gate-legend chips carry `aria-label` (gate + open/closed) so the meaning is available without the canvas; `prefers-reduced-motion` slows/stops the polariton pulse (a flag the loop checks).
- [ ] **Step 2: Hygiene guard.** Extend the `web/ledger.js`/`ledger3d.js` egress-determinism guard: no `fetch`/`XMLHttpRequest`/`WebSocket`; no `Math.random`/`Date.now` in any computed gate state (the render loop's `performance.now()` is allowed and must be used ONLY for animation, not for a returned/serialized value); no `innerHTML` on researcher text; the string "HUDSON CLAIM VALIDATED" never emitted.
- [ ] **Step 3: README.** One line under the ledger mention noting the 3D material-state stage (schematic; degrades without WebGL).
- [ ] **Step 4: Verify.** Full suite; the fallback-path screenshot; parity green.
- [ ] **Step 5: Commit** (`feat(web): 3D stage a11y, reduced-motion, hygiene guard, README note`).

---

## Self-Review

**Spec coverage:** `gateRing` + parity (T1); the guarded 3D stage — cluster, six-gate ring, O_H polariton, rAF loop (T2); insertion + breadcrumb + click-to-focus + CSS + fallback (T3); a11y/reduced-motion/hygiene/README (T4). Graceful degradation verified via the fallback path (T3/T4). The six ring states reuse the parity-locked gates (T1) — no new claim.

**Placeholder scan:** T1 carries full `gateRing` + parity code; T2/T3 carry the module structure, exact guard/loop/no-WebGL behavior, insertion point, and concrete fallback-path acceptance (the WebGL render is the operator's live check — appropriately, since headless has no WebGL).

**Type consistency:** `gateRing` return shape (`identity/materialState/transport/magnetism/replication/mechanism`) is the single source; `material.element/witness/optical/lineage` are the real field names; `branchFlow`/`gIdentityEstablished`/`DEFAULT_TH`/`DEFAULT_DOUBLET`/`HUDSON_CLAIM` are the real exports.

**Executor note:** This phase's 3D cannot be verified in headless Chrome (no WebGL). Verify the `gateRing` parity and the **fallback path** (no-WebGL → note + working 2D). Do NOT claim the cluster/ring/polariton visual or the animation correct from code alone — that is the operator's live-site check + the Codex bot.
