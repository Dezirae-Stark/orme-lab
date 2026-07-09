# Design — Research platform Phase 2: 3D vibrational viewer + spectral strip + control-experiment widget

**Date:** 2026-07-10 · **Status:** approved for implementation planning
**Part of:** the sterile-base + loadable-research platform. Phase 1 (dossier + load + sterile base)
merged as PR #5. This is **Phase 2**; Phase 3 (record/export) is a separate spec.

## Purpose

Make the site's marquee 3D surface *reflect our IR results*: a new **Vibration** mode on the
existing `#stage` that renders the two hypotheses the isotope test decides between — a
**carboxylate C–O group** (H_contaminant) and a **metal–metal dimer** (H_intrinsic) — animates
their normal modes, and lets an isotope toggle (¹²C | ¹³C | ¹⁸O) shift the carboxylate's motion
and frequency while leaving the metal–metal dimer untouched. A linked 2D **spectral strip**
shows the doublet and the isotope-shifted ghost peak; a compact **control-experiment readout**
surfaces the Level-3 predictions interactively. This is the visual, interactive form of the
`control_experiment.py` discriminator — the same physics, decided by the viewer's own animation.

## Non-goals (Phase 2)

- No new 3D library — reuse the already-imported THREE (importmap `"three"`), no new egress.
- No nitrate/carbonate species — the head-to-head (carboxylate vs metal–metal) only.
- No record/export — Phase 3.
- The normal-mode displacement vectors are **schematic** (in-phase vs out-of-phase illustration),
  not a normal-coordinate analysis — flagged in-code and in the caption, like `eigenstate.js`
  flags its model potential. Stays a visualization of a Level-2/3 result; asserts no new physics.

## Architecture (follows the eigenstate.js pattern)

`web/vibration.js` is **THREE-free**: it exports species geometry + normal-mode eigenvectors +
the isotope-shift math (a direct mirror of `control_experiment.py`). `app.js` builds the THREE
meshes and animates in the existing `loop()`. This keeps the physics/math pure and parity-testable.

```
web/
  vibration.js    # NEW — species data, mode vectors, isotope math (THREE-free, parity-locked)
  app.js          # + vibration stage-mode: build molecule meshes, animate, isotope toggle, spectral strip
  index.html      # + vibration mode toggle + species/mode/isotope controls + #irSpectrum canvas + readout
  research.js     # control-exp entry gains preset {mode:"vibration", species:"carboxylate"}; loadPreset extended
  styles.css      # + vibration controls + spectrum styles
tests/
  test_vibration_parity.py   # NEW — JS isotope masses + shift math reproduce control_experiment.py
```

### `vibration.js` (THREE-free)

```js
export const ISO = { C: 12.0, O: 15.994915, N: 14.003074, Rh: 102.905, Ir: 192.217 };
export const LABEL = { "12C": null, "13C": ["C", 13.003355], "18O": ["O", 17.99916], "15N": ["N", 15.000109] };
export const SPECIES = {
  carboxylate: {
    label: "carboxylate COO⁻", bond_atoms: ["C", "O"],
    atoms: [ {el:"C",pos:[0,0,0]}, {el:"O",pos:[-1.1,0.75,0]}, {el:"O",pos:[1.1,0.75,0]} ],
    bonds: [[0,1],[0,2]],
    modes: {
      asym: { label:"νasym (out-of-phase)", disp:[[0,0,0],[-1,0,0],[1,0,0]] },   // patent upper line
      sym:  { label:"νsym (in-phase)",     disp:[[0,-0.6,0],[0.5,0.5,0],[-0.5,0.5,0]] }, // patent lower line
    },
  },
  metal_dimer: {
    label: "metal–metal dimer", bond_atoms: ["Rh","Rh"],  // metal set by app from selected symbol
    atoms: [ {el:"Rh",pos:[-1.3,0,0]}, {el:"Rh",pos:[1.3,0,0]} ], bonds: [[0,1]],
    modes: { stretch: { label:"ν(M–M)", disp:[[-1,0,0],[1,0,0]] } },
  },
};
const reduced = (a,b) => (a*b)/(a+b);
// Frequency ratio nu'/nu = sqrt(mu_old/mu_new) under isotope `label`; 1.0 if label absent from bond.
export function freqRatio(bond, label) { /* mirror of control_experiment._shift_for_bond ratio */ }
export function shiftCm(nu, bond, label) { return nu * (freqRatio(bond, label) - 1); }
```

