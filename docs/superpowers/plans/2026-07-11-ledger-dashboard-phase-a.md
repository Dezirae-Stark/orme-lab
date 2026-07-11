# Ledger Dashboard — Phase A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Ship the first web view of the Hudson Claim Ledger — a new **Ledger** tab with a parity-locked JS ledger core, a claim matrix (every green cell names its material), two roll-up cards (portfolio vs integrated), HC-02 as fraction+CI, and interactive evidence controls — matching the site's aesthetic and honest by construction.

**Architecture:** A JS port of the ledger's decision layer (`web/ledger.js`) parity-locked to `hudson_ledger.py` via `tests/test_ledger_parity.py` (node subprocess, the pattern `test_vibration_parity.py` uses). A new `reg-overlay` tab wired exactly like Research/Loop. Pure/deterministic; researcher text via `textContent`; no network, no THREE (that is Phase C).

**Tech Stack:** ES modules (no build step, `?v=__BUILD__` cache-bust like the other web modules), the existing CSS idiom, pytest + node for parity. No new dependencies.

## Global Constraints

- **Parity to Python.** Every status/gate/roll-up/verdict the JS produces is locked to `hudson_ledger.py` by `test_ledger_parity.py`. The dashboard must not compute anything the Python doesn't.
- **Anti-Frankenstein, visible.** The integrated roll-up is `max_lineage(min_claim)` — the JS must never compute `min_claim(max_candidate)`. Every claim cell at PROVISIONALLY_SUPPORTED+ must render the material state that earned it.
- **Default-block + evidence discipline.** With controls at defaults, transport/magnetism/replication gates read closed; `credited_sc_lead` renders as **Lead**, never Supported; the string `"HUDSON CLAIM VALIDATED"` is never rendered. Illustrative material states carry a `demo` badge and "demonstration, not a finding."
- **Determinism + no egress.** No `Date`/`Math.random` in computed output; no `fetch`/network; researcher-entered text rendered via `textContent`/`createElement`, never `innerHTML`.
- **Aesthetic reuse.** Reuse `reg-overlay`/`reg-inner`/`reg-head`/`chip`/panel/evidence-badge classes and the dark palette; do not restyle the rest of the site.
- **Commits:** author as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c ...`. NEVER emit AI-identity trailers in author, committer, message body, or PR body.
- **Verification:** each UI task is checked by serving `web/` and headless-Chrome screenshotting the Ledger tab (`google-chrome --headless=new --no-sandbox --screenshot=... --window-size=1440,900 http://127.0.0.1:PORT/#ledger`), plus the Codex PR bot + operator live-site check for animation/interaction. No claim of visual correctness from code alone.

---

## File Structure

- `web/ledger.js` **(create)** — enums, assessors, gates, roll-ups, interim verdict, `evaluateLedger`, the dossier, and `renderLedger`.
- `web/index.html` **(modify)** — the 5th tab button + `#ledger` `reg-overlay` container.
- `web/app.js` **(modify)** — import `renderLedger`, wire `setTab`/close/Escape, call on init.
- `tests/test_ledger_parity.py` **(create)** — node-subprocess parity to `hudson_ledger.py`.
- CSS: a block appended to the existing `<style>` in `index.html`.

**The JS ledger API (mirrors `hudson_ledger.py`, all pure):**
```
CLAIM_STATUS = {CANDIDATE:0, LEAD:1, ANOMALOUS:2, PROVISIONALLY_SUPPORTED:3, SUPPORTED:4, INDEPENDENTLY_REPLICATED:5}
ROUTE = {CONVENTIONAL:"conventional", OPTICAL:"optical", NONE:"none"}
HC = ["HC-01",...,"HC-08"]
assessHc01(witness,target,th) / assessHc02(dist,th) / assessHc03(m)…assessHc08(m)  -> {id,status,route,note}
gIdentityEstablished(witness) / gHudsonMaterialState(witness,dist,target,th)
gConventionalSuperconductivity(m) / gCandidateOptical(opt) / opticalMagneticCausality(opt) / replicationGate(rep,th)
rollupBestOf(perMaterial) / rollupIntegrated(perLineage, CORE)   // max_lineage(min_claim)
interimVerdict(bits)
evaluateLedger(materials, {th}) -> {claims, gate, integratedStatus, integratedLineageId, perLineage}
```
`th` mirrors the HC-02/replication `ModelThresholds` fields; a material = `{lineage:{familyId,batchId,aliquotId,processing:[]}, element, witness, distribution:{f1,sizeDist,nnDistances}, creditedScLead, optical, measured, demo}`.

---

