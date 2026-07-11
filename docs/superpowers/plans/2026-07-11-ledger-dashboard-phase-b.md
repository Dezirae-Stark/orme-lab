# Ledger Dashboard — Phase B Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Add the **two-branch flow** to the Ledger tab — Branch A (conventional SC) and Branch B (Hudson optical) as parallel, independent, animated gate-pipelines that fill as evidence loads, each terminating in its own result node, wired to the Phase A focused-material + evidence controls.

**Architecture:** A pure `branchFlow(material, doublet, th)` helper (parity-locked to `hudson_ledger.py`) + a `_buildBranchFlow` render section inserted in `_renderDash` between the roll-up cards and the matrix. CSS-only kinetics. No new decision logic, no Python change, no THREE.

**Tech Stack:** ES modules (`web/ledger.js`), the existing CSS idiom, pytest + node for parity. No new dependencies.

## Global Constraints

- **Parity to Python.** `branchFlow`'s `conventional.result` and `hudson.result` are locked to `hudson_ledger.py` (a single-material `evaluate_hudson_ledger` run) by `tests/test_ledger_parity.py`. No new logic the Python doesn't have.
- **Two branches stay INDEPENDENT.** Two parallel tracks that never merge — Branch A → `G_conventional_superconductivity`, Branch B → `G_hudson_mechanism`. The render must not draw a path where one branch's evidence advances the other.
- **Default-block, visible.** At control defaults both result nodes read **CLOSED (DEFAULT-BLOCK)**; only measured toggles open them. The energy-transport stage stays shut until the ring-down is **persistent** (a metastable ring-down must not fill it). Never render "HUDSON CLAIM VALIDATED".
- **Determinism + no egress.** No `Date`/`Math.random` in computed state; no `fetch`/network; text via `textContent`/`createElement`, never `innerHTML`.
- **Aesthetic reuse.** Reuse the dark palette + Phase A classes; `prefers-reduced-motion` disables the flow animation. Do not restyle the rest of the site or the Phase A sections.
- **Commits:** author as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c ...`. NEVER emit AI-identity trailers in author, committer, message body, or PR body.
- **Verification:** UI tasks are checked by serving `web/` and headless-Chrome screenshotting the Ledger tab (#22 decoupled the tabs from WebGL, so the real tab-click flow renders headless). Read the PNG. Codex bot + operator live check remain the loop for animation feel.

---

## File Structure

- `web/ledger.js` **(modify)** — add `branchFlow(material, doublet, th)` (exported, pure) and `_buildBranchFlow(material, doublet, th)`; insert the section in `_renderDash`.
- `web/index.html` **(modify)** — a CSS block for the flow (nodes, connectors, flow keyframes, reduced-motion guard, lock glyph).
- `tests/test_ledger_parity.py` **(modify)** — the `branchFlow` parity case.
- `README.md` **(modify, Task 4)** — one line noting the two-branch flow.

**`branchFlow` return shape (the single source both render and parity bind to):**
```
{ conventional: { zeroR, flux, critical, artifact, result },
  hudson:       { coherentMode, materialCoupling, energyTransport, causalMagnetism, materialState, replication, result } }
```

---

### Task 1: `branchFlow` helper + parity

**Files:** Modify `web/ledger.js`, `tests/test_ledger_parity.py`.

**Interfaces:** `export function branchFlow(material, doublet, th)` — pure; mirrors `evaluateLedger`'s per-lineage gate computation for a single focused material. `conventional.result === gConventionalSuperconductivity(measured)`; `hudson.result === materialState ∧ gCandidateOptical ∧ opticalMagneticCausality ∧ replicationGate` where `materialState = HC-01 record ≥ PROVISIONALLY ∧ HC-02 record ≥ PROVISIONALLY` (the same batch-combined rule `evaluateLedger` uses, applied to the single material's records).

- [ ] **Step 1: Write the failing parity test.** Append to `tests/test_ledger_parity.py`:
```python
def test_branchflow_results_match_python_gates():
    # branchFlow's two result booleans must equal the Python ledger's gate bits for the same
    # single-material inputs (conventional SC gate; Hudson mechanism conjunction).
    from orme_lab.hudson_ledger import (evaluate_hudson_ledger, MeasuredEvidence,
                                        ReplicationEvidence)
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
    # a fully-evidenced single material: conventional SC full AND the Hudson mechanism full
    cand = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)
    m = MeasuredEvidence(zero_resistance=True, flux_exclusion=True, critical_behavior=True,
                         artifact_excluded=True, optical_result=opt,
                         replication=ReplicationEvidence(3, 2, True, True, True))
    w = IdentityWitness("Ir", "nonmetallic-elemental", "monatomic", 0.0)
    led = evaluate_hudson_ledger([cand], witnesses=[w], distributions=[dispersed_sample(el, 0.95)],
                                 lineages=[singleton_lineage("m1")], measured={"m1/m1": m},
                                 observed_doublet=(1429.53, 1490.99), thresholds=TH)
    py_conv = led.gate.g_conventional_superconductivity
    py_mech = led.gate.g_hudson_mechanism
    # JS: the equivalent single material fixture (witness nonmetallic-elemental, dispersed, full evidence)
    matjs = dict(
        lineage=dict(familyId="m1", batchId="m1", aliquotId="m1", processing=[]),
        element="Ir",
        witness=dict(composition="Ir", phase="nonmetallic-elemental", morphology="monatomic", oxidation=0.0),
        distribution=dict(f1=0.95, sizeDist={"1": 0.95, "2": 0.03, "13": 0.02},
                          nnDistances=[[float("inf"), 0.95], [2.82, 0.03], [2.82, 0.02]]),
        optical=dict(supported=[3, 4, 5, 6, 7], persistence="persistent"),
        measured=dict(zeroResistance=True, fluxExclusion=True, criticalBehavior=True,
                      artifactExcluded=True, hc01NonmetallicConfirmed=True, hc02DispersionConfirmed=True,
                      replication=dict(nBatches=3, nLabs=2, preregistered=True, rawRetained=True, blindedOk=True)),
        demo=True)
    js = (f'import {{branchFlow}} from "{_JS.as_posix()}";'
          f'const bf=branchFlow({json.dumps(matjs)},[1429.53,1490.99],{json.dumps(_th_js())});'
          f'console.log(JSON.stringify([bf.conventional.result, bf.hudson.result]));')
    got = _node(js)
    assert got == [py_conv, py_mech]