`freqRatio`/`shiftCm` are the parity-locked mirror of `control_experiment._shift_for_bond`.

### 3D content (app.js "vibration" stage mode)

A stage-mode toggle (`#vibToggle`, alongside `eigenToggle`) reuses the camera/renderer/OrbitControls.
When active: `clearGroup(moleculeGroup)`, build atom spheres (element-colored, reusing `sphereGeo`)
+ bond cylinders from `SPECIES[sel]`; the eigenstate meshes hide. In `loop()`, when in vibration
mode, displace each atom: `pos = base + AMP · disp · sin(2π · RATE · t · ratio)`, where
`ratio = freqRatio(bond, isotope)` — so ¹³C (ratio<1) visibly **slows** the carboxylate and a
C/O label on the metal dimer leaves `ratio == 1` (unchanged). Controls: species select
(carboxylate | metal–metal), mode select (νsym | νasym | stretch), isotope select (¹²C | ¹³C | ¹⁸O),
metal symbol (Rh | Ir) for the dimer.

### Linked spectral strip

New 2D-canvas `#irSpectrum` beneath the stage, drawn like the existing `drawPlasmon`: axis
1200–1700 cm⁻¹; the current doublet as two peaks; when an isotope is active, a **ghost peak** at
`nu + shiftCm(...)` for the carboxylate (no ghost for the metal dimer — the label doesn't apply).
Caption states the shift (e.g. "¹³C → −33 cm⁻¹").

### Interactive control-experiment readout

A compact panel driven by `vibration.js`: for the current doublet + metal + centrosymmetry, show
the isotope predictions (¹³C/¹⁸O shift vs metal ≈0) computed live, plus the static Raman/IR and
coverage rows and the `4/5 decisive` headline — the interactive form of `design_control_experiment`.

### Research load + neutrality

`research.js` `control-exp` entry gains `preset: { mode:"vibration", species:"carboxylate" }`.
`loadPreset` is extended: if `preset.mode` is present it routes to the **Lab** tab (the stage lives
there), activates vibration mode, and selects the species; if `preset.inputs` is present it routes to
Registry (unchanged Phase-1 behavior). **Sterile base preserved:** vibration mode opens on a neutral
prompt ("select a species, or load a result") — no molecule animates unprompted.

## Testing

`test_vibration_parity.py`: parse `vibration.js`; assert `ISO`/`LABEL` masses equal
`control_experiment._ISO`/`_LABEL`; and that `shiftCm(1490.99, ["C","O"], "13C") ≈ −33`,
`"18O" ≈ −36`, and metal–metal or ¹⁵N-on-C–O `== 0` — i.e. the JS mirror reproduces the Python
authority (`_shift_for_bond`). Mutation-checkable (change a JS mass → test fails). Plus `node --check`
and a Node ES-module smoke test of `vibration.js` exports + a `buildMolecule`-shape check.

## Invariants preserved

Reuse the already-imported THREE (no new dependency/egress); no telemetry; predictions labeled
Level 3, screens ≤2; deterministic math (the animation uses the render clock for motion only — a
display concern, not a correctness path; no RNG); the viewer visualizes both hypotheses and decides
neither; sterile base (nothing animates until a species is selected or a result loaded); JS isotope
math parity-locked to `control_experiment.py`.

## Open items for the writing-plans step

- `AMP`/`RATE` visual constants; element colors (reuse any existing palette).
- Whether the control-experiment readout is its own panel or folded under the stage caption
  (default: a compact panel beside the vibration controls).
- Exact metal default for the dimer (default Rh, switchable to Ir).