### Task 1: The Ledger tab (skeleton) — tab wiring + empty overlay

**Files:** Modify `web/index.html`, `web/app.js`; Create `web/ledger.js` (stub export).

- [ ] **Step 1: Add the tab button + overlay to `index.html`.** After the Research tab button add `<button class="tab" data-tab="ledger" role="tab" aria-selected="false">Ledger</button>`. After the `#research` overlay add:
```html
<div id="ledger" class="reg-overlay" hidden>
  <div class="reg-inner">
    <header class="reg-head">
      <div>
        <div class="reg-eyebrow">Hudson Claim Ledger</div>
        <h2 class="reg-title display">Ledger Dashboard</h2>
        <p class="reg-sub">Hudson's eight ORME claims assessed <strong>falsify-first</strong> — each with the ordinary explanation attacked first. <em>Triage, not proof</em>; the lab never asserts a validated verdict. A green claim always names the material state that earned it.</p>
      </div>
      <button id="ledgerClose" class="chip">← back to lab</button>
    </header>
    <div id="ledgerBody"></div>
  </div>
</div>
```
- [ ] **Step 2: Stub `web/ledger.js`.**
```js
// web/ledger.js — Hudson Claim Ledger dashboard (Phase A). Parity-locked to hudson_ledger.py.
export function renderLedger(el) {
  el.textContent = "";
  const p = document.createElement("p");
  p.className = "reg-sub";
  p.textContent = "Ledger dashboard loading…";
  el.appendChild(p);
}
```
- [ ] **Step 3: Wire `app.js`.** Add `import { renderLedger } from "./ledger.js?v=__BUILD__";`. In `setTab`, add `$("ledger").hidden = name !== "ledger";`. Extend the Escape handler condition to include `!$("ledger").hidden`. In init, add `renderLedger($("ledgerBody"));` and a `ledgerClose` listener mirroring `researchClose`.
- [ ] **Step 4: Verify render.** Run: `cd /orme-lab && (cd web && python3 -m http.server 8099 &) ; sleep 1 ; google-chrome --headless=new --no-sandbox --disable-gpu --window-size=1440,900 --virtual-time-budget=4000 --screenshot=/tmp/ledger_t1.png "http://127.0.0.1:8099/#ledger" ; pkill -f "http.server 8099"` — then the reviewer/controller Reads `/tmp/ledger_t1.png` and confirms a Ledger tab exists and its overlay shows the header + "loading…". (The tab must be clickable to `#ledger`; if the hash doesn't auto-open, the wiring is via the tab button — screenshot the site and confirm the 5th tab button reads "Ledger".)
- [ ] **Step 5: Commit.**
```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' add web/index.html web/app.js web/ledger.js
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m "feat(web): Ledger tab skeleton + overlay wiring"
```

---

### Task 2: `ledger.js` core — enums, assessors, gates (+ parity)

**Files:** Modify `web/ledger.js`; Create `tests/test_ledger_parity.py`.

**Interfaces produced:** the enums and every `assessHcNN` / `g*` function in the API block above. Faithful ports of `hudson_ledger.py` (read that file for exact thresholds and branch order). Key equivalences: HC-01 clears (→ PROVISIONALLY) when `witness.composition===target && Math.abs(witness.oxidation)<=0.5 && witness.phase==="nonmetallic-elemental"`; HC-02 policy `f1>=th.hc02MinIsolated && (1-f1)+th.hc02ClusterMargin<=th.hc02MaxClustered && coordinated<=th.hc02PgmPgmTol` where `coordinated=Σ frac for (d,frac) in nnDistances if isFinite(d)&&d<=th.hc02BondLen`; `gCandidateOptical` requires `{STRONG,MACRO,ELECTRONIC,LOW_LOSS}⊆opt.supported && opt.persistence==="persistent"`; a measured confirmation (`m.hcNNConfirmed`) upgrades a ≥PROVISIONALLY claim to SUPPORTED.

- [ ] **Step 1: Write the failing parity test** `tests/test_ledger_parity.py`:
```python
"""Parity: web/ledger.js assessors & gates match hudson_ledger.py exactly (via node)."""
from __future__ import annotations
import json, shutil, subprocess
from pathlib import Path
import pytest
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.identity import IdentityWitness
from orme_lab.structure import dispersed_sample, make_distribution
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab import hudson_ledger as HL

_JS = Path(__file__).resolve().parents[1] / "web" / "ledger.js"
TH = DEFAULT_CONFIG.thresholds


def _th_js():
    return dict(hc02MinIsolated=TH.hudson_hc02_min_isolated_fraction,
                hc02MaxClustered=TH.hudson_hc02_max_clustered_fraction,
                hc02ClusterMargin=TH.hudson_hc02_cluster_margin,
                hc02PgmPgmTol=TH.hudson_hc02_pgm_pgm_tolerance,
                hc02BondLen=TH.hudson_hc02_bond_length_ang,
                replMinBatches=TH.hudson_replication_min_batches,
                replMinLabs=TH.hudson_replication_min_labs)


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    out = subprocess.run([node, "--input-type=module", "-e", js],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_hc02_policy_matches_python():
    el = get_element("Ir")
    for f1 in (0.95, 0.60, 0.30):
        dist = dispersed_sample(el, f1)
        py = HL.assess_hc02(dist, TH).status.value
        distjs = dict(f1=dist.f1(), sizeDist=dist.size_distribution(),
                      nnDistances=[list(t) for t in dist.nn_distances()])
        js = (f'import {{assessHc02}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(assessHc02({json.dumps(distjs)},{json.dumps(_th_js())}).status));')
        assert _node(js) == py, f"HC-02 mismatch at f1={f1}"


def test_identity_and_material_state_match_python():
    cases = [
        ("Ir", "nonmetallic-elemental", "monatomic", 0.0),
        ("Ir", "metallic", "bulk", 0.0),
        ("IrO2", "oxide", "nanoparticle", 4.0),
    ]
    el = get_element("Ir")
    dist = dispersed_sample(el, 0.95)
    for comp, phase, morph, ox in cases:
        w = IdentityWitness(comp, phase, morph, ox)
        py_est = HL.g_identity_established(w)
        py_ms, _ = HL.g_hudson_material_state(w, dist, "Ir", TH)
        wjs = dict(composition=comp, phase=phase, morphology=morph, oxidation=ox)
        distjs = dict(f1=dist.f1(), sizeDist=dist.size_distribution(),
                      nnDistances=[list(t) for t in dist.nn_distances()])
        js = (f'import {{gIdentityEstablished,gHudsonMaterialState}} from "{_JS.as_posix()}";'
              f'const w={json.dumps(wjs)},d={json.dumps(distjs)},th={json.dumps(_th_js())};'
              f'console.log(JSON.stringify([gIdentityEstablished(w),gHudsonMaterialState(w,d,"Ir",th)]));')
        got = _node(js)
        assert got[0] is py_est and got[1] is py_ms


def test_optical_and_replication_gates_match_python():
    # optical persistent vs metastable; replication thresholds
    supported = [3, 4, 5, 6]  # STRONG,MACRO,LOW_LOSS,ELECTRONIC as int levels
    for persist, expect in (("persistent", True), ("metastable", False)):
        opt = dict(supported=supported, persistence=persist)
        js = (f'import {{gCandidateOptical}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(gCandidateOptical({json.dumps(opt)})));')
        assert _node(js) is expect
    for batches, labs, ok in ((3, 2, True), (2, 2, False), (3, 1, False)):
        rep = dict(nBatches=batches, nLabs=labs, preregistered=True, rawRetained=True, blindedOk=True)
        py = HL.replication_gate(HL.ReplicationEvidence(batches, labs, True, True, True), TH)
        js = (f'import {{replicationGate}} from "{_JS.as_posix()}";'
              f'console.log(JSON.stringify(replicationGate({json.dumps(rep)},{json.dumps(_th_js())})));')
        assert _node(js) is py is ok
```
Note the JS `opt.supported` uses the same integer claim levels Branch B uses (3=STRONG_COUPLING, 4=MACRO, 5=LOW_LOSS, 6=ELECTRONIC); the JS `gCandidateOptical` checks the `{3,4,5,6}` subset + `persistence==="persistent"`.

- [ ] **Step 2: Run to verify it fails.** Run: `cd /orme-lab && python3 -m pytest tests/test_ledger_parity.py -q` → FAIL (SyntaxError / missing exports).
- [ ] **Step 3: Implement** the enums, assessors, and gates in `web/ledger.js` as faithful ports (read `hudson_ledger.py` §HC-01..HC-08 assessors and §gates; port the exact conditions). Export each function. Deterministic; no `Date`/`Math.random`.
- [ ] **Step 4: Run to verify it passes + full suite.** Run: `cd /orme-lab && python3 -m pytest tests/test_ledger_parity.py -q && python3 -m pytest -q`.
- [ ] **Step 5: Commit** (`feat(web): ledger.js assessors + gates, parity-locked to hudson_ledger.py`).

---

### Task 3: `ledger.js` roll-ups, interim verdict, `evaluateLedger` (+ parity)

**Files:** Modify `web/ledger.js`, `tests/test_ledger_parity.py`.

**Interfaces:** `rollupBestOf`, `rollupIntegrated` (`max_lineage(min_claim over CORE)`; group by `familyId/batchId[/processing]`; **never** `min_claim(max_candidate)`), `interimVerdict`, `evaluateLedger(materials,{th})`. CORE = `["HC-01","HC-02","HC-04","HC-06","HC-07"]`. `g_hudson_mechanism`/`g_conventional_superconductivity` are EXISTENTIALS over lineages, each same-lineage.

- [ ] **Step 1: Write the failing parity test** — append the anti-Frankenstein keystone (mirror `test_anti_frankenstein_max_min_discriminates_from_forbidden_min_max`): build 5 single-claim lineages in JS fixture form, assert JS `evaluateLedger` gives `integratedStatus < SUPPORTED` while `min(claimStatus for CORE) === SUPPORTED` (the two forms diverge), and `gate.gHudsonMechanism === false`; and a full single-lineage fixture giving `gHudsonMechanism === true` with `interimVerdict` never `"HUDSON CLAIM VALIDATED"`. Compare the same fixtures against `HL.evaluate_hudson_ledger` built from equivalent Python objects (construct `IdentityWitness`, `dispersed_sample`, real `CandidateRecord`s via `evaluate_candidate`, `MeasuredEvidence`, `singleton_lineage`) so JS and Python agree cell-for-cell.
- [ ] **Step 2: Run → fail.**
- [ ] **Step 3: Implement** the roll-ups (mirror `evaluate_hudson_ledger` §5.2 exactly — inner `min` over CORE per lineage, outer `max`; existential mechanism/conventional gates over lineages; representative-lineage bit reporting), `interimVerdict` (the priority ladder, never the forbidden string), and `evaluateLedger`.
- [ ] **Step 4: Run → pass + full suite.**
- [ ] **Step 5: Commit** (`feat(web): ledger.js two roll-ups + interim verdict (anti-Frankenstein)`).

---

### Task 4: The dossier — conducted research + labelled demo states

**Files:** Modify `web/ledger.js`, `tests/test_ledger_parity.py`.

**Interfaces:** `export const DOSSIER` — an array of material states. Findings (frozen, provenance + doc link like `research.js`): the IR-doublet contaminant/control → an HC-04 material (LEAD, carboxylate mundane alternative), the Meissner screen → an HC-06 material (LEAD, conventional). Demo states (`demo:true`): `demo/batch-7` and a treated `demo/batch-7▸anneal`, carrying partial measured evidence chosen so the portfolio-vs-integrated divergence is visible (one clears HC-07 optically-persistent, a *separate* one clears HC-06) — none clears the core conjunction.

- [ ] **Step 1: Write the failing test** — assert `DOSSIER` findings' computed statuses match `hudson_ledger.py` for the same inputs (parity), every `demo:true` entry has a `demo` flag and a "demonstration" note, and no finding is marked `demo`. Assert `evaluateLedger(DOSSIER)` never yields `interimVerdict === "HUDSON CLAIM VALIDATED"` and its portfolio can be green while integrated is `< SUPPORTED` (the demo states are arranged to show this).
- [ ] **Step 2–4:** implement the dossier; run → pass + full suite.
- [ ] **Step 5: Commit** (`feat(web): ledger dossier — conducted findings + labelled demo states`).

---

### Task 5: `renderLedger` — the 2D dashboard UI

**Files:** Modify `web/ledger.js`, `web/index.html` (CSS block).

**Interfaces:** replace the Task-1 stub `renderLedger(el)` with the full render over `evaluateLedger(DOSSIER, {th})`: (1) the **status-ladder legend** (`Candidate → Lead → … → Independently Replicated`); (2) two **roll-up cards** side by side — *Portfolio claim coverage* (count + supporting material per claim) and *Best coherent same-material candidate* (integrated status + `gConventionalSuperconductivity`/`gHudsonMechanism` readouts + the plain-language divergence reason); (3) the **claim matrix** HC-01..HC-08 × material columns, each cell a status dot, **every ≥PROVISIONALLY cell labels its material** (column name + inline earned-by), route glyph on HC-06/HC-07; (4) the **HC-02 detail** (f1 + confidence band + P(n) cluster evidence + PGM–PGM readout as a bar, not a checkmark). All text via `textContent`/`createElement`. `credited_sc_lead` → "Lead". Add a CSS block (matrix grid, status-dot palette matching the site, cards, legend) to the `<style>` in `index.html`, in the existing idiom.

- [ ] **Step 1–3:** implement render + CSS.
- [ ] **Step 4: Verify (browser).** Serve + headless-screenshot `#ledger` (as Task 1 Step 4) to `/tmp/ledger_t5.png`; the reviewer Reads it and confirms: legend present, two cards present and visibly different when portfolio≠integrated, matrix renders with a material name on every green cell, HC-02 shows a fraction/bar not a checkmark, palette matches the site. **Also** assert in a small DOM smoke test (node + a minimal DOM shim, or a string check) that `renderLedger` output contains no literal `"HUDSON CLAIM VALIDATED"` and no `innerHTML` assignment path for researcher text.
- [ ] **Step 5: Commit** (`feat(web): ledger dashboard render — matrix, roll-up cards, HC-02 detail`).

---

### Task 6: Interactive evidence controls (live recompute)

**Files:** Modify `web/ledger.js`, `web/index.html` (CSS).

**Interfaces:** a controls panel for the **focused material** (selected by clicking a matrix column header; default = first material). Controls mirror `MeasuredEvidence`: a **ring-down slider** (driven-dissipative → metastable → persistent — the Branch-B optical transport gate must stay shut until *persistent*), toggles for on-resonance ∂M/∂P, flux exclusion, zero-R, critical behavior, artifact-excluded, and HC-01/HC-02/HC-04 measured confirmations, and replication inputs (batches, labs). State = `{focusedLineageId, measuredByLineage}`; any change recomputes `evaluateLedger` and re-renders matrix + cards + HC-02 detail. Measured controls are visually marked "measured lab input", distinct from computed values.

- [ ] **Step 1–3:** implement controls + live recompute.
- [ ] **Step 4: Verify (browser + scripted).** A test that drives the page with node/JSDOM *or* a headless-Chrome script that: loads `#ledger`, sets the ring-down slider to metastable then persistent, and screenshots each (`/tmp/ledger_t6_meta.png`, `/tmp/ledger_t6_persist.png`); the reviewer Reads both and confirms the optical transport / HC-07 cell is closed at metastable and opens at persistent, and that with all controls at default the transport/magnetism/replication gates read closed (default-block holds live). Codex bot + operator live check remain the loop for full interaction.
- [ ] **Step 5: Commit** (`feat(web): interactive evidence controls with live ledger recompute`).

---

### Task 7: Polish — a11y, no-egress/determinism check, README note

**Files:** Modify `web/ledger.js`, `web/index.html`, `README.md`.

- [ ] **Step 1:** a11y — the Ledger tab button carries `role="tab"`/`aria-selected` toggled with the others; matrix cells have accessible labels (`aria-label` naming claim, status, and earned-by material); the overlay is keyboard-dismissable (Escape, already wired).
- [ ] **Step 2:** a static guard test (`tests/test_ledger_parity.py` or a small `test_ledger_web_hygiene.py`): assert `web/ledger.js` contains no `fetch(`/`XMLHttpRequest`/`WebSocket`, no `Date.now`/`Math.random`, and no `.innerHTML =` with a non-constant right-hand side (grep-level check).
- [ ] **Step 3:** README — add one line under the interactive-lab section noting the **Ledger** tab (the falsify-first HC-01..HC-08 dashboard). Keep framing honest.
- [ ] **Step 4:** Run full suite; serve + screenshot the final Ledger tab to `/tmp/ledger_final.png` for the reviewer + operator.
- [ ] **Step 5: Commit** (`feat(web): ledger dashboard a11y, egress/determinism guard, README note`).

---

## Self-Review

**Spec coverage:** parity-locked core (T2/T3) + dossier (T4) + tab (T1) + matrix/cards/HC-02 (T5) + interactive controls (T6) + a11y/hygiene/README (T7). Anti-Frankenstein keystone ported (T3). Default-block + Lead-not-Supported + never-"validated" enforced and tested (T3/T4/T5/T6/T7). Browser-screenshot verification on every UI task (T1/T5/T6/T7). No THREE, no export (Phases C / later).

**Placeholder scan:** logic + parity steps carry complete code; UI steps carry the render/control structure, exact reuse classes, and concrete browser-screenshot acceptance criteria (pixel-final CSS is verified by screenshot + bot, not prescribed line-by-line — appropriate for a view layer).

**Type consistency:** the JS API block is the single source; `_th_js()` keys, the `material`/`opt`/`measured` shapes, the integer claim levels for `opt.supported`, and the CORE list are identical across T2–T6 and the parity tests.

**Verification note for the executor:** there is a browser in this environment (`google-chrome --headless`). Use it on every UI task and Read the PNG. Do NOT claim visual correctness from code alone; the Codex PR bot and the operator's live-site check remain the loop for animation/interaction.
