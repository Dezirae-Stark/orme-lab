# Design — Mechanism-specific pairing tracks (#6)

**Date:** 2026-07-11 · **Status:** approved (operator review #6; forks: crediting REQUIRES a
surviving mechanism; implement all five tracks with honest surrogates). Consumes #7 (structure).

## Purpose

Replace the single synthetic SC score as the *crediting* basis with **independent pairing-
mechanism tracks**, each with its own necessary conditions and rejection rules. A candidate is
credited as an SC lead only if **≥1 complete mechanism survives end-to-end** — partial strengths
are never combined into one score. Crucially, this separates mechanisms that a large local moment
*kills* (singlet phonon) from those it *enables* (spin-fluctuation, triplet), resolving the
high-spin ⊥ singlet-EPW tension the lab hit empirically (Tier-2 Ir moment collapse).

## Architecture

New `src/orme_lab/mechanisms.py`. Each track is a pure evaluator over the candidate's already-
computed descriptors (coupling, carrier_proxy, structural_stability, field_suppression,
spin_polarization [local-moment proxy], observable_signal, em_coherence_score, n_atoms). All
thresholds are documented module constants (assumptions, not tuned to pass favourites).

```python
class Mechanism(str, Enum):
    PHONON = "M_phonon"
    SPIN_FLUCTUATION = "M_spin_fluctuation"
    TRIPLET = "M_triplet"
    EXCITONIC_POLARITONIC = "M_excitonic_polaritonic"
    GRANULAR_JOSEPHSON = "M_granular_josephson"

@dataclass(frozen=True)
class MechanismResult:
    mechanism: str
    survives: bool
    plausibility: float          # 0 unless every necessary condition passes
    is_surrogate: bool           # True for the less-developed tracks (honest label)
    rejection: str               # "" if it survives; else why it was rejected
    note: str

def evaluate_mechanisms(*, coupling, carrier_proxy, structural_stability, field_suppression,
                        spin_polarization, observable_signal, em_coherence_score, n_atoms,
                        thresholds) -> tuple[MechanismResult, ...]
```

### The five tracks (necessary conditions → rejection)

- **M_phonon** (conventional electron–phonon, singlet BCS; NOT a surrogate — reuses the toy gate
  inputs). Necessary: coupling, carrier, stability above floors. **Magnetic pair-breaking**: a
  static local moment pair-breaks singlet pairing (Abrikosov–Gor'kov). Graded penalty
  `plausibility ×= max(0, 1 − spin_polarization/PB_MOMENT_MAX)`; and **hard reject** when
  `spin_polarization ≥ PB_MOMENT_MAX` (= 0.5) — a high-spin candidate has NO phonon-singlet
  mechanism. This is the load-bearing correction.
- **M_spin_fluctuation** (magnetically-mediated; SURROGATE, susceptibility/Hubbard-style).
  Necessary: a local moment PRESENT (`spin_polarization ≥ MOMENT_MIN`) AND coupling (neighbours to
  mediate). Plausibility ∝ spin_polarization·coupling. Rejected if no moment (nothing to mediate)
  or no coupling. **This is the honest home for the high-spin premise** — the candidates phonon
  rejects route here.
- **M_triplet** (odd-parity spin-triplet; SURROGATE). Necessary: moment-compatible
  (`spin_polarization ≥ MOMENT_MIN`; triplet is NOT pair-broken by moments) AND coupling; PGMs are
  heavy → strong spin–orbit assumed (stated). Plausibility ∝ spin_polarization·coupling. Rejected
  if no coupling.
- **M_excitonic_polaritonic** (SURROGATE; repurposes the H12/H16 EM channel as a speculative
  pairing glue — flagged, since EM coherence is normally the *mundane alternative*). Necessary:
  `em_coherence_score` present and ≥ strong-coupling floor AND coupling. Rejected if EM not
  computed (`None`) or below the floor.
- **M_granular_josephson** (structural; DIRECT_PRECEDENT, granular-josephson prior-art). Derive
  `E_J/E_C` from EXISTING state, no free knob: `E_J ∝ coupling` (inter-grain contact), `E_C ∝
  1/n_atoms` (grain self-capacitance ∝ grain size), ratio `= EJEC_SCALE · coupling · n_atoms`.
  Sharp threshold: survives iff `n_atoms ≥ 2` AND `ratio ≥ 1.0` (phase-locked network); rejected
  below (phase-incoherent). Threshold/form documented, not tuned.

### Integration into `pipeline.evaluate_candidate`

Compute the mechanisms from the descriptors already in scope. Add `CandidateRecord` fields:
`surviving_mechanisms: tuple[str, ...]` and `mechanism_summary: str`. **Tighten crediting**:
```python
credited = (id_result.established and plaus.all_passed and plaus.score > 0.0
            and len(surviving_mechanisms) > 0)
```
No surviving mechanism → not credited even with identity + passing proxies (the operator's
"no synthetic score credits SC unless one complete mechanism survives"). The mechanism fields are
composites of gate ∧ off-gate inputs → **in neither closure set** (like `credited_sc_lead`); the
closure golden is unchanged (new fields aren't classified). The generic `sc_plausibility` gate is
untouched — it remains the necessary-condition floor; mechanisms are the crediting basis on top.

## Testing

`test_mechanisms.py`: each track's survive/reject on hand-set descriptors; **the load-bearing
test** — a large-moment (high-spin) descriptor set REJECTS M_phonon (pair-breaking) but SURVIVES
via M_spin_fluctuation/M_triplet; a low-moment well-coupled set survives M_phonon; granular gate
is a sharp threshold (n=1 or low ratio rejected, n≥2 high ratio survives); excitonic rejected when
em is None. `test_identity.py`/pipeline: a candidate with identity + passing proxies but NO
surviving mechanism → `credited_sc_lead` False; with a surviving mechanism → True. Determinism.

## Invariants

Deterministic (no time/RNG); every threshold a documented constant; surrogates explicitly labelled
(`is_surrogate`); generic SC gate and closure golden untouched; evidence clamp unchanged; crediting
strictly tightened (never loosened). No fabricated physics — each track cites its basis (phonon
pair-breaking: Abrikosov–Gor'kov; granular: Abeles 1977 / Ambegaokar–Baratoff per prior-art;
spin-fluctuation/triplet: labelled surrogates, not claimed as computed).

## Open items for writing-plans

- Exact constant values: `PB_MOMENT_MAX=0.5`, `MOMENT_MIN=0.2`, `EM_STRONG_FLOOR`, `EJEC_SCALE`.
- Whether `mechanism_summary` lists survivors + the top rejection, or all five verdicts (default:
  survivors + rejections, compact).
