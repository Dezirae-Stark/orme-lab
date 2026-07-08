# IR-doublet Control Experiment — Implementation Plan

> Execute TDD, task-by-task. Spec: `docs/superpowers/specs/2026-07-08-ir-doublet-control-experiment-design.md`.

**Goal:** A computable Level-3 predictor that, for three controls, computes what H_contaminant vs H_intrinsic expect and flags decisiveness; plus a protocol doc.

## Global Constraints

- Deterministic; no time/RNG/order-dependent iteration; no network/telemetry.
- Commit as `Dezirae Stark <deziraestark69@gmail.com>`; never AI-identity trailers.
- Every physical relation cited (harmonic √μ; Raman/IR mutual exclusion; Beer–Lambert; Langmuir 1918). Isotope masses = CODATA specific-isotope values, not natural averages.
- `LAB_CEILING` (2) and all `min(level, LAB_CEILING)` sites unchanged. Only the prediction path reaches Level 3 via the new `PREDICTION_CEILING`.
- Neutral: both hypotheses predicted symmetrically; a discriminator must be able to return `decisive=False` (e.g. ¹⁵N label on a C–O bond → 0 shift → not decisive).

---

### Task 1 — `PREDICTION_CEILING` in `evidence.py`

Add after `LAB_CEILING`:
```python
#: Highest level the *prediction* path may assert. A concrete measurable prediction is
#: Level 3 by the ladder's own definition (see ``candidate_evidence_level``); screens and
#: verdicts keep the ``LAB_CEILING`` (2) clamp. Only ``control_experiment`` uses this.
PREDICTION_CEILING = EvidenceLevel.LABORATORY_PREDICTION
```
Test (`test_evidence.py`): `PREDICTION_CEILING == 3` and `LAB_CEILING == 2` (unchanged). Commit.

### Task 2 — isotope discriminator + `Prediction` dataclass

`control_experiment.py`. Specific-isotope masses (CODATA): ¹²C 12.000, ¹³C 13.00335, ¹⁴N 14.00307, ¹⁵N 15.00011, ¹⁶O 15.99491, ¹⁸O 17.99916.
```python
@dataclass(frozen=True)
class Prediction:
    measurement: str
    expected_under_contaminant: str
    expected_under_intrinsic: str
    decisive: bool
    evidence_level: EvidenceLevel
    note: str = ""

DETECTION_FLOOR_CM = 2.0  # conservative FTIR peak-position resolution

def _pred_level() -> EvidenceLevel:
    return EvidenceLevel(min(EvidenceLevel.LABORATORY_PREDICTION, PREDICTION_CEILING))

def _shift_for_bond(nu, bond, label) -> float:
    # bond = (sym_a, sym_b); label like "13C". 0.0 if the labelled element is not in the bond.
    elem, iso_mass = _LABEL[label]
    if elem not in bond:
        return 0.0
    m = [_ISO[bond[0]], _ISO[bond[1]]]
    for i, s in enumerate(bond):
        if s == elem:
            m[i] = iso_mass
    mu_new = _reduced_mass(*m)
    mu_old = _reduced_mass(_ISO[bond[0]], _ISO[bond[1]])
    return nu * (math.sqrt(mu_old / mu_new) - 1.0)

def predict_isotope_shift(lines_cm, label, contaminant_bond=("C","O"), intrinsic_bond=("Rh","Rh")) -> Prediction:
    hi = max(lines_cm)
    sc = _shift_for_bond(hi, contaminant_bond, label)
    si = _shift_for_bond(hi, intrinsic_bond, label)
    decisive = abs(sc - si) > DETECTION_FLOOR_CM
    ...
```
`_ISO` maps element symbol → dominant-isotope mass (C→12.000, O→15.99491, N→14.00307, Rh→102.905, Ir→192.217). `_LABEL`: "13C"→("C",13.00335), "18O"→("O",17.99916), "15N"→("N",15.00011).
Tests: ¹³C on C–O at 1490.99 → sc ≈ −33 (±1); ¹⁸O → ≈ −36; intrinsic Rh–Rh → 0; decisive True. ¹⁵N on C–O → sc == 0.0 → decisive False (neutral lever). evidence_level == 3. Commit.

### Task 3 — Raman/IR mutual-exclusion discriminator

`predict_raman_ir(centrosymmetric_intrinsic=True) -> Prediction`. H_contaminant (carboxylate C₂ᵥ): IR+Raman both active, strong Raman νsym expected. H_intrinsic centrosymmetric: symmetric M–M stretch IR-forbidden (mutual exclusion) → IR-observed doublet in tension; no IR/Raman coincidence. `decisive=True`. Cite mutual-exclusion rule. Test the activity/pattern strings + decisive + level. Commit.

### Task 4 — coverage/exposure scaling discriminator

`predict_coverage_scaling() -> Prediction`. H_contaminant: A ∝ exposure¹ (Beer–Lambert × Langmuir sub-saturation), saturates at monolayer, tracks surface area. H_intrinsic: A invariant to exposure/surface treatment. `decisive=True`; `note` states the softness (samples saturate/desorb). Cite Beer–Lambert + Langmuir 1918. Test. Commit.

### Task 5 — orchestrator

```python
@dataclass(frozen=True)
class ControlExperimentResult:
    predictions: tuple[Prediction, ...]
    decisive_count: int
    evidence_level: EvidenceLevel
    def explain(self) -> str: ...

def design_control_experiment(lines_cm, metal_symbol="Rh", light_bond=("C","O")) -> ControlExperimentResult:
    preds = (
        predict_isotope_shift(lines_cm, "13C", light_bond, (metal_symbol, metal_symbol)),
        predict_isotope_shift(lines_cm, "18O", light_bond, (metal_symbol, metal_symbol)),
        predict_isotope_shift(lines_cm, "15N", light_bond, (metal_symbol, metal_symbol)),
        predict_raman_ir(),
        predict_coverage_scaling(),
    )
    dc = sum(p.decisive for p in preds)
    return ControlExperimentResult(preds, dc, _pred_level())
```
Test: for patent lines + Rh, `decisive_count >= 3` (¹³C, ¹⁸O, Raman/IR, coverage decisive; ¹⁵N not); every `evidence_level == 3`; deterministic (call twice, identical). Commit.

### Task 6 — protocol doc + pointers

`docs/ir-doublet-control-experiment.md`: origin question; sample/reference set; per-discriminator decision table (H_contaminant vs H_intrinsic + how to read); the computed isotope numbers (run the module, paste actual); qualitative desorption/dosing; honest Level-3 framing; the Grigorev-primary "exhaustively attempted, inaccessible, stays one-hop" note. Add a one-line pointer from `docs/patent-claim-tests.md`. Full suite green. Commit. PR (no merge).
