# Research Platform Phase 3 — Implementation Plan

Spec: `docs/superpowers/specs/2026-07-10-research-platform-phase3-design.md`. Branch `research-phase3`.

**Constraints:** local-only (localStorage + user-download, no egress); user text rendered via `textContent` ONLY (never innerHTML); imports schema-validated (validateSnapshot whitelists keys + primitives); recorder.js pure/deterministic (clock+id passed in, no Date/Math.random); commit as Dezirae; new JS import `?v=__BUILD__`.

### Task 1 — `web/recorder.js` (pure core)
Export `STORE_KEY`, `MAX_ENTRIES`, `validateSnapshot(obj)` (whitelist state/vib/eigen/patent keys, primitives only, cap string len), `makeEntry({id,created,label,hypothesis,notes,snapshot,outputs})` (normalize + cap + validateSnapshot), `sanitizeOutputs`, `loadEntries()`/`saveEntries()`/`addEntry()`/`removeEntry(id)` (localStorage CRUD, drop malformed, trim to MAX_ENTRIES), `toMarkdown(entry)` (deterministic .md from entry fields — no clock inside). No DOM/THREE/network.

### Task 2 — `tests/test_recorder.py` (node subprocess; skip if no node)
- **round-trip:** inject an in-memory `globalThis.localStorage` shim; `addEntry(makeEntry(...))` then `loadEntries()` returns it; `toMarkdown` contains label/hypothesis/notes + an output value.
- **defensive import:** `validateSnapshot` on `null`, a string, `{state:{elSym:{}, evil:1}, __proto__:{x:1}}`, and a snapshot with `<script>` in a field → returns a clean object with only whitelisted primitive keys, never throws; the `<script>` string is preserved as data (inert) but confined to a whitelisted key or dropped.
- **determinism:** `toMarkdown(fixedEntry)` byte-identical across two calls.
- **no innerHTML in recorder.js** (grep assertion).

### Task 3 — `index.html`: Record section in the Research tab
Below `#researchBody` inside `#research`: a `#recordPanel` with a form — `<input id="recLabel">`, `<textarea id="recHypothesis">`, `<textarea id="recNotes">`, `<button id="recSave">Record current state</button>`; a `<div id="recEntries">` list; and `<button id="recExportSession">Export session ⬇</button>` + `<label>Import session <input id="recImport" type="file" accept=".json" hidden></label>`. Neutrality note: "Recorded locally in this browser; export to a file to share. Nothing is sent anywhere."

### Task 4 — `app.js`: capture/apply + Record UI + downloads/import
- `import * as REC from "./recorder.js?v=__BUILD__"`.
- `captureSnapshot()` → {state:{elSym,geomKind,spinKind,fieldT,tempK}, vib:{on,species,mode,iso,metal}, eigen:{k,l,m}, patent:{pwIrSym,pwIrLineLo,pwIrLine,pwThSym,pwThT,pwMeB}, loadedResearchId}. Read from `state`, `vib`, `eigen`, DOM inputs.
- `captureOutputs()` → flat {irOut,thermalOut,meissnerOut} from the patent widget `.pw-out` textContent (or "" if blank).
- `applySnapshot(s)`: `const v = REC.validateSnapshot(s); if(!v) return;` set `state.*` from v.state (coerce numbers), `syncControls(); recompute();`; restore vib (`if(v.vib.on){activateVibration(v.vib.species); set mode/iso/metal; refreshVibration()}` else `setVibOn(false)`); set patent inputs + dispatch input events; set eigen selects.
- `renderRecordEntries()`: for each `REC.loadEntries()` build a row with `createElement` + `textContent` for label/created; buttons reload ▶ (applySnapshot(entry.snapshot)+setTab), export .json ⬇ (download JSON.stringify(entry)), export .md ⬇ (download REC.toMarkdown(entry)), delete (REC.removeEntry+rerender). NO innerHTML with entry text.
- `download(name, text, mime)`: Blob + createObjectURL + synthetic `<a download>` click + revoke. Local only.
- wire: `recSave` → `REC.addEntry(REC.makeEntry({id:String(Date.now()), created:new Date().toISOString(), label:$("recLabel").value, hypothesis:$("recHypothesis").value, notes:$("recNotes").value, snapshot:captureSnapshot(), outputs:captureOutputs()}))` then clear form + `renderRecordEntries()`. (Date/id are created HERE in app.js — recorder.js stays clock-free.) `recExportSession` → download session.json of captureSnapshot(). `recImport` change → FileReader → JSON.parse in try/catch → applySnapshot → toast. `safe("recorder", wireRecorder)` in boot; call `renderRecordEntries()` in wireTabs.

### Task 5 — `styles.css`
`.record-panel` form + `.rec-entry` list rows + buttons, theme-consistent.

### Task 6 — verify + PR
`node --check` all changed JS; Node smoke of recorder.js (round-trip + toMarkdown + validateSnapshot on junk); `python3 -m pytest -q` green; opus review (no-egress, XSS/textContent, defensive import/validateSnapshot, determinism, neutrality). PR (no merge; touches web/ → deploy). Honest note: browser E2E unavailable (no Chrome) — the download/import/reload UX needs the operator's eye on the deployed site.
