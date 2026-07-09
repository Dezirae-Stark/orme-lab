# Research Platform Phase 1 — Implementation Plan

Spec: `docs/superpowers/specs/2026-07-09-research-platform-phase1-design.md`. Branch `research-foundation`.

**Constraints:** no egress/telemetry; base sterile by default; loading explicit; predictions L3 / screens ≤2; every entry cites provenance; dossier results parity-locked to Python; commit as Dezirae, no AI trailers; new JS import uses `?v=__BUILD__`.

### Task 1 — `web/research.js` (the spine)
Create `RESEARCH` (array of entries per spec: `ir-negative` L1, `contaminant` L2 w/ `result{residual,verdict}` + preset, `control-exp` L3 w/ `result{c13_shift,o18_shift,decisive_count}`, plus `thermal` + `meissner` short entries w/ presets), `LEVEL_LABEL = {1:"mathematical consistency",2:"simulation candidate",3:"laboratory prediction"}`, and `renderResearch(el, onLoad)` — builds a card per entry (title, `Level N/6 — label` badge, statement, provenance, **Load into models ▶** button when `entry.preset` calling `onLoad(entry)`, **full note ↗** link to `entry.doc`), plus the neutrality banner. Frozen entries (`Object.freeze`).

### Task 2 — `index.html`: Research tab + overlay + neutral widget host
Add nav button `<button class="tab" data-tab="research" role="tab" aria-selected="false">Research</button>` after Loop. Add a `#research` `.reg-overlay` (hidden) mirroring the registry/loop structure: `.reg-inner` → `.reg-head` (eyebrow "Conducted research", title "Research Dossier", sub = neutrality contract + "peer-review & physical test runs", `#researchClose` chip "← back to lab") → `#researchBody`.

### Task 3 — `patent_tests.js`: sterile defaults
In `renderPatentTests`, remove hard `value="..."` from `pwIrLineLo`/`pwIrLine`/`pwThT`/`pwMeB` and add `placeholder="e.g. 1490.99"` style hints (neutral, not the patent value as a default). In each `upd*` handler, if inputs are empty/NaN, set the output to a neutral prompt ("enter a doublet, or load a result from the Research tab") instead of computing on 0. Keep the element/select defaults (Rh/Ir list) — those aren't conclusions. Expose nothing new; app.js fills inputs via events.

### Task 4 — `app.js`: wire tab, render, loadPreset
Import `renderResearch` (`?v=__BUILD__`). In `setTab`: add `$("research").hidden = name !== "research";`. At init: `renderResearch($("researchBody"), loadPreset)`. Add `$("researchClose")` → `setTab("lab")`; extend the Escape handler to include `!$("research").hidden`. Implement `loadPreset(entry)`: `setTab("lab")`; for each `[id,val]` in `entry.preset.inputs`, set `$(id).value = val` and dispatch `new Event("input",{bubbles:true})` / `change` so existing widget handlers recompute; show a transient "loaded: <title>" confirmation.

### Task 5 — `styles.css`: dossier cards
Add `.research-entry` card styling (reuse `.reg-overlay/.reg-inner/.reg-head`), evidence-badge chip, `.research-banner` for the neutrality contract, load-button + note-link styles. Theme-consistent with registry cards.

### Task 6 — `tests/test_research_parity.py`
Parse `web/research.js` (regex-extract the `RESEARCH` entries' numeric `result` fields + evidence levels + preset input ids). Assert:
- `contaminant.result` == `screen_contaminants((1429.53,1490.99))` (residual ≈, verdict ==).
- `control-exp.result` c13≈−33/o18≈−36 (±1) and decisive_count == `design_control_experiment((1429.53,1490.99),"Rh")`.
- every `evidence_level ∈ {1,2,3}`; the prediction entry ==3, screen entries ≤2.
- every `preset.inputs` id is one of the known widget ids `{pwIrSym,pwIrLineLo,pwIrLine,pwThSym,pwThT,pwMeB}`.

### Task 7 — verify + PR
`node --check` each JS file; `python3 -m pytest -q` green; if feasible, serve `web/` and Playwright-smoke: Research tab renders, Load fills the IR widget + switches to Lab, base is empty on first load. Commit per task. Open PR (no merge). NOTE: touches `web/**` → merging will trigger a Pages deploy.
