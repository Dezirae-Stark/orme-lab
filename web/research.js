// web/research.js
/*
 * research.js -- the structured spine of the Research dossier. Obsidian Circuit's
 * conducted findings as cited, machine-readable entries. The Research tab renders
 * these; the "Load into models" buttons inject an entry's `preset` into the base
 * widgets. Every `result` here is PARITY-LOCKED to the Python authority by
 * tests/test_research_parity.py -- the dossier cannot drift from the code.
 *
 * Neutrality: nothing here preloads into the Lab tab. The base is sterile; loading
 * a result is always an explicit click and only fills widget inputs -- it never
 * changes the underlying model. No network egress.
 */

const DOC = "https://github.com/Dezirae-Stark/orme-lab/blob/master/docs/";

export const LEVEL_LABEL = {
  1: "mathematical consistency",
  2: "simulation candidate",
  3: "laboratory prediction",
};

export const RESEARCH = [
  Object.freeze({
    id: "ir-negative",
    title: "IR doublet — metal–metal bonding excluded",
    evidence_level: 1,
    leg: "negative",
    statement: "The patent's 1400–1600 cm⁻¹ identity doublet needs a force constant k≈67 mdyne/Å; " +
      "the metal–metal envelope tops out at ≤5. A metal–metal bond cannot reach it.",
    provenance: "ir_signature.py · Herzberg, Spectra of Diatomic Molecules · Atkins, Physical Chemistry",
    doc: DOC + "patent-claim-tests.md",
    preset: { widget: "ir", inputs: { pwIrSym: "Rh", pwIrLineLo: 1429.53, pwIrLine: 1490.99 } },
  }),
  Object.freeze({
    id: "contaminant",
    title: "Best mundane match — carboxylate (plausible, not tight)",
    evidence_level: 2,
    leg: "positive",
    statement: "Scored against a cited contaminant library, the doublet's top match is an " +
      "ionic/bridging carboxylate (residual ≈0.59) — plausible but not a tight single-species match. " +
      "The unmatched (anomalous) branch was not triggered.",
    provenance: "ir_contaminant.py · Steill & Oomens 2009 · Deacon & Phillips 1980 · Grigorev 1963 (one-hop)",
    doc: DOC + "patent-claim-tests.md",
    result: { residual: 0.59, verdict: "plausible_match" },
    preset: { widget: "ir", inputs: { pwIrSym: "Rh", pwIrLineLo: 1429.53, pwIrLine: 1490.99 } },
  }),
  Object.freeze({
    id: "control-exp",
    title: "The decisive measurement (Level-3 prediction)",
    evidence_level: 3,
    leg: "prediction",
    statement: "¹³C labelling red-shifts a C–O carboxylate doublet by ≈−33 cm⁻¹, ¹⁸O by ≈−36; a " +
      "metal–metal bond shifts ≈0. With Raman/IR mutual exclusion and coverage scaling, 4 of 5 " +
      "controls distinguish surface-contaminant from metal-intrinsic origin. The lab designs this; " +
      "running it needs a real instrument.",
    provenance: "control_experiment.py · Langmuir 1918 · Raman/IR mutual-exclusion rule",
    doc: DOC + "ir-doublet-control-experiment.md",
    result: { c13_shift: -33, o18_shift: -36, decisive_count: 4 },
    // no preset in Phase 1 — the interactive isotope widget ships in Phase 2 with the 3D viewer.
  }),
  Object.freeze({
    id: "thermal",
    title: "Thermal stability — sintering-onset screen",
    evidence_level: 2,
    leg: "screen",
    statement: "For Ir a 1200 °C stability claim exceeds the Tammann onset (≈1086 °C) — anomalous " +
      "for that metal by the Hüttig/Tammann heuristic; per-element, not a blanket verdict.",
    provenance: "thermal_stability.py · Tammann/Hüttig sintering rule · CRC melting points",
    doc: DOC + "patent-claim-tests.md",
    result: { verdict: "exceeds_envelope" },
    preset: { widget: "thermal", inputs: { pwThSym: "Ir", pwThT: 1200 } },
  }),
  Object.freeze({
    id: "meissner",
    title: "Meissner Hc1 — implied λ / nₛ",
    evidence_level: 2,
    leg: "screen",
    statement: "An Hc1 ≈ 50 µT implies λ ≈ 1.8 µm and nₛ ≈ 8.6×10²⁴ m⁻³ — but Meissner screening needs " +
      "inter-unit phase coherence the isolated-monomer premise lacks; the claim is in tension with its own premise.",
    provenance: "meissner_field.py · Tinkham, Introduction to Superconductivity · CODATA 2018 Φ₀",
    doc: DOC + "patent-claim-tests.md",
    result: { verdict: "in_tension_with_isolation" },
    preset: { widget: "meissner", inputs: { pwMeB: 50 } },
  }),
];

export function renderResearch(el, onLoad) {
  if (!el) return;
  const banner =
    `<div class="research-banner">This is <strong>Obsidian Circuit's conducted research</strong> — ` +
    `for peer review and possible physical test runs. The base tools are <strong>sterile by default</strong>; ` +
    `loading a result populates the tools, it does not change the underlying model. ` +
    `Nothing here leaves your machine.</div>`;

  const card = (e) => {
    const badge = `<span class="research-badge lvl-${e.evidence_level}">Level ${e.evidence_level}/6 — ${LEVEL_LABEL[e.evidence_level]}</span>`;
    const load = e.preset
      ? `<button class="research-load" data-id="${e.id}">Load into models ▶</button>`
      : `<span class="research-noload">interactive viewer in Phase 2</span>`;
    const doc = `<a class="research-doc" href="${e.doc}" target="_blank" rel="noopener noreferrer">full note ↗</a>`;
    return `<div class="research-entry">
      <div class="research-head"><h3 class="research-title">${e.title}</h3>${badge}</div>
      <p class="research-statement">${e.statement}</p>
      <div class="research-prov">${e.provenance}</div>
      <div class="research-actions">${load}${doc}</div>
    </div>`;
  };

  // SAFE: every value interpolated below comes from the static, developer-authored RESEARCH
  // array above — no user or external input reaches innerHTML. Phase 3 will render
  // researcher-entered notes; THOSE must be escaped/textContent'd, not interpolated here.
  el.innerHTML = banner + RESEARCH.map(card).join("");
  el.querySelectorAll(".research-load").forEach((btn) => {
    btn.addEventListener("click", () => {
      const entry = RESEARCH.find((e) => e.id === btn.dataset.id);
      if (entry && typeof onLoad === "function") onLoad(entry);
    });
  });
}
