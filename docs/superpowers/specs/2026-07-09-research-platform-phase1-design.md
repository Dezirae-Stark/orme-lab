# Design — Research platform, Phase 1: research foundation (dossier + load + sterile base)

**Date:** 2026-07-09 · **Status:** approved for implementation planning
**Part of:** the "sterile base + loadable research dossier" platform (3 phases). This spec is
**Phase 1 only**; Phase 2 (3D vibrational viewer + spectral strip) and Phase 3 (record/export)
are separate specs.

## Purpose

Turn the static lab site into a two-mode research platform *foundation*:
1. a **sterile neutral base** — every interactive widget defaults to neutral/empty, so a
   researcher reproduces from zero with no preloaded conclusions; and
2. a **Research dossier add-on** — our conducted findings, structured and cited, rendered on
   a new tab for peer review, each with a **Load into models** action that injects that
   result's preset into the base widgets.

The spine is a structured research data layer (`web/research.js`) that the dossier renders,
the load buttons inject, and (in later phases) the 3D viewer reads and exports serialize.
Nothing preloads into the base; loading is always an explicit click. No egress.

## Non-goals (Phase 1)

- **No 3D vibrational viewer / spectral strip** — Phase 2.
- **No record/export or session snapshot** — Phase 3.
- **No live control-experiment widget** — the Level-3 predictions are *rendered* in the dossier
  (from `research.js`) with a link to the full doc, but the interactive isotope widget ships in
  Phase 2 alongside the viewer that animates the same shift (they are tightly coupled). Load
  targets in Phase 1 are the existing IR-doublet and contaminant widgets.
- No backend, no telemetry, no network egress — unchanged lab invariants.

## Architecture

```
web/
  research.js     # NEW — structured, cited research entries + load presets (the spine)
  index.html      # + a 4th "Research" tab + #research section; neutral widget defaults
  app.js          # + tab wiring for #research; renderResearch() mount; loadPreset()
  patent_tests.js # widgets default NEUTRAL (empty + placeholder); expose a load hook
  styles.css      # + .research-entry / dossier styles
tests/
  test_research_parity.py   # NEW — research.js stated results reproduce Python computations
```

### `research.js` — the structured spine

Exports `RESEARCH` — an ordered array of frozen entry objects:

```js
export const RESEARCH = [
  {
    id: "ir-negative",
    title: "IR doublet — metal–metal excluded",
    evidence_level: 1,                       // ladder level (labels via a shared map)
    leg: "negative",
    statement: "The patent doublet needs k≈67 mdyne/Å; the metal–metal envelope is ≤5.",
    provenance: "ir_signature.py; Herzberg; Atkins",
    doc: "https://github.com/Dezirae-Stark/orme-lab/blob/master/docs/patent-claim-tests.md",
    preset: { widget: "ir", inputs: { pwIrSym: "Rh", pwIrLineLo: 1429.53, pwIrLine: 1490.99 } },
  },
  { id: "contaminant", title: "Best mundane match — carboxylate (plausible)",
    evidence_level: 2, leg: "positive",
    statement: "Top match carboxylate (ionic/bridging), residual ≈0.59 — plausible, not tight.",
    provenance: "ir_contaminant.py; Steill&Oomens 2009; Deacon&Phillips 1980; Grigorev 1963 (one-hop)",
    doc: ".../docs/patent-claim-tests.md",
    preset: { widget: "contaminant", inputs: { pwIrSym: "Rh", pwIrLineLo: 1429.53, pwIrLine: 1490.99 } },
    result: { residual: 0.59, verdict: "plausible_match" },   // parity-checked vs Python
  },
  { id: "control-exp", title: "Decisive measurement (Level-3 prediction)",
    evidence_level: 3, leg: "prediction",
    statement: "¹³C ≈ −33 / ¹⁸O ≈ −36 cm⁻¹ if C–O; ≈0 if metal–metal. 4/5 controls decisive.",
    provenance: "control_experiment.py; Langmuir 1918; mutual-exclusion rule",
    doc: ".../docs/ir-doublet-control-experiment.md",
    result: { c13_shift: -33, o18_shift: -36, decisive_count: 4 },  // parity-checked vs Python
    // no preset in Phase 1 (interactive widget is Phase 2)
  },
];
```

`evidence_level` is rendered via a shared label map (Level 1/2/3 → "mathematical consistency"
/ "simulation candidate" / "laboratory prediction"), reusing the ladder vocabulary. Entries
are the single source the dossier renders and the load buttons consume.

### Research tab + dossier

New nav button `data-tab="research"` (after Loop) and a `#research` section. `app.js` gains
`renderResearch($("researchBody"))`: for each `RESEARCH` entry, a card with title, an evidence
badge (`Level N/6 — label`, reusing the badge style), the statement, provenance line, a
**Load into models ▶** button (only if `entry.preset`), and a **full note ↗** link to
`entry.doc` (opens the committed doc on GitHub — a plain link, no fetch). A short banner states
the neutrality contract: "This is Obsidian Circuit's conducted research. The Lab tab is sterile
by default; loading a result populates the tools — it does not change the underlying model."

### Load-into-models

`loadPreset(entry)` (in `app.js`): switches to the Lab tab, writes `entry.preset.inputs` into
the named DOM inputs, and dispatches `input`/`change` events so the existing widget update
handlers recompute and display. No new compute — it drives the existing widgets. A brief
"loaded: <title>" confirmation is shown; the base is otherwise unchanged.

### Sterile base (behaviour change, deliberate)

The patent widgets currently hard-default to the patent's own values (1429.53/1490.99, 1200 °C,
50 µT). Phase 1 makes them **neutral**: inputs start empty with a `placeholder` (e.g. "enter a
line, cm⁻¹"), and each widget's output shows a neutral prompt ("enter a doublet, or load a
result from Research") until values are entered or a preset is loaded. This is the sterility
requirement made real — the patent numbers now live only in `research.js` and arrive by
explicit load. Documented as an intentional change from current behaviour.

## Testing

- `test_research_parity.py`: for every `RESEARCH` entry carrying a `result`, import the Python
  authority and assert the stated numbers reproduce what the code computes — e.g. the
  `contaminant` entry's `residual`/`verdict` equal `screen_contaminants((1429.53,1490.99))`;
  the `control-exp` entry's `c13_shift`/`o18_shift` (±1) and `decisive_count` equal
  `design_control_experiment(...)`. This keeps the dossier from ever drifting from the code.
  Also assert every entry's `preset.inputs` reference real widget input ids and every
  `evidence_level ∈ {1,2,3}` with predictions ≤3 and screens ≤2.
- Parse `research.js` with the same regex-extraction approach already used in
  `test_patent_web_parity.py`.

## Invariants preserved

No network egress; no telemetry; base sterile by default (no preload); loading is explicit and
only drives existing widgets (no model change); Level-3 predictions labeled as predictions,
screens ≤2; every research entry cites its provenance and links its full committed doc; the
dossier's stated results are parity-locked to the Python computations (honest, non-drifting);
deterministic.

## Open items for the writing-plans step

- Exact neutral-prompt copy per widget, and whether thermal/Meissner widgets also go neutral in
  Phase 1 (default: yes — sterility applies to all patent widgets).
- Whether the Research tab lists a 4th entry pointing at the thermal/Meissner screens (default:
  include short entries for completeness, load-target = those widgets).
