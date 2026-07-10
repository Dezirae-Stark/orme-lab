# Design — Research platform Phase 3: record + export (structured entry + session snapshot)

**Date:** 2026-07-10 · **Status:** approved for implementation planning (platform design approved;
Phase 3 shape settled in the platform brainstorm — structured JSON entry + markdown note + full
session snapshot, all client-side, no egress).
**Part of:** the sterile-base + loadable-research platform. Phase 1 (dossier + load) = PR #5,
Phase 2 (3D viewer) = PR #6. This is the final phase.

## Purpose

Close the loop: let a researcher who has run the tools — sterile or loaded from our research —
**record a new test/hypothesis** and **export** it, entirely on their own machine. Three outputs:
1. a **structured JSON entry** (reloadable into the models; PR-submittable to extend the registry),
2. a **markdown lab-note** (human-readable, for peer review), and
3. a **full session snapshot** (every UI input + which research preset was loaded) a peer can
   re-import to land in the exact same environment.

Everything is `localStorage` + user-initiated file download/upload. **Nothing leaves the machine.**

## Non-goals

- No backend, no telemetry, no network egress — the record/export is local-only (consistent with
  the existing `scientist.js` localStorage pattern, which already documents "never sent anywhere").
- No server-side persistence or accounts — entries live in this browser until exported.
- No auto-recording — recording is always an explicit researcher action (neutrality preserved).

## Security (load-bearing — the carry-over flagged since Phase 1)

Researcher-entered text (label, hypothesis, notes) is the **first user content to reach the DOM.**
It MUST be rendered with `textContent` / DOM node construction only — **never** interpolated into
`innerHTML`. Imported session/entry JSON is parsed defensively (schema-checked, unknown fields
ignored, types validated) before anything is applied or rendered. The markdown export is a text
file (no DOM render of untrusted content on our side).

## Architecture

```
web/
  recorder.js     # NEW — entry schema, localStorage CRUD, JSON/markdown serializers, validation (pure, testable)
  app.js          # + captureSnapshot()/applySnapshot() (touch app state); the Record UI + wiring
  index.html      # + a "Record" section in the Research tab (form + entry list + export/import)
  research.js     # renderResearch gains a record-panel mount point (or app.js renders it into #research)
  styles.css      # + record-form / entry-list styles
tests/
  test_recorder.py   # NEW — run recorder.js via node: entry round-trip, markdown fields, defensive import
```

### `recorder.js` (pure, THREE-free, DOM-free)

```js
export const STORE_KEY = "orme:research-entries";
// Entry schema (all fields present; user text is arbitrary UTF-8, treated as untrusted downstream).
//   { id, label, hypothesis, notes, created, snapshot, outputs }
export function makeEntry({ label, hypothesis, notes, snapshot, outputs, created, id }) { /* normalize */ }
export function loadEntries() { /* parse STORE_KEY, validate array, drop malformed */ }
export function saveEntries(entries) { /* JSON.stringify to STORE_KEY */ }
export function addEntry(entry) { /* load, push, save; returns entries */ }
export function removeEntry(id) { /* load, filter, save */ }
export function toMarkdown(entry) { /* deterministic .md string: title, hypothesis, notes, snapshot table, outputs */ }
export function validateSnapshot(obj) { /* type-checked, whitelisted keys only; returns a clean snapshot or null */ }
```

`created` is passed in by the caller (a browser timestamp) — recorder.js itself uses no clock, so
its outputs are testable deterministically. `id` likewise passed in (caller supplies a value derived
from `created` + a counter — no `Math.random`/`Date` inside recorder.js).

### `app.js` — capture / apply / UI

- **`captureSnapshot()`** → `{ state:{elSym,geomKind,spinKind,fieldT,tempK}, vib:{on,species,mode,iso,metal},
  eigen:{k,l,m}, patent:{pwIrSym,pwIrLineLo,pwIrLine,pwThSym,pwThT,pwMeB}, loadedResearchId }`. Reads
  current DOM/state.
- **`applySnapshot(s)`** — validate via `recorder.validateSnapshot`; set `state`, call `syncControls()`
  + `recompute()`; restore vib via `activateVibration`/`setVibOn`; set patent inputs + dispatch events;
  set eigen selects. Only writes recognized fields; ignores the rest.
- **Record UI** (in the Research tab, below the dossier): a form (label, hypothesis, notes textareas),
  **Record current state** (captures a snapshot + the current screen outputs into a new entry), an
  **entry list** (each: reload ▶, export .json ⬇, export .md ⬇, delete), and global **Export session ⬇**
  / **Import session ⬆** (a file input). All user text rendered via `textContent`.
- **Downloads** via a `Blob` + `URL.createObjectURL` + a synthetic `<a download>` click — user-initiated,
  local, no network. **Import** via `<input type=file>` → `FileReader` → `JSON.parse` in try/catch →
  `validateSnapshot`/entry-validate → apply. Nothing auto-loads on page load beyond listing saved entries.

### Neutrality preserved

The base stays sterile; recording captures whatever the researcher has set up (or loaded), and does
nothing until they click Record. Reloading an entry restores its snapshot — an explicit action, clearly
theirs, not ours. Our dossier entries remain read-only and separate from researcher-recorded ones.

## Testing

`test_recorder.py` (runs `recorder.js` via `node` subprocess, skips if node absent):
- **round-trip:** `makeEntry` → `toMarkdown` contains the label/hypothesis/notes/outputs; `addEntry`
  then `loadEntries` returns the entry (using a fake in-memory localStorage shim injected into node).
- **defensive import:** `validateSnapshot` on junk (missing keys, wrong types, extra keys, a snapshot
  with a `<script>` in a string field) returns a clean whitelisted object or null — never throws.
- **determinism:** `toMarkdown` of a fixed entry is byte-identical across calls (no clock/RNG inside).
- `node --check` on all changed JS. XSS-safe DOM rendering (textContent) is verified by review +
  a Node/JSDOM-free assertion that the render helper is not called with innerHTML (grep-level check in
  the test: recorder.js contains no `innerHTML`).

## Invariants preserved

No egress/telemetry (localStorage + user-download only); user text is `textContent`-rendered and
imports are schema-validated (no XSS, no injection); recorder.js is pure/deterministic (clock/id passed
in); neutrality (explicit record, sterile base); no new dependency.

## Open items for the writing-plans step

- Exact markdown template; the entry-list empty state copy.
- Whether "Export session" and a recorded entry's snapshot share one serializer (default: yes — an
  entry embeds a snapshot; "Export session" exports a bare snapshot).
- Storage cap / entry count guard (default: soft cap ~200 entries, oldest-trimmed with a log line).
