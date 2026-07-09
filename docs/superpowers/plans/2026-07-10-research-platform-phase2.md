# Research Platform Phase 2 — Implementation Plan

Spec: `docs/superpowers/specs/2026-07-10-research-platform-phase2-design.md`. Branch `research-phase2`.

**Constraints:** reuse imported THREE (no new egress); vibration.js THREE-free + parity-locked to `control_experiment.py`; predictions L3 / screens ≤2; sterile base (nothing animates unprompted); deterministic math (render clock drives motion only); commit as Dezirae, no AI trailers; new JS import `?v=__BUILD__`.

### Task 1 — `web/vibration.js` (THREE-free data + isotope math)
Export `ISO`, `LABEL` (specific-isotope masses, mirror of `control_experiment._ISO/_LABEL`), `SPECIES` (carboxylate C+2O + metal_dimer, atoms/bonds/modes/bond_atoms per spec — modes' `disp` are schematic in-phase/out-of-phase vectors, flagged), `reduced(a,b)`, `freqRatio(bond,label)` (= `sqrt(mu_old/mu_new)`, 1.0 if label null or element∉bond), `shiftCm(nu,bond,label)` (= `nu*(freqRatio-1)`). SAFE: pure data/math, no DOM/THREE.

### Task 2 — `tests/test_vibration_parity.py`
Parse vibration.js. Assert: `ISO` masses == `control_experiment._ISO`; `LABEL` isotope masses == `control_experiment._LABEL`; `shiftCm(1490.99,["C","O"],"13C")` ≈ `_shift_for_bond(1490.99,("C","O"),"13C")` (≈−33, abs 0.5); `"18O"` ≈ −36; `["Rh","Rh"]` under 13C == 0; `["C","O"]` under 15N == 0. (Recompute the JS formula in Python from the parsed masses, compare to the authority.)

### Task 3 — `index.html`: vibration controls + spectrum + readout
In the stage controls block (near `#eigenToggle`): add `<button class="chip" id="vibToggle" aria-pressed="false">vibration mode</button>` and a hidden `#vibControls` div: species `<select id="vibSpecies">` (carboxylate | metal–metal), mode `<select id="vibMode">`, isotope `<select id="vibIso">` (¹²C|¹³C|¹⁸O), metal `<select id="vibMetal">` (Rh|Ir). Below `#stage`: `<canvas id="irSpectrum"></canvas>` + `<div class="spec-caption" id="irSpecCap"></div>` and a `<div id="ceReadout" class="ce-readout"></div>` for the control-experiment predictions. Neutral prompt text until a species is chosen.

### Task 4 — `app.js`: vibration mode
- `import * as VIB from "./vibration.js?v=__BUILD__"`.
- `ELEMENT_COLOR` += `C:0x2b2f36, O:0xd66a4a, N:0x6aa6d6` (O reuses --ruled red, N reuses spin-dn blue).
- `moleculeGroup = new THREE.Group(); scene.add(moleculeGroup)`. `vib = {on:false, species:null, mode:null, iso:"12C", metal:"Rh", bases:[], meshes:[]}`.
- `buildMolecule()`: clearGroup(moleculeGroup); for metal_dimer use `vib.metal` for element+color; make atom spheres (scaled sphereGeo) + bond cylinders; store base positions + atom meshes + per-atom mode `disp`.
- In `loop()`: `if (vib.on && vib.species) { const t=performance.now()/1000; const ratio=VIB.freqRatio(bondOf(vib), VIB.LABEL[vib.iso]?VIB.iso:null...); for each atom mesh: pos = base + AMP*disp*Math.sin(2π*RATE*t*ratio); }` (ratio slows ¹³C; metal dimer ratio==1). Guard: motion only, no state mutation.
- `vibToggle` → toggle vib.on, show `#vibControls`, hide eigen meshes, `buildMolecule()`, `drawIrSpectrum()`, `renderCE()`. Selects rewire species/mode/iso/metal → rebuild + redraw.
- `drawIrSpectrum()`: 2D canvas like `drawPlasmon` — axis 1200–1700, draw the species' two mode lines (carboxylate: patent 1429.53/1490.99; metal: ν~275 off-scale note), ghost peak at `nu+VIB.shiftCm(...)` for carboxylate when iso≠12C; caption the shift.
- `renderCE()`: compact table — ¹³C/¹⁸O shift (via VIB.shiftCm), metal ≈0, static Raman/IR + coverage rows, "4/5 decisive" headline. textContent/escaped.
- `loadPreset` extension: `if (entry.preset.mode) { setTab("lab"); activate vib mode; set vibSpecies=species; rebuild; }` else the Phase-1 registry path.

### Task 5 — `styles.css`
`.vib-controls`, `#irSpectrum` (match `#plasmon` sizing), `.ce-readout` table styling, theme-consistent.

### Task 6 — `research.js`
`control-exp` entry: add `preset: { mode: "vibration", species: "carboxylate" }`. Remove the "interactive viewer in Phase 2" noload note (now it loads). Parity test unaffected (no `result` change).

### Task 7 — verify + PR
`node --check` all changed JS; Node ES-module smoke of vibration.js (exports, SPECIES shape, shiftCm values); `python3 -m pytest -q` green; opus review (reuse-THREE/no-egress, parity, neutrality, sterile-base, the animation guard). PR (no merge; touches web/ → deploy on merge). Honest note: browser E2E unavailable (no Chrome) — visual behavior needs the operator's eye on the deployed site.