def test_branchflow_energy_transport_needs_persistent():
    # the Branch-B energy-transport stage must be false for a metastable ring-down, true for persistent
    def _bf(persist):
        matjs = dict(lineage=dict(familyId="x", batchId="x", aliquotId="x", processing=[]), element="Ir",
                     witness=None, distribution=None,
                     optical=dict(supported=[3, 4, 5, 6], persistence=persist), measured={}, demo=True)
        js = (f'import {{branchFlow}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(branchFlow({json.dumps(matjs)},[1429.53,1490.99],{json.dumps(_th_js())}).hudson.energyTransport));')
        return _node(js)
    assert _bf("metastable") is False
    assert _bf("persistent") is True
```
(Note: dispersed_sample's exact P(n)/nn values must match what `dispersed_sample(el, 0.95)` produces — the implementer should read them from Python and mirror into `matjs.distribution` so HC-02 clears identically on both sides. If they differ, HC-02 → materialState → hudson.result diverges and the test correctly fails.)

- [ ] **Step 2: Run → fail.** `cd /orme-lab && python3 -m pytest tests/test_ledger_parity.py -k branchflow -q` → FAIL (missing export).
- [ ] **Step 3: Implement** `branchFlow` in `web/ledger.js` (near the gate functions), calling the internal `_materialClaimRecords`, `gConventionalSuperconductivity`, `gCandidateOptical`, `opticalMagneticCausality`, `replicationGate`, and the `HUDSON_CLAIM` levels — no new logic. Deterministic; no `Date`/`Math.random`.
- [ ] **Step 4: Run → pass + full suite.** `python3 -m pytest tests/test_ledger_parity.py -q && python3 -m pytest -q`.
- [ ] **Step 5: Commit** (`feat(web): branchFlow helper — per-material two-branch gate states, parity-locked`).

---

### Task 2: `_buildBranchFlow` render section + insertion + base CSS

**Files:** Modify `web/ledger.js`, `web/index.html`.

**Interfaces:** `_buildBranchFlow(material, doublet, th)` returns a DOM section rendering two labelled tracks from `branchFlow(...)`; inserted in `_renderDash` **between the `cards` block and the matrix**, for the focused material.

- [ ] **Step 1: Implement the render.** Add `_buildBranchFlow(material, doublet, th)`:
  - A section titled "Two-branch flow — <material title>" with a one-line note: "Conventional superconductivity and the Hudson optical mechanism are **independent** results — a material may clear one without the other."
  - **Branch A track:** a labelled row "Branch A · conventional SC" with four stage nodes `zero-R`, `Meissner flux`, `critical behavior`, `artifact excluded`, connectors between them, ending in a result node `⬢ G_conventional_superconductivity` that reads CLOSED (DEFAULT-BLOCK) / OPEN. Each stage node carries a `.filled` class iff its `branchFlow.conventional.*` is true.
  - **Branch B track:** a labelled row "Branch B · Hudson optical" with stage nodes `coherent mode`, `material coupling`, `energy transport`, `causal magnetism`, ending in `⬢ G_hudson_mechanism`; plus a **feeder** row showing `Hudson material state` and `replication` joining into the result node. `.filled` per `branchFlow.hudson.*`; the result node OPEN iff `branchFlow.hudson.result`.
  - Each node has an `aria-label` naming the stage and its state; all text via `textContent`.
  - In `_renderDash`, after `dash.appendChild(cards);` and before the matrix, add:
    `dash.appendChild(_buildBranchFlow(materials.find((m) => _lineageKey(m.lineage) === focusedKey) || materials[0], doublet, th));`
- [ ] **Step 2: Base CSS.** Add a block to `index.html`'s `<style>`: `.ledger-flow` (section), `.ledger-flow-track` (a flex row), `.ledger-flow-node` (a pill/box; `.filled` = teal/green fill, unfilled = muted), `.ledger-flow-conn` (connector line), `.ledger-flow-result` (the hex/box result node; `.open` vs `.closed` with a lock glyph). Reuse the palette vars.
- [ ] **Step 3: Verify (browser).** Serve `web/`; headless-screenshot `#ledger` (click the tab; #22 makes this work headless) to `/tmp/ledger_b2.png`; the reviewer Reads it and confirms: two labelled tracks present, both result nodes read CLOSED (DEFAULT-BLOCK) at defaults, the section sits between the cards and the matrix, palette matches.
- [ ] **Step 4: Commit** (`feat(web): two-branch flow render section + base styling`).

