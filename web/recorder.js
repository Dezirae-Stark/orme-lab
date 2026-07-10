// web/recorder.js
/*
 * recorder.js -- Phase 3: local record + export of researcher tests. PURE + DOM-free
 * (no THREE, no network). Entries live in this browser's localStorage and are exported
 * to files only on an explicit user action -- nothing is ever sent anywhere (same posture
 * as scientist.js). app.js owns the DOM/capture/apply; this file owns the data model,
 * validation, and serialization so it can be unit-tested via node.
 *
 * SECURITY: user text (label/hypothesis/notes) is arbitrary UTF-8 treated as UNTRUSTED
 * downstream -- app.js renders it with textContent only, never innerHTML. Imported JSON is
 * schema-validated here (whitelisted keys, primitives only) before app.js applies it.
 *
 * DETERMINISM: this module uses NO clock and NO RNG. The caller (app.js) supplies `created`
 * and `id`, so toMarkdown/makeEntry are byte-deterministic and testable.
 */

export const STORE_KEY = "orme:research-entries";
export const MAX_ENTRIES = 200;

// Snapshot key whitelist -- only these are captured/restored; anything else in imported JSON is dropped.
const SNAP = {
  state: ["elSym", "geomKind", "spinKind", "fieldT", "tempK"],
  vib: ["on", "species", "mode", "iso", "metal"],
  eigen: ["k", "l", "m", "on"],
  patent: ["pwIrSym", "pwIrLineLo", "pwIrLine", "pwThSym", "pwThT", "pwMeB"],
};

const isPrim = (v) => { const t = typeof v; return t === "string" || t === "number" || t === "boolean"; };
const capStr = (v, n) => (typeof v === "string" ? v.slice(0, n) : v == null ? "" : String(v).slice(0, n));

function pickPrimitives(from, keys) {
  const src = from && typeof from === "object" ? from : {};
  const out = {};
  for (const k of keys) {
    if (!Object.prototype.hasOwnProperty.call(src, k)) continue;
    const v = src[k];
    if (isPrim(v)) out[k] = typeof v === "string" ? v.slice(0, 120) : v;
  }
  return out;
}

/** Return a clean, whitelisted snapshot (primitives only) or null. Never throws. */
export function validateSnapshot(obj) {
  if (!obj || typeof obj !== "object") return null;
  return {
    state: pickPrimitives(obj.state, SNAP.state),
    vib: pickPrimitives(obj.vib, SNAP.vib),
    eigen: pickPrimitives(obj.eigen, SNAP.eigen),
    patent: pickPrimitives(obj.patent, SNAP.patent),
    loadedResearchId: capStr(obj.loadedResearchId, 64),
  };
}

function sanitizeOutputs(obj) {
  const src = obj && typeof obj === "object" ? obj : {};
  const out = {};
  for (const k of Object.keys(src)) {
    if (Object.keys(out).length >= 20) break;             // hard cap
    if (isPrim(src[k])) out[capStr(k, 40)] = typeof src[k] === "string" ? src[k].slice(0, 400) : src[k];
  }
  return out;
}

/** Build a normalized entry. `id` and `created` are supplied by the caller (no clock here). */
export function makeEntry({ id, created, label, hypothesis, notes, snapshot, outputs } = {}) {
  return {
    id: capStr(id, 64) || capStr(created, 64),
    created: capStr(created, 40),
    label: capStr(label, 200),
    hypothesis: capStr(hypothesis, 4000),
    notes: capStr(notes, 8000),
    snapshot: validateSnapshot(snapshot) || { state: {}, vib: {}, eigen: {}, patent: {}, loadedResearchId: "" },
    outputs: sanitizeOutputs(outputs),
  };
}

function getStore() {
  try { return typeof localStorage !== "undefined" ? localStorage : null; } catch { return null; }
}

/** Load entries; drop anything malformed. Never throws. */
export function loadEntries() {
  const s = getStore();
  if (!s) return [];
  let raw;
  try { raw = JSON.parse(s.getItem(STORE_KEY) || "[]"); } catch { return []; }
  if (!Array.isArray(raw)) return [];
  return raw.filter((e) => e && typeof e === "object").map((e) => makeEntry(e));
}

/** Persist entries. Never throws — a full quota (QuotaExceededError) is swallowed with a warn,
 *  so a failed save loses the new entry rather than crashing the record handler. Returns success. */
export function saveEntries(entries) {
  const s = getStore();
  if (!s) return false;
  const trimmed = (Array.isArray(entries) ? entries : []).slice(-MAX_ENTRIES);
  try {
    s.setItem(STORE_KEY, JSON.stringify(trimmed));
    return true;
  } catch (err) {
    if (typeof console !== "undefined") console.warn("recorder: could not persist entries", err);
    return false;
  }
}

export function addEntry(entry) {
  const es = loadEntries();
  es.push(makeEntry(entry));
  saveEntries(es);
  return loadEntries();
}

export function removeEntry(id) {
  saveEntries(loadEntries().filter((e) => e.id !== id));
  return loadEntries();
}

/** Deterministic markdown lab-note for an entry (no clock/RNG). */
export function toMarkdown(entry) {
  const e = makeEntry(entry);
  const st = e.snapshot.state || {};
  const vb = e.snapshot.vib || {};
  const pt = e.snapshot.patent || {};
  const kv = (o) => Object.keys(o).sort().map((k) => `${k}: ${o[k]}`).join(" · ") || "(none)";
  const outs = Object.keys(e.outputs).sort().map((k) => `- **${k}**: ${e.outputs[k]}`).join("\n") || "- (none)";
  return [
    `# ${e.label || "(untitled test)"}`,
    ``,
    `*Recorded: ${e.created || "(unknown)"}*`,
    ``,
    `## Hypothesis`,
    e.hypothesis || "(none)",
    ``,
    `## Notes`,
    e.notes || "(none)",
    ``,
    `## Captured state`,
    `- state: ${kv(st)}`,
    `- vibration: ${kv(vb)}`,
    `- patent inputs: ${kv(pt)}`,
    `- loaded research: ${e.snapshot.loadedResearchId || "(none — sterile)"}`,
    ``,
    `## Screen outputs at capture`,
    outs,
    ``,
    `---`,
    `Recorded in the ORME Lab research platform (client-side; not peer-reviewed).`,
    `Evidence stays ≤ Level 3 — this is a prediction/triage artifact, not an observation.`,
    ``,
  ].join("\n");
}
