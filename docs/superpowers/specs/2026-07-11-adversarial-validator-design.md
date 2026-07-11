# Design — Generalized adversarial validator

**Date:** 2026-07-11 · **Status:** approved (operator; forks: full branch table + route per
surviving mechanism). Generalizes `control_experiment.py` from the one IR-doublet case to a
per-candidate engine. Consumes #6 (mechanism tracks). Feeds the Hudson ledger.

## Purpose

For a candidate, automatically design the decisive experiments that separate a genuine
coherent (ORME-like) phase from the strongest mundane alternatives — **attacking the ordinary
explanations first**. Each test carries the operator's seven fields: claimed signature,
strongest mundane alternative(s), control sample, required instrument, expected result under
each hypothesis, rejection threshold, and the evidence-level change a confirmed result permits.
The claimed signature is **mechanism-specific**: the validator reads the candidate's
`surviving_mechanisms` (#6) and emits the decisive experiment for each surviving channel — so a
high-spin candidate (phonon pair-broken) is told to look for triplet/granular signatures (NMR
Knight shift, Shapiro steps), *not* the phonon isotope effect. This is a Level-3 laboratory
prediction (the lab designs; it cannot run the experiment).

## Architecture

New `src/orme_lab/validator.py`:

```python
@dataclass(frozen=True)
class AdversarialTest:
    measurement: str
    instrument: str
    claimed_signature: str                      # what the coherent-phase / mechanism hypothesis predicts
    mundane_alternatives: tuple[tuple[str, str], ...]  # (alternative, expected_result) — attacked first
    control_samples: tuple[str, ...]            # blinded controls to run alongside
    rejection_threshold: str                    # the result that KILLS the claim
    evidence_level_if_confirmed: int            # INITIAL_OBSERVATION(4) etc. a positive result would reach
    decisive: bool                              # separates the claim from ALL listed mundane alternatives?
    mechanism: str | None                       # the surviving mechanism this test targets (None = generic)
    evidence_level: int                         # of THIS design artifact = LABORATORY_PREDICTION(3)
    note: str

@dataclass(frozen=True)
class ValidationSuite:
    element: str
    surviving_mechanisms: tuple[str, ...]
    tests: tuple[AdversarialTest, ...]
    decisive_count: int
    def explain(self) -> str

def design_validation(record: CandidateRecord, *, observed_doublet=None) -> ValidationSuite
```

### Generic branch table (operator's, always emitted)

Each measurement vs the mundane alternatives {metallic filament / percolation, ionic
conduction, contact/measurement artifact}, with blinded controls {empty holder, substrate-only,
ordinary PGM salt, PGM nanoparticles, known diamagnet, coded duplicates}:

| measurement | instrument | coherent phase | metallic filament | ionic conduction |
|---|---|---|---|---|
| R(T,B,I) | 4-probe transport | sharp/structured transition, field/current-dependent | weak metallic T-dep, no transition | strong frequency/time dependence, polarization |
| Meissner | SQUID (ZFC/FC vs B) | field-dependent diamagnetic transition, demag-corrected | little bulk shielding | no diamagnetic screening |
| current reversal | I–V ± | symmetric voltage | symmetric | polarization/hysteresis (asymmetric) |
| AC sweep | impedance vs f | stable electronic response | stable | dispersive |
| heat capacity | calorimetry (ΔC/γT_c) | bulk anomaly if bulk fraction sufficient | absent | absent |
| subdivision | subdivide + re-measure | coherence effect (grain-size dep.) | path easily destroyed | geometry/moisture sensitive |

(Heat-capacity rejection is the #1-corrected form: no anomaly bounds the *bulk fraction*, does
not alone exclude filamentary/granular.)

### Mechanism-routed decisive tests (per surviving mechanism)

- **M_phonon** → isotope effect: T_c ∝ M^−α (α≈0.5); no shift ⇒ non-phononic. (Emitted ONLY if
  M_phonon survives — a high-spin candidate does NOT get this.)
- **M_granular_josephson** → Shapiro steps under RF: steps at V = nhf/2e (ac-Josephson).
- **M_triplet** → NMR Knight shift through T_c (unchanged for triplet) + H_c2 vs the Pauli limit.
- **M_spin_fluctuation** → non-Fermi-liquid resistivity + T_c peaking near a magnetic instability
  (pressure/field tuning).
- **M_excitonic_polaritonic** → coherent optical/THz response distinct from DC transport (flagged:
  close to the H12/H16 EM mundane alternative; the IR-doublet control belongs here).

### IR-doublet control

If `observed_doublet` is supplied, fold in the `control_experiment.py` predictions (the existing
Level-3 IR control) as `AdversarialTest`s in the excitonic/identity family — reuse, don't
reimplement.

## Determinism / evidence

Deterministic (fixed test order; no time/RNG). Each test's `evidence_level` =
LABORATORY_PREDICTION (3) via `PREDICTION_CEILING` (reuse `control_experiment._pred_level`);
`evidence_level_if_confirmed` = 4 (initial observation) for decisive transport/magnetic tests.
Additive — no pipeline change; consumes a `CandidateRecord`.

## Testing

`test_validator.py`: the six generic branch-table tests always present with the 7 fields;
mechanism routing — a high-spin record (survivors: spin_fluctuation/triplet/granular) yields the
triplet NMR + granular Shapiro tests and NOT the phonon isotope test; a closed-shell record
(phonon survivor) yields the isotope test and not the triplet one; `decisive` correct;
`evidence_level == 3` on every design, `evidence_level_if_confirmed` ≥ 3; determinism; the
IR-doublet fold-in when a doublet is supplied.

## Open items for writing-plans

- Whether `mundane_alternatives` is fixed-3 or per-measurement (default: per-measurement, since
  ionic vs filament expectations differ by measurement).
- Blinded-control set as a module constant (default: the six above).
