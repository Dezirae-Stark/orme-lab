# Design — IR-doublet control experiment (`control_experiment.py`)

**Date:** 2026-07-08 · **Status:** approved for implementation planning
**Builds on:** the IR-doublet contaminant screen (`ir_contaminant.py`, `ir_signature.py`;
PRs #1–#3). Findings: `docs/patent-claim-tests.md`.

## Purpose

The contaminant screen concluded the patent's 1400–1600 cm⁻¹ doublet (DE3920144A1) is
*plausibly* an ionic/bridging carboxylate surface contaminant, with metal–metal bonding
excluded. But a reachability match cannot decide **origin** — whether the doublet is a
surface contaminant or intrinsic to the metal (the metal–metal / ORME reading). This module
turns that open question into the **decisive measurement**: for each of three controls it
computes what two competing hypotheses predict and flags where they *differ*.

The two hypotheses:
- **H_contaminant** — the doublet is a light-atom (C–O carboxylate) surface species.
- **H_intrinsic** — the doublet is intrinsic to the metal (metal–metal bond / high-spin ORME state).

Neutral by construction: the module predicts the outcome under *both* hypotheses and decides
neither. It produces the lab's first **Level-3 (LABORATORY_PREDICTION)** artifacts — the rung
`evidence.py` already defines and `candidate_evidence_level()` already returns ("tells you
which measurement would be decisive"), but which every screen so far has had clamped to
Level 2.

## Non-goals (YAGNI)

- No new EPW/DFT compute; closed-form predictions reusing the harmonic relation.
- No web widget (not requested this cycle); the protocol doc is the experimentalist surface.
- The lab **designs** the experiment (Level 3); it does not and cannot **run** it (Level 4+
  needs a real instrument). No claim crosses that line.
- No fabricated citations: every physical relation (harmonic √μ scaling; Raman/IR mutual-
  exclusion rule; Beer–Lambert; Langmuir) carries a source and is textbook-standard.

## Architecture

New `src/orme_lab/control_experiment.py`, reusing `_reduced_mass` from `ir_signature.py`.
(Implementation note: it defines its own `_ISO` table of **specific-isotope** masses rather
than reusing `ir_signature._MASS`, whose natural-abundance averages would be wrong for an
isotopologue comparison.) A frozen `Prediction` dataclass per discriminator:
`measurement`, `expected_under_contaminant`, `expected_under_intrinsic`, `decisive` (bool —
do the two differ beyond the measurement's resolution?), `evidence_level`, `note`. An
orchestrator `design_control_experiment(lines_cm, light_mu, metal_symbol) →
ControlExperimentResult` runs all three and aggregates (list of predictions + a headline
`decisive_count`). One small change to `evidence.py` (below). Tests + a protocol doc.

```
src/orme_lab/
  control_experiment.py   # NEW — the three discriminators + orchestrator
  evidence.py             # + PREDICTION_CEILING (Level 3); LAB_CEILING (2) unchanged
tests/
  test_control_experiment.py   # NEW
  test_evidence.py             # + PREDICTION_CEILING behaviour
docs/
  ir-doublet-control-experiment.md  # NEW — decisive-experiment protocol + decision table
  patent-claim-tests.md             # + short pointer to the control-experiment doc
```

## The three computed discriminators

### 1. Isotopic substitution (headline; fully computable)

ν ∝ 1/√μ (harmonic diatomic, `wavenumber` in `ir_signature.py`). Substituting ¹³C or ¹⁸O in
a C–O carboxylate raises μ → red-shifts the doublet by a **computed** Δν; substituting C/O
leaves a metal–metal bond's μ unchanged → ~0 shift.

`predict_isotope_shift(lines_cm, label) → Prediction`, `label ∈ {"13C", "18O", "15N"}`.
For a C–O bond (μ = 6.856 for ¹²C¹⁶O): ¹³C → μ(¹³C¹⁶O) = _reduced_mass(13.00335, 15.99491);
¹⁸O → μ(¹²C¹⁸O) = _reduced_mass(12.011, 17.99916). Shifted line = ν·√(μ_old/μ_new).
Expected magnitudes for the patent's upper line (~1490): ¹³C ≈ −33 cm⁻¹, ¹⁸O ≈ −36 cm⁻¹;
H_intrinsic ≈ 0. `decisive = |shift_contaminant − shift_intrinsic| > DETECTION_FLOOR`
(DETECTION_FLOOR ≈ 2 cm⁻¹, a conservative FTIR peak-position resolution).
Isotope masses are CODATA/CRC standard, cited in a module table.

### 2. Raman/IR mutual exclusion (symmetry-grounded)

A centrosymmetric metal–metal homodimer (point group with an inversion centre) has a
Raman-active, **IR-forbidden** symmetric stretch (mutual-exclusion rule). A non-centrosymmetric
carboxylate (C₂ᵥ) is active in both IR and Raman (νsym Raman-strong ~1430–1470, νasym
IR-strong). `predict_raman_ir(assignment) → Prediction` returns the expected activity pattern:
- H_contaminant (carboxylate): band appears in IR **and** Raman; a strong Raman νsym is expected.
- H_intrinsic (centrosymmetric M–M): the symmetric stretch is IR-forbidden — an *IR-observed*
  doublet is already in tension with a centrosymmetric M–M assignment; Raman would show no
  coincidence with the IR bands.
Output is structural (activity booleans + expected pattern string), not a single number.
`decisive = True` (the predicted Raman coincidence patterns differ). Cited to the mutual-
exclusion rule (Atkins/Harris standard spectroscopy).

### 3. Coverage / exposure scaling (Beer–Lambert + Langmuir)

Integrated band area A ∝ N absorbers (Beer–Lambert). A surface contaminant's N scales ~linearly
with exposure below saturation (Langmuir isotherm) and with surface-area/volume; an intrinsic
bulk mode scales with sample mass but is invariant to surface treatment/exposure.
`predict_coverage_scaling(...) → Prediction`:
- H_contaminant: A ∝ exposure¹ (sub-saturation), saturating at monolayer; tracks surface area.
- H_intrinsic: A invariant to exposure/surface treatment.
`decisive = True` (linear-vs-flat response). Cited to Beer–Lambert and Langmuir (1918). This is
the softest of the three — real samples saturate and desorb — stated plainly in output + doc.

## Evidence-ladder change (operator-authorized)

Add to `evidence.py`:
```python
#: Highest level the *prediction* path may assert. A concrete measurable prediction is
#: Level 3 by the ladder's own definition; screens/verdicts keep the LAB_CEILING (2) clamp.
PREDICTION_CEILING = EvidenceLevel.LABORATORY_PREDICTION
```
`control_experiment` clamps its `evidence_level` to `min(LABORATORY_PREDICTION,
PREDICTION_CEILING)` = 3. **No existing screen changes**; `LAB_CEILING` and every
`min(level, LAB_CEILING)` call site stay exactly as they are. This is the sole, narrow,
documented ladder change, confined to the prediction path — the operator authorized it.

## Protocol document

`docs/ir-doublet-control-experiment.md` — experimentalist-facing decisive-experiment spec:
the origin question; the sample + reference set (ORME sample; clean PGM reference;
deliberately carboxylate-dosed reference; solvent/substrate blank); a decision table (per
discriminator: H_contaminant vs H_intrinsic outcome + how to read the result), including the
computed isotope numbers and the qualitative desorption/dosing controls; honest framing (the
lab designs at Level 3, cannot run it; what a positive/negative result means for the patent).
Also records that the Grigorev 1963 primary was exhaustively attempted and is digitally
inaccessible — the chelating citation stays one-hop.

## Testing

`test_control_experiment.py`: isotope math (¹³C carboxylate ≈ −33 cm⁻¹; metal–metal 0; a
metal-mass input gives ~0 shift so the discriminator can *fail* to be decisive — the neutral
lever); symmetry classification (centrosymmetric → mutual exclusion; C₂ᵥ → both active);
coverage linear-vs-flat; orchestrator `decisive_count`; `evidence_level ==
LABORATORY_PREDICTION`; determinism. `test_evidence.py`: `PREDICTION_CEILING` == 3 and that
`LAB_CEILING` is unchanged (== 2).

## Invariants preserved

Deterministic (no time/RNG/order-dependent iteration); no network egress; no telemetry; every
physical relation cited (harmonic √μ; mutual-exclusion rule; Beer–Lambert; Langmuir 1918);
neutral (both hypotheses predicted symmetrically; the isotope discriminator can return
non-decisive on a metal-mass input, so the design can fail to discriminate); `LAB_CEILING`
clamp on screens untouched — only the prediction path reaches Level 3.

## Open items for the writing-plans step

- Exact `DETECTION_FLOOR` value (default 2.0 cm⁻¹) and isotope-mass constants.
- Whether `design_control_experiment` takes the light-atom μ explicitly or derives it from the
  screen's top assignment (default: explicit `light_mu` argument, defaulting to C–O 6.856).