---

### Task 3: Kinetics — fill transitions, connector flow, lock, reduced-motion

**Files:** Modify `web/index.html` (CSS), `web/ledger.js` (class hooks if needed).

- [ ] **Step 1: Animation CSS.** Node `.filled` gets a color + soft glow transition; a connector between two consecutive filled nodes gets `.flowing` with a slow animated gradient/pulse keyframe; the result `.open` node animates the lock opening (icon + color). Add `@media (prefers-reduced-motion: reduce) { … animation: none; }` so only static filled/unfilled states remain. The `.flowing` class is applied in `_buildBranchFlow` to a connector iff both adjacent nodes are filled.
- [ ] **Step 2: Verify (browser, interactive).** A headless-Chrome script (Playwright via the MCP node_modules path, or a screenshot at two states): load `#ledger`, screenshot default (`/tmp/ledger_b3_default.png`); then focus the `demo/batch-7` column and drive the ring-down slider from metastable to persistent, screenshotting each (`/tmp/ledger_b3_meta.png`, `/tmp/ledger_b3_persist.png`). The reviewer Reads them and confirms: at default both result nodes CLOSED; the Branch B **energy-transport** node is unfilled at metastable and **filled at persistent**; the reduced-motion path leaves static states intact.
- [ ] **Step 3: Commit** (`feat(web): two-branch flow kinetics — fill/flow/lock animation, reduced-motion`).

---

### Task 4: a11y, hygiene guard, README note

**Files:** Modify `web/ledger.js`, `web/index.html`, `README.md`, `tests/test_ledger_parity.py`.

- [ ] **Step 1: a11y.** The flow section has a heading; each node/result carries an `aria-label` (stage + state); the section is reachable/announced. No focus trap.
- [ ] **Step 2: Hygiene guard.** Extend the existing `web/ledger.js` egress/determinism guard test to cover the new code (no `fetch`/`Date.now`/`Math.random`/`innerHTML` introduced). Add a check that `branchFlow` output contains no path merging the two branches (a static assertion that `hudson.result` never reads a Branch-A field and vice-versa — e.g. grep that `branchFlow`'s conventional block references only `measured.*`/`gConventionalSuperconductivity` and the hudson block only optical/material-state/replication).
- [ ] **Step 3: README.** One line under the ledger/dashboard mention noting the two-branch flow (independent tracks, animated). Honest framing.
- [ ] **Step 4: Verify + final screenshot.** Full suite; serve + screenshot the final Ledger tab with the flow to `/tmp/ledger_b_final.png`.
- [ ] **Step 5: Commit** (`feat(web): two-branch flow a11y, hygiene guard, README note`).

---

## Self-Review

**Spec coverage:** `branchFlow` + parity (T1), the two independent tracks + result nodes + material-state/replication feeder (T2), kinetics with persistent-gated energy transport + reduced-motion (T3), a11y/hygiene/README (T4). Branches-stay-separate enforced in render (T2) and asserted (T4). Default-block + never-"validated" carried from Phase A and re-checked (T2/T3).

**Placeholder scan:** T1 carries full parity code + the `branchFlow` contract; UI tasks carry the render structure, exact insertion point, reuse classes, and concrete browser-screenshot acceptance (pixel-final CSS verified by screenshot + bot, not prescribed line-by-line).

**Type consistency:** the `branchFlow` return shape is the single source for T1–T4; `material.measured`/`material.optical`/`material.witness`/`material.distribution` are the real field names; `HUDSON_CLAIM` levels (3/4/5/6/7) and the `_th_js()` keys match Phase A and the parity test.

**Executor note:** #22 decoupled the tabs from WebGL, so the real Ledger tab-click flow now renders in headless Chrome — screenshot it directly (no harness needed). Do NOT claim animation correctness from a static screenshot; the Codex bot + operator live check remain the loop for flow feel.
