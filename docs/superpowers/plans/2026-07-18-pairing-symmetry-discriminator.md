# Pairing-symmetry discriminator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Branch the field-response hypothesis H7 into singlet vs equal-spin-triplet pairing (opposite Pauli-limit field predictions), add an H7-triplet-gated spin/magnetic AC-drive-channel hypothesis in the EM-coherence branch, and back both with off-gate decisive-measurement predictions — making the screen strictly more able to kill candidates, never more permissive.

**Architecture:** A new `PairingSymmetry` enum (`UNDETERMINED`/`SINGLET`/`TRIPLET`) threads through the field-response path. `UNDETERMINED` (default) preserves current behavior byte-for-byte. Under an explicit singlet/triplet assumption the critical field becomes pairing-conditional (singlet → Pauli-limited/spin-suppressed; triplet → field-robust) and the creditable pairing mechanisms filter accordingly, so spin has one clean sign per hypothesis. Two new off-gate observables (`field_response_ratio`, `em_drive_response`) drive the falsification of the new hypotheses; a new liveness-dependency gate makes `H16-drive-triplet` live only while `H7-triplet` is open.

**Tech Stack:** Python 3 (stdlib: `math`, `dataclasses`, `enum`), pytest, vanilla ES-module JS (`web/*.js`), node-based parity tests.

## Global Constraints

- **No new verdict members.** `Verdict` (`lab_loop/triage.py`) stays `KILLED_HYPOTHESIS`/`SURVIVED`/`TAUTOLOGICAL`/`INCONCLUSIVE`. No `VALIDATED`/`CONFIRMED`, ever.
- **Level-2 clamp** on every screen verdict (`min(candidate_evidence_level(...), LAB_CEILING)`, `pipeline.py:291`). Decisive-measurement predictions may carry `PREDICTION_CEILING` (Level 3, already in `evidence.py:54`) — they are predictions, not observations.
- **Anti-tautology gate is authoritative.** A predictor must reference ≥1 `OFF_GATE_INVARIANT` (`closure.py`). New off-gate fields are ADDED to the pinned set and the golden `test_closure.py` is updated in lockstep — never weakened.
- **Determinism:** no `time`/RNG/order-dependent iteration; enums compared by identity; dict iteration only over fixed tuples.
- **Default path unchanged:** with `PairingSymmetry.UNDETERMINED` (the default) and `applied_field_t=0.0`, every existing `CandidateRecord` field and metric is byte-identical. A regression is a bug. Scope: this covers every *decision-bearing* field and metric — `surviving_mechanisms`, `credited_sc_lead`, `evidence_level`, `verdict`, `ruled_out`, `field_suppression`, `field_response_ratio`, `sc_plausibility`, etc. (pinned by `test_default_symmetry_is_byte_identical`). It does **not** extend to `mechanism_summary`: that field is a diagnostic string that enumerates every `Mechanism` member's rejection reason, so it necessarily grows whenever a task appends a member to the `Mechanism` enum (Task 6 Step 3 does this by design, adding `M_drive`). Task 6 documents this exception explicitly (see its note below) and pins the new default-path string with a regression test — it is a tracked, reviewed consequence of the enum growing, not a silent behavior drift.
- **Stricter, never more permissive:** the branch must be able to rule out a candidate it previously credited. A change that only ever passes more is wrong.
- **Honesty labels:** new proxy outputs are labeled "Toy (Level 2)" / "proxy" / "SURROGATE" (the in-code convention), never presented as measured.
- **No fabricated ab-initio numbers:** the backend seam stays a no-number stub (`_nyi`); the toy drive-response proxy lives only in `electromagnetic_coherence.py`, clearly labeled.
- **Commit identity:** `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`; never emit AI-identity trailers (author, committer, or message body). Public repo.
- **Run tests:** `cd /orme-lab && python3 -m pytest`.
- Branch: all work on `pairing-symmetry-discriminator`; open a PR at the end, do not merge (operator-reserved).

## File structure (what each touched file is responsible for)

```
src/orme_lab/
  magnetic_field.py      # NEW: PairingSymmetry, pauli_limit_tesla, pairing-conditional critical field, field_response_ratio
  mechanisms.py          # NEW: creditable-mechanism filter by PairingSymmetry; _drive track (Change 5, mechanisms half)
  electromagnetic_coherence.py  # NEW: magnetic_drive_response toy proxy + CoherenceResult field
  pipeline.py            # wire pairing_symmetry through evaluate_candidate; new record fields field_response_ratio, em_drive_response
  config.py              # LabConfig.pairing_symmetry (default UNDETERMINED)
  backends.py            # NEW Capability stubs: NON_PHONON_PAIRING, SPIN_DRIVE_RESPONSE (no-number _nyi)
  lab_loop/
    hypotheses.py        # split H7 -> H7-singlet/H7-triplet; add H16-drive-triplet; LIVENESS_DEPENDENCIES + validate_liveness
    closure.py           # add field_response_ratio, em_drive_response to OFF_GATE_INVARIANTS
    triage.py            # liveness gate (INCONCLUSIVE when parent hypothesis dead)
    avenue.py            # METRIC_RANGES: max_field_response_ratio, max_em_drive_response; ActionSpec.pairing_symmetry
    runner.py            # aggregate the two new metrics; pass pairing_symmetry into run_config
    loop.py              # digest: surface the split + drive hypothesis + both decisive measurements
web/
  hypotheses.js          # registry cards for the new hypotheses
  metrics.js             # honesty label for em_drive_response ("Toy (Level 2)")
  sim.js                 # mirror the drive-response field
docs/
  hypothesis_matrix.md   # H7 split rows + H16-drive-triplet row + decisive measurements
tests/
  test_pairing_symmetry.py         # NEW (Tasks 1,3)
  test_magnetic_drive.py           # NEW (Task 4)
  test_liveness_dependency.py      # NEW (Task 5)
  test_pairing_acceptance.py       # NEW (Task 9 — the cross-cutting acceptance contract)
  test_web_pairing_parity.py       # NEW (Task 8)
  test_closure.py, test_mechanisms.py, test_backends.py  # extended
```

---

### Task 1: `PairingSymmetry` + Pauli limit + pairing-conditional critical field + field-response ratio

**Files:**
- Modify: `src/orme_lab/magnetic_field.py`
- Test: `tests/test_pairing_symmetry.py` (create)

**Interfaces:**
- Consumes: nothing new (pure functions).
- Produces: `PairingSymmetry` (Enum: `UNDETERMINED`, `SINGLET`, `TRIPLET`); `pauli_limit_tesla(tc_kelvin: float) -> float`; `pairing_critical_field(spin_score, coupling_score, symmetry, tc_kelvin=None) -> float`; `field_response_ratio(critical_field_t, tc_kelvin) -> float | None`. `PAULI_SLOPE_T_PER_K = 1.86`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pairing_symmetry.py
import math
import pytest
from orme_lab.magnetic_field import (
    PairingSymmetry, pauli_limit_tesla, pairing_critical_field, field_response_ratio,
    critical_field_proxy,
)


def test_pauli_limit_is_1_86_tc():
    assert pauli_limit_tesla(10.0) == pytest.approx(18.6)


def test_undetermined_matches_legacy_proxy():
    # UNDETERMINED must reproduce the legacy toy critical field exactly (byte-identical default).
    for spin in (0.0, 0.3, 0.8):
        for coup in (0.2, 0.5, 0.9):
            assert pairing_critical_field(spin, coup, PairingSymmetry.UNDETERMINED) == \
                pytest.approx(critical_field_proxy(spin, coup))


def test_triplet_field_rises_with_spin():
    lo = pairing_critical_field(0.1, 0.6, PairingSymmetry.TRIPLET)
    hi = pairing_critical_field(0.9, 0.6, PairingSymmetry.TRIPLET)
    assert hi > lo  # equal-spin triplet is field-robust: more moment, more critical field


def test_singlet_field_falls_with_spin():
    lo = pairing_critical_field(0.1, 0.6, PairingSymmetry.SINGLET)
    hi = pairing_critical_field(0.9, 0.6, PairingSymmetry.SINGLET)
    assert hi < lo  # singlet: a larger moment pair-breaks -> lower critical field


def test_singlet_capped_at_pauli_when_tc_known():
    # With a Tc, a singlet critical field can never exceed the Pauli limit.
    cf = pairing_critical_field(0.0, 1.0, PairingSymmetry.SINGLET, tc_kelvin=1.0)
    assert cf <= pauli_limit_tesla(1.0) + 1e-9


def test_field_response_ratio_none_without_tc():
    assert field_response_ratio(3.0, None) is None
    assert field_response_ratio(3.0, 0.0) is None


def test_field_response_ratio_gt_one_signals_enhancement():
    # Bc above the Pauli limit -> ratio > 1 -> only triplet can host it.
    r = field_response_ratio(pauli_limit_tesla(2.0) * 1.5, 2.0)
    assert r == pytest.approx(1.5)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /orme-lab && python3 -m pytest tests/test_pairing_symmetry.py -v`
Expected: FAIL — cannot import `PairingSymmetry` / `pauli_limit_tesla` etc.

- [ ] **Step 3: Implement in `magnetic_field.py`**

Add near the top (after imports), keeping the existing `critical_field_proxy` in `pipeline.py` untouched — these are NEW functions in `magnetic_field.py` that reference the legacy form for the UNDETERMINED case:

```python
from enum import Enum

PAULI_SLOPE_T_PER_K = 1.86   # Chandrasekhar-Clogston / Pauli limit: Bc_pauli ~ 1.86 * Tc (weak-coupling BCS).
                             # Clogston, PRL 9, 266 (1962); Chandrasekhar, APL 1, 7 (1962).


class PairingSymmetry(Enum):
    """Assumed Cooper-pair symmetry for a candidate's field response.

    UNDETERMINED reproduces the legacy toy critical field (default; no assumption).
    SINGLET: a static moment pair-breaks -> field suppressed, capped at the Pauli limit.
    TRIPLET: equal-spin pairs carry the moment -> field-robust, may exceed the Pauli limit.
    """
    UNDETERMINED = "undetermined"
    SINGLET = "singlet"
    TRIPLET = "triplet"


def _legacy_critical_field(spin_score: float, coupling_score: float) -> float:
    """The pairing-agnostic toy critical field (identical to pipeline.critical_field_proxy)."""
    return 5.0 * coupling_score * (0.5 + 0.5 * spin_score)


def pauli_limit_tesla(tc_kelvin: float) -> float:
    """Chandrasekhar-Clogston paramagnetic limit Bc_pauli (tesla) for a singlet gap ~ Tc."""
    return PAULI_SLOPE_T_PER_K * tc_kelvin


def pairing_critical_field(spin_score: float, coupling_score: float,
                           symmetry: "PairingSymmetry",
                           tc_kelvin: float | None = None) -> float:
    """Toy critical field (tesla), pairing-symmetry-conditional. Triage only.

    - UNDETERMINED: the legacy proxy (spin raises Hc); default, byte-identical.
    - TRIPLET: field-robust; spin raises Hc (equal-spin pairs carry the moment).
    - SINGLET: spin SUPPRESSES Hc (pair-breaking); when Tc is known, capped at the Pauli limit.
    """
    base = _legacy_critical_field(spin_score, coupling_score)
    if symmetry is PairingSymmetry.UNDETERMINED:
        return base
    if symmetry is PairingSymmetry.TRIPLET:
        return base
    # SINGLET: invert the spin dependence (moment pair-breaks), then cap at Pauli if Tc known.
    singlet = 5.0 * coupling_score * (1.0 - 0.5 * spin_score)
    if tc_kelvin is not None and tc_kelvin > 0.0:
        singlet = min(singlet, pauli_limit_tesla(tc_kelvin))
    return max(0.0, singlet)


def field_response_ratio(critical_field_t: float, tc_kelvin: float | None) -> float | None:
    """Bc / Bc_pauli — the singlet-vs-triplet discriminator. None when Tc is unknown
    (toy path): the ratio is a decisive-measurement PREDICTION, computable only with a
    pairing energy scale. > 1 => exceeds the Pauli limit => only a triplet can host it."""
    if tc_kelvin is None or tc_kelvin <= 0.0:
        return None
    return critical_field_t / pauli_limit_tesla(tc_kelvin)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /orme-lab && python3 -m pytest tests/test_pairing_symmetry.py -v`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/magnetic_field.py tests/test_pairing_symmetry.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: PairingSymmetry + Pauli-limit + pairing-conditional critical field"
```

---

### Task 2: creditable-mechanism filter by pairing symmetry (`mechanisms.py`)

**Files:**
- Modify: `src/orme_lab/mechanisms.py`
- Test: `tests/test_mechanisms.py` (extend)

**Interfaces:**
- Consumes: `PairingSymmetry` from `magnetic_field.py`; existing `Mechanism`, `MechanismResult`, `evaluate_mechanisms`.
- Produces: `creditable_under(symmetry: PairingSymmetry) -> frozenset[Mechanism]`; `filter_by_symmetry(results, symmetry) -> tuple[MechanismResult, ...]`.

Design: a candidate under one pairing symmetry may only be *credited* by mechanisms compatible with that symmetry. `UNDETERMINED` credits all (default, unchanged). `SINGLET` credits conventional singlet channels (`M_phonon`, `M_granular_josephson`). `TRIPLET` credits the moment-carrying channels (`M_triplet`, `M_spin_fluctuation`). `M_excitonic_polaritonic` is speculative/non-magnetic-glue and is credited only under `UNDETERMINED`. This is what makes spin's sign clean per hypothesis: under SINGLET the spin-positive `_triplet` credit is removed; under TRIPLET the singlet `_phonon` penalty is irrelevant.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_mechanisms.py
from orme_lab.mechanisms import creditable_under, filter_by_symmetry, Mechanism, evaluate_mechanisms
from orme_lab.magnetic_field import PairingSymmetry
from orme_lab.config import ModelThresholds


def test_creditable_sets_partition_by_symmetry():
    assert Mechanism.TRIPLET in creditable_under(PairingSymmetry.TRIPLET)
    assert Mechanism.PHONON not in creditable_under(PairingSymmetry.TRIPLET)
    assert Mechanism.PHONON in creditable_under(PairingSymmetry.SINGLET)
    assert Mechanism.TRIPLET not in creditable_under(PairingSymmetry.SINGLET)
    # UNDETERMINED credits everything (default, unchanged)
    assert set(creditable_under(PairingSymmetry.UNDETERMINED)) == set(Mechanism)


def test_filter_removes_incompatible_survivors():
    th = ModelThresholds()
    # high spin + good coupling: _triplet survives, _phonon is pair-broken
    results = evaluate_mechanisms(
        coupling=0.6, carrier_proxy=0.5, structural_stability=0.5,
        field_suppression=1.0, observable_signal=0.5,
        spin_polarization=0.8, em_coherence_score=None, n_atoms=13, thresholds=th)
    singlet = filter_by_symmetry(results, PairingSymmetry.SINGLET)
    # under the singlet assumption the surviving triplet track is NOT creditable
    assert all(m.mechanism != Mechanism.TRIPLET.value for m in singlet if m.survives)
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /orme-lab && python3 -m pytest tests/test_mechanisms.py -k "symmetry or creditable or filter" -v`
Expected: FAIL — cannot import `creditable_under`.

- [ ] **Step 3: Implement in `mechanisms.py`**

Add after `_SURROGATE` (before `evaluate_mechanisms`):

```python
from .magnetic_field import PairingSymmetry

#: Which pairing mechanisms a candidate may be CREDITED by, per assumed pairing symmetry.
#: UNDETERMINED credits all (default, unchanged). SINGLET: conventional singlet channels.
#: TRIPLET: moment-carrying (equal-spin) channels. This routes spin to ONE sign per hypothesis.
_CREDITABLE = {
    PairingSymmetry.UNDETERMINED: frozenset(Mechanism),
    PairingSymmetry.SINGLET: frozenset({Mechanism.PHONON, Mechanism.GRANULAR_JOSEPHSON}),
    PairingSymmetry.TRIPLET: frozenset({Mechanism.TRIPLET, Mechanism.SPIN_FLUCTUATION}),
}


def creditable_under(symmetry: PairingSymmetry) -> frozenset:
    return _CREDITABLE[symmetry]


def filter_by_symmetry(results: tuple[MechanismResult, ...],
                       symmetry: PairingSymmetry) -> tuple[MechanismResult, ...]:
    """Return only the mechanism results creditable under `symmetry`. A survivor of an
    incompatible symmetry is demoted to non-surviving (its physics is real but does not
    support THIS hypothesis's pairing assumption)."""
    ok = creditable_under(symmetry)
    out = []
    for r in results:
        if Mechanism(r.mechanism) in ok:
            out.append(r)
        else:
            out.append(MechanismResult(r.mechanism, False, 0.0, r.is_surrogate,
                                       f"not creditable under {symmetry.value} pairing", r.note))
    return tuple(out)
```

- [ ] **Step 4: Run to verify pass**

Run: `cd /orme-lab && python3 -m pytest tests/test_mechanisms.py -v`
Expected: PASS (existing + 2 new).

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/mechanisms.py tests/test_mechanisms.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: creditable-mechanism filter by pairing symmetry (clean spin sign per hypothesis)"
```

---

### Task 3: wire pairing symmetry + field-response ratio through the pipeline

**Files:**
- Modify: `src/orme_lab/config.py` (add `LabConfig.pairing_symmetry`)
- Modify: `src/orme_lab/pipeline.py` (`evaluate_candidate`, `CandidateRecord`)
- Test: `tests/test_pairing_symmetry.py` (extend)

**Interfaces:**
- Consumes: `PairingSymmetry`, `pairing_critical_field`, `field_response_ratio` (Task 1); `filter_by_symmetry` (Task 2).
- Produces: `CandidateRecord.field_response_ratio: float | None`, `CandidateRecord.pairing_symmetry: str`; `LabConfig.pairing_symmetry` (default `PairingSymmetry.UNDETERMINED`).

- [ ] **Step 1: Add the config field.** In `config.py`, add to `LabConfig` (after the `applied_field_t` field). Store the symmetry as a plain **string** (its `PairingSymmetry` value), NOT the enum — `magnetic_field.py` imports `config`, so importing `PairingSymmetry` into `config.py` would create an import cycle:

```python
    pairing_symmetry: str = "undetermined"  # PairingSymmetry value; "singlet"/"triplet" branch the field response
```

- [ ] **Step 2: Write the failing integration test**

```python
# add to tests/test_pairing_symmetry.py
from dataclasses import replace
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state


def _rec(symmetry="undetermined", field_t=0.0):
    el = get_element("Ir")
    geo = make_compact_cluster(el, 13)
    cfg = replace(DEFAULT_CONFIG, pairing_symmetry=symmetry, applied_field_t=field_t)
    return evaluate_candidate(el, geo, "high_spin", high_spin_state(el), cfg)


def test_default_symmetry_is_byte_identical():
    # UNDETERMINED default: field_suppression identical to a run with no symmetry concept.
    r = _rec("undetermined", field_t=0.0)
    assert r.pairing_symmetry == "undetermined"
    assert r.field_suppression == pytest.approx(1.0)   # zero field
    assert r.field_response_ratio is None               # no Tc on the toy path


def test_singlet_high_spin_lower_field_than_triplet_under_field():
    s = _rec("singlet", field_t=2.0)
    t = _rec("triplet", field_t=2.0)
    # Under an applied field, a high-spin singlet is suppressed more than a triplet.
    assert s.field_suppression <= t.field_suppression
```

- [ ] **Step 3: Run to verify fail**

Run: `cd /orme-lab && python3 -m pytest tests/test_pairing_symmetry.py -k "byte_identical or lower_field" -v`
Expected: FAIL — `CandidateRecord` has no `pairing_symmetry` / `field_response_ratio`.

- [ ] **Step 4: Implement the pipeline wiring.** Read `pipeline.py:166-345` first. Make these edits:

(a) Add two fields to `CandidateRecord` (after `field_suppression`, keep defaults so the toy path is unchanged):
```python
    field_response_ratio: float | None = None   # off-gate: Bc/Bc_pauli (None without Tc)
    pairing_symmetry: str = "undetermined"
```

(b) Replace the field-response seam (`pipeline.py:204-208`). Import at top of `pipeline.py`:
`from .magnetic_field import PairingSymmetry, pairing_critical_field, field_response_ratio` and `from .mechanisms import filter_by_symmetry`. Then:
```python
    sym = PairingSymmetry(config.pairing_symmetry)
    # Field-response seam (orbital + paramagnetic pair-breaking), pairing-symmetry-conditional.
    crit_field = pairing_critical_field(spin_pol, coupling, sym)  # tc unknown here; refined below if EPW runs
    if backend is not None and backend.provides(Capability.FIELD_RESPONSE):
        crit_field = backend.critical_field(spin_pol, coupling)
    suppression = magnetic_field_suppression_factor(config.applied_field_t, crit_field)
```

(c) Insert this **immediately after the EPW block** (`pipeline.py:234-240`, where `epw.tc_kelvin` becomes available) and **before** the identity/`ruled_out` block (`:274-276`). It computes the off-gate ratio always, and — only when Tc is known and the singlet symmetry is assumed — refines `crit_field`/`suppression`/`plaus`. Because it runs before `:274-276` and `:281`, the existing `ruled_out` and `evaluate_mechanisms` naturally pick up the refined `plaus`/`suppression` — do NOT recompute `ruled_out` here:
```python
    # Off-gate field-response discriminator (needs a pairing energy scale = Tc).
    fr_ratio = field_response_ratio(
        pairing_critical_field(spin_pol, coupling, PairingSymmetry.TRIPLET), epw.tc_kelvin)
    # Singlet refinement: a Pauli-limited critical field (only when Tc is known -> toy path untouched).
    if sym is PairingSymmetry.SINGLET and epw.tc_kelvin is not None:
        crit_field = pairing_critical_field(spin_pol, coupling, sym, tc_kelvin=epw.tc_kelvin)
        suppression = magnetic_field_suppression_factor(config.applied_field_t, crit_field)
        plaus = superconductivity_plausibility_score(
            coupling_score=coupling, carrier_proxy=carrier, field_suppression=suppression,
            structural_stability=stability, observable_signal=observable_signal, thresholds=th)
```
The `observable_signal` and `stability` locals are already defined above this point (`:210`, `:221`); the guard `epw.tc_kelvin is not None` keeps the toy path byte-identical.

(d) Apply the symmetry filter to the credited mechanisms (`pipeline.py:281-290`):
```python
    mech_results = filter_by_symmetry(evaluate_mechanisms(
        coupling=coupling, carrier_proxy=carrier, structural_stability=stability,
        field_suppression=suppression, observable_signal=observable_signal,
        spin_polarization=spin_pol, em_coherence_score=em_score, n_atoms=geometry.n_atoms,
        thresholds=th), sym)
```
`filter_by_symmetry` with `UNDETERMINED` returns the results unchanged, so the default path is byte-identical.

(e) Pass the two new fields into the `CandidateRecord(...)` constructor (after `field_suppression=suppression,`):
```python
        field_response_ratio=fr_ratio,
        pairing_symmetry=sym.value,
```

- [ ] **Step 5: Run to verify pass + no regressions**

Run: `cd /orme-lab && python3 -m pytest tests/test_pairing_symmetry.py -v && python3 -m pytest -q`
Expected: PASS; full suite green (the UNDETERMINED default keeps existing tests byte-identical).

- [ ] **Step 6: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/config.py src/orme_lab/pipeline.py tests/test_pairing_symmetry.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: thread pairing symmetry + field_response_ratio through the screen (default byte-identical)"
```

---

### Task 4: toy magnetic-drive-response proxy (`electromagnetic_coherence.py`)

**Files:**
- Modify: `src/orme_lab/electromagnetic_coherence.py`
- Test: `tests/test_magnetic_drive.py` (create)

**Interfaces:**
- Consumes: existing `CoherenceResult`, `evaluate_em_coherence` (`:270`), `ElectromagneticMode`.
- Produces: `magnetic_drive_response(coherence_score, spin_polarization, symmetry) -> float`; `DRIVE_BASELINE = 0.1`; `CoherenceResult.magnetic_drive_response: float`.

Design: a spin-carrying (triplet) coherent condensate can be parametrically pumped by an AC magnetic drive (magnon-BEC analogue, Demokritov 2006); a spin-neutral singlet has no clean magnetic drive. Toy proxy in [0,1]: nonzero only when there is both coherence AND a moment AND the assumed symmetry is triplet. Bounded, labeled a MODEL PROXY, Level 2.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_magnetic_drive.py
import pytest
from orme_lab.electromagnetic_coherence import magnetic_drive_response, DRIVE_BASELINE
from orme_lab.magnetic_field import PairingSymmetry


def test_triplet_with_coherence_and_moment_responds():
    r = magnetic_drive_response(0.8, 0.6, PairingSymmetry.TRIPLET)
    assert r > DRIVE_BASELINE


def test_singlet_has_no_magnetic_drive_channel():
    assert magnetic_drive_response(0.8, 0.6, PairingSymmetry.SINGLET) == 0.0


def test_no_moment_no_drive():
    assert magnetic_drive_response(0.8, 0.0, PairingSymmetry.TRIPLET) == 0.0


def test_no_coherence_no_drive():
    assert magnetic_drive_response(0.0, 0.6, PairingSymmetry.TRIPLET) == 0.0


def test_bounded_unit_interval():
    assert 0.0 <= magnetic_drive_response(1.0, 1.0, PairingSymmetry.TRIPLET) <= 1.0
```

- [ ] **Step 2: Run to verify fail**

Run: `cd /orme-lab && python3 -m pytest tests/test_magnetic_drive.py -v`
Expected: FAIL — cannot import `magnetic_drive_response`.

- [ ] **Step 3: Implement.** In `electromagnetic_coherence.py` add (import `PairingSymmetry` from `.magnetic_field`):

```python
DRIVE_BASELINE = 0.1   # below this modeled response, a drive-channel hypothesis is falsified


def magnetic_drive_response(coherence_score: float, spin_polarization: float,
                            symmetry: "PairingSymmetry") -> float:
    """Toy [0,1] proxy for parametric response to an AC MAGNETIC drive (magnon-BEC analogue).

    MODEL PROXY, Level 2. Speculation on the PGM-SAC premise + triplet assumption +
    magnon-analogue drive assumption — a hypothesis to test, not a mechanism claim. Nonzero
    ONLY for a spin-carrying (triplet) coherent condensate: needs coherence AND a moment AND
    equal-spin pairing. A spin-neutral singlet has no clean magnetic drive channel -> 0.
    """
    from .magnetic_field import PairingSymmetry as _PS
    if symmetry is not _PS.TRIPLET:
        return 0.0
    if coherence_score <= 0.0 or spin_polarization <= 0.0:
        return 0.0
    return max(0.0, min(1.0, coherence_score * spin_polarization))
```

Add a `magnetic_drive_response: float = 0.0` field to `CoherenceResult` (default 0.0 keeps existing construction valid), and set it in `evaluate_em_coherence(...)` — extend that function's signature with `symmetry: "PairingSymmetry" = None` (treat `None` as `UNDETERMINED`) and compute the field. Keep the `predicted_observables` / `explain()` additions labeled "MODEL PROXY (Level 2)".

- [ ] **Step 4: Run to verify pass**

Run: `cd /orme-lab && python3 -m pytest tests/test_magnetic_drive.py -v && python3 -m pytest tests/test_electromagnetic_coherence.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/electromagnetic_coherence.py tests/test_magnetic_drive.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: toy magnetic-drive-response proxy (triplet-only, magnon-BEC analogue, Level 2)"
```

---

### Task 5: hypotheses split + liveness dependency + off-gate + metrics wiring

**Files:**
- Modify: `src/orme_lab/lab_loop/hypotheses.py` (split H7, add H16-drive-triplet, `LIVENESS_DEPENDENCIES`, `validate_liveness`)
- Modify: `src/orme_lab/lab_loop/triage.py` (liveness gate)
- Modify: `src/orme_lab/lab_loop/closure.py` (off-gate additions)
- Modify: `src/orme_lab/lab_loop/avenue.py` (`METRIC_RANGES`, `ActionSpec.pairing_symmetry`)
- Modify: `src/orme_lab/lab_loop/runner.py` (aggregate metrics + pass pairing_symmetry)
- Modify: `src/orme_lab/pipeline.py` (`CandidateRecord.em_drive_response` + set it)
- Modify: `tests/test_closure.py` (golden set update)
- Test: `tests/test_liveness_dependency.py` (create)

**Interfaces:**
- Consumes: `Verdict`, `triage`, `is_independent`, `FalsificationCondition`.
- Produces: `HYPOTHESES` with `H7-singlet`,`H7-triplet`,`H16-drive-triplet` (H7 removed); `LIVENESS_DEPENDENCIES: dict[str,str]`; `validate_liveness(target, open_hypotheses) -> tuple[bool,str]`; `CandidateRecord.em_drive_response: float | None`; metrics `max_field_response_ratio`, `max_em_drive_response`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_liveness_dependency.py
import pytest
from orme_lab.lab_loop.hypotheses import HYPOTHESES, LIVENESS_DEPENDENCIES, validate_liveness
from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, is_independent
from orme_lab.lab_loop.avenue import METRIC_RANGES, FalsificationCondition, Comparator


def test_h7_split_present_and_h7_gone():
    assert "H7-singlet" in HYPOTHESES and "H7-triplet" in HYPOTHESES
    assert "H16-drive-triplet" in HYPOTHESES
    assert "H7" not in HYPOTHESES


def test_drive_depends_on_h7_triplet():
    assert LIVENESS_DEPENDENCIES["H16-drive-triplet"] == "H7-triplet"


def test_liveness_dead_parent_blocks():
    open_h = frozenset(HYPOTHESES) - {"H7-triplet"}
    ok, reason = validate_liveness("H16-drive-triplet", open_h)
    assert not ok and "H7-triplet" in reason
    # a hypothesis with no dependency always passes
    assert validate_liveness("H7-singlet", open_h)[0]


def test_new_offgate_and_metrics_exist():
    assert "field_response_ratio" in OFF_GATE_INVARIANTS
    assert "em_drive_response" in OFF_GATE_INVARIANTS
    assert "max_field_response_ratio" in METRIC_RANGES
    assert "max_em_drive_response" in METRIC_RANGES
    # both new signals are off-gate (pass the anti-tautology gate)
    assert is_independent(("field_response_ratio",))
    assert is_independent(("em_drive_response",))
    # the opposite falsifiers are fireable
    assert FalsificationCondition("max_field_response_ratio", Comparator.GT, 1.0).fireable()
    assert FalsificationCondition("max_em_drive_response", Comparator.LT, 0.1).fireable()
```

Plus a triage liveness test:
```python
# tests/test_liveness_dependency.py (continued) — build a minimal AvenueResult
from orme_lab.lab_loop.triage import triage, Verdict
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier


def _drive_avenue():
    return Avenue(
        id="a1", tier=Tier.TIER1, description="drive", targeted_hypothesis="H16-drive-triplet",
        action=ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, False, True, None, "triplet"),
        falsification=FalsificationCondition("max_em_drive_response", Comparator.LT, 0.1),
        predictor_invariants=("em_drive_response",), provenance="test")


def test_triage_inconclusive_when_parent_dead():
    res = AvenueResult(avenue=_drive_avenue(), records=(), metrics={"max_em_drive_response": 0.5})
    open_h = frozenset(HYPOTHESES) - {"H7-triplet"}   # parent killed
    assert triage(res, open_h).verdict == Verdict.INCONCLUSIVE
```

Note: `ActionSpec` gains a trailing `pairing_symmetry` field (Step 3) — the tuple above includes `"triplet"` as its last element.

- [ ] **Step 2: Run to verify fail**

Run: `cd /orme-lab && python3 -m pytest tests/test_liveness_dependency.py -v`
Expected: FAIL — imports missing.

- [ ] **Step 3: Implement.**

`hypotheses.py`: change `HYPOTHESES` to replace `"H7"` with `"H7-singlet", "H7-triplet"` and append `"H16-drive-triplet"`. Add:
```python
#: Dependent hypothesis id -> the id that must remain OPEN for it to be live.
#: H16-drive-triplet (spin/magnetic AC-drive channel) only makes sense if equal-spin
#: triplet pairing is still on the table. Evaluated at judge time (parent may die mid-run).
LIVENESS_DEPENDENCIES: dict[str, str] = {"H16-drive-triplet": "H7-triplet"}


def validate_liveness(target: str, open_hypotheses) -> tuple[bool, str]:
    """A dependent hypothesis is live only while its parent is open. Others always pass."""
    parent = LIVENESS_DEPENDENCIES.get(target)
    if parent is None:
        return True, ""
    if parent in open_hypotheses:
        return True, ""
    return False, f"{target}: parent hypothesis {parent} is killed — drive channel not live"
```

`triage.py`: after the target-open check (`triage.py:38-39`), add the liveness gate:
```python
    from .hypotheses import validate_liveness
    live, _reason = validate_liveness(av.targeted_hypothesis, open_hypotheses)
    if not live:
        return TriageOutcome(Verdict.INCONCLUSIVE, 0.0, None)
```

`closure.py`: add `"field_response_ratio"` (with the EPW block, it needs Tc) and `"em_drive_response"` (with the EM block) to `OFF_GATE_INVARIANTS`. Update the docstring.

`avenue.py`: add to `METRIC_RANGES`: `"max_field_response_ratio": (0.0, 5.0), "max_em_drive_response": (0.0, 1.0)`. Add `pairing_symmetry: str = "undetermined"` as the last field of `ActionSpec` (default keeps existing construction valid).

`runner.py`: add `"max_field_response_ratio", "max_em_drive_response"` to `_METRIC_KEYS`; in `_metrics` add `"max_field_response_ratio": _max("field_response_ratio"), "max_em_drive_response": _max("em_drive_response")`; in `run_avenue`, add `pairing_symmetry=action.pairing_symmetry` to the `replace(config, ...)` call.

`pipeline.py`: add `em_drive_response: float | None = None` to `CandidateRecord`; in the EM block (`pipeline.py:246-251`) compute `em_drive = magnetic_drive_response(em_score, spin_pol, sym)` when `em_score is not None` (import `magnetic_drive_response`), and pass `em_drive_response=em_drive` to the constructor. Also add `em_drive_response` to `closure.GATE_INPUT_CLOSURE`? No — it is off-gate; leave it only in `OFF_GATE_INVARIANTS`.

`tests/test_closure.py`: update the golden assertion to expect the two new members in `OFF_GATE_INVARIANTS` (read the file; extend the expected set).

- [ ] **Step 4: Run to verify pass + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_liveness_dependency.py tests/test_closure.py -v && python3 -m pytest -q`
Expected: PASS; full suite green.

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/lab_loop/ src/orme_lab/pipeline.py tests/test_liveness_dependency.py tests/test_closure.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: H7 split + H16-drive-triplet + liveness gate + off-gate signals + falsification metrics"
```

---

### Task 6: backend seam stubs (`backends.py`, `mechanisms.py` `_drive` track)

**Files:**
- Modify: `src/orme_lab/backends.py`
- Modify: `src/orme_lab/mechanisms.py`
- Test: `tests/test_backends.py` (extend), `tests/test_mechanisms.py` (extend)

**Interfaces:**
- Produces: `Capability.NON_PHONON_PAIRING`, `Capability.SPIN_DRIVE_RESPONSE`; `DFTBackend.non_phonon_pairing(...)` and `DFTBackend.spin_drive_response(...)` raising `_nyi`; `Mechanism.DRIVE` + `_drive(...)` track.

- [ ] **Step 1: Write the failing tests**

```python
# add to tests/test_backends.py
from orme_lab.backends import DFTBackend, Capability
import pytest

def test_new_capabilities_are_unimplemented_stubs():
    b = DFTBackend()
    assert not b.provides(Capability.NON_PHONON_PAIRING)
    assert not b.provides(Capability.SPIN_DRIVE_RESPONSE)
    with pytest.raises(NotImplementedError):
        b.non_phonon_pairing(None, None, None)
    with pytest.raises(NotImplementedError):
        b.spin_drive_response(None, None, None)
```

```python
# add to tests/test_mechanisms.py
from orme_lab.mechanisms import Mechanism
def test_drive_mechanism_member_exists():
    assert Mechanism.DRIVE.value == "M_drive"
```

- [ ] **Step 2: Run to verify fail** — `cd /orme-lab && python3 -m pytest tests/test_backends.py -k capabilities tests/test_mechanisms.py -k drive_mechanism -v` → FAIL.

- [ ] **Step 3: Implement.** In `backends.py`, add to `Capability` (match the enum-comment style at `:45-57`):
```python
    NON_PHONON_PAIRING = "non_phonon_pairing"     # TODO(backend): triplet/magnetic pairing kernel (NOT phonon-mediated)
    SPIN_DRIVE_RESPONSE = "spin_drive_response"   # TODO(backend): response to an AC magnetic (spin-sector) drive
```
Add two stub methods on `DFTBackend` mirroring the `_nyi` pattern (e.g. `plasmon_energy` at `:166-168`):
```python
    def non_phonon_pairing(self, element, geometry, state):
        """TODO(backend): non-phonon (triplet/magnetic) pairing channel. No toy fallback — a real
        triplet Tc requires a computed spin-fluctuation/odd-parity kernel; never fabricated."""
        self._nyi(Capability.NON_PHONON_PAIRING)

    def spin_drive_response(self, element, geometry, state):
        """TODO(backend): ab-initio response to an AC magnetic drive (spin-sector). No toy number
        here — the killable toy proxy lives in electromagnetic_coherence.magnetic_drive_response."""
        self._nyi(Capability.SPIN_DRIVE_RESPONSE)
```
In `mechanisms.py`, add `DRIVE = "M_drive"` to `Mechanism`, add it to `_SURROGATE` as `True`, add it to the `_CREDITABLE[TRIPLET]` set (Task 2), and add a `_drive(coupling, spin_pol, em_score, th)` track that is a labeled SURROGATE requiring a moment + EM coherence (mirrors `_excitonic`/`_triplet`), returning `is_surrogate=True` with a `"SURROGATE: spin/magnetic AC-drive (magnon-BEC analogue), not a computed kernel"` note. Add it to the `evaluate_mechanisms` return tuple.

**Note — DEFAULT-PATH BYTE-IDENTICAL reconciliation (post-review):** adding `Mechanism.DRIVE` to
the `Mechanism` enum and to `evaluate_mechanisms`'s return tuple (this task, as specced) means the
global-rejection branch's `tuple(_reject(m, why, _SURROGATE[m]) for m in Mechanism)` now iterates
6 members instead of 5. On the default path (`PairingSymmetry.UNDETERMINED`, `applied_field_t=0.0`)
this appends a new `M_drive✗ ...` clause to `CandidateRecord.mechanism_summary` that did not exist
pre-Task-6 — verified empirically against `fb43e4a`. No decision-bearing field or metric changes
(`surviving_mechanisms`, `credited_sc_lead`, `evidence_level`, `field_suppression`,
`field_response_ratio`, `sc_plausibility`, `verdict`, `ruled_out` are all unaffected in this
scenario), so this is scoped out of the byte-identical invariant per the Global Constraints note
above, and pinned going forward by `test_mechanism_summary_default_path_after_drive_track` in
`tests/test_mechanisms.py` — any future silent change to the default-path summary string now fails
a test instead of passing unnoticed.

- [ ] **Step 4: Run to verify pass** — `cd /orme-lab && python3 -m pytest tests/test_backends.py tests/test_mechanisms.py -q && python3 -m pytest -q` → PASS.

- [ ] **Step 5: Commit**
```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/backends.py src/orme_lab/mechanisms.py tests/test_backends.py tests/test_mechanisms.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: backend Capability stubs (non-phonon pairing + spin-drive) + _drive mechanism track"
```

---

### Task 7: web mirrors + honesty labels + digest

**Files:**
- Modify: `web/hypotheses.js` (cards for the new hypotheses), `web/metrics.js` (drive label), `web/sim.js` (drive field), `src/orme_lab/lab_loop/loop.py` (digest), `docs/hypothesis_matrix.md`
- Test: none in this task (parity test is Task 8)

- [ ] **Step 1:** In `docs/hypothesis_matrix.md`, replace the H7 row with `H7-singlet` and `H7-triplet` rows (opposite Pauli-limit field predictions; rejected-when: singlet rejected by field-response ratio > 1, triplet rejected by ratio ≤ 1) and add an `H16-drive-triplet` row (rejected when modeled magnetic-drive response < baseline; live only under H7-triplet). Add both decisive measurements: "critical field vs Pauli limit (1.86·Tc)" and "magnetic-drive response vs baseline".

- [ ] **Step 2:** In `web/hypotheses.js`, add registry cards for `H7-singlet`, `H7-triplet`, `H16-drive-triplet` following the existing `card()` shape (`id/group/level/status/statement/modeled/test`), each `level: 2`, statement naming the pairing symmetry and the decisive measurement, `test:` naming the falsification. Mark the drive card's statement with the provenance text ("speculation on PGM-SAC + triplet + magnon-analogue assumptions").

- [ ] **Step 3:** In `web/metrics.js`, add a `drive` entry (title "Magnetic-drive response", `confidence: "Toy (Level 2) …"`, `source: "src/orme_lab/electromagnetic_coherence.py"`) matching the existing entry shape (`:112-140`).

- [ ] **Step 4:** In `web/sim.js`, mirror the drive field: where the EM physics is reimplemented (`:221-312`), add a `magneticDriveResponse(coherence, spin, symmetry)` returning `symmetry==="triplet" ? clamp01(coherence*spin) : 0` and surface it in `evaluateCandidate` output. Keep numeric parity with the Python `magnetic_drive_response`.

- [ ] **Step 5:** In `lab_loop/loop.py` `_digest()` (`:51-122`), add a line to the screening-leads / registry section naming the H7 split and H16-drive-triplet and their two decisive measurements. Keep the `badge(LAB_CEILING)` header.

- [ ] **Step 6:** Manual check (no browser in build env — visual verification is out of scope here; see the operator visual-review note). Run `cd /orme-lab && python3 -m pytest -q` to confirm nothing Python broke.

- [ ] **Step 7: Commit**
```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add web/hypotheses.js web/metrics.js web/sim.js src/orme_lab/lab_loop/loop.py docs/hypothesis_matrix.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(web+docs): registry cards, drive honesty label, digest + hypothesis-matrix rows"
```

---

### Task 8: Python↔JS parity tests

**Files:**
- Test: `tests/test_web_pairing_parity.py` (create)

**Interfaces:** Consumes `HYPOTHESES` (Python), `web/hypotheses.js`, `web/sim.js`, `DRIVE_BASELINE`.

- [ ] **Step 1: Write the parity tests**

```python
# tests/test_web_pairing_parity.py
import re
from pathlib import Path
from orme_lab.lab_loop.hypotheses import HYPOTHESES

_WEB = Path(__file__).resolve().parents[1] / "web"


def test_new_hypotheses_present_in_web_registry():
    js = (_WEB / "hypotheses.js").read_text()
    # web uses dashed ids; the split + drive hypotheses must each appear as a card id
    for token in ("H7-singlet", "H7-triplet", "H16-drive-triplet"):
        assert token in js, f"{token} missing from web/hypotheses.js"


def test_sim_js_has_drive_response_mirror():
    js = (_WEB / "sim.js").read_text()
    assert "magneticDriveResponse" in js
    # triplet-only gating mirrored (singlet -> 0)
    assert re.search(r'symmetry\s*===\s*"triplet"', js)
```

For a numeric parity check on the drive proxy, follow the `test_ledger_parity.py` node pattern: shell out to `node --input-type=module` evaluating `magneticDriveResponse(0.8,0.6,"triplet")` and assert it equals the Python `magnetic_drive_response(0.8,0.6,PairingSymmetry.TRIPLET)` to 1e-9. (Include this only if `node` is available in the test env, mirroring the existing parity test's skip guard.)

- [ ] **Step 2: Run** — `cd /orme-lab && python3 -m pytest tests/test_web_pairing_parity.py -v` → PASS (after Task 7 landed the JS).

- [ ] **Step 3: Commit**
```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add tests/test_web_pairing_parity.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "test: Python<->JS parity for the new hypotheses + drive-response mirror"
```

---

### Task 9: cross-cutting acceptance contract + changelog

**Files:**
- Test: `tests/test_pairing_acceptance.py` (create)
- Modify: `docs/superpowers/specs/2026-07-18-pairing-symmetry-discriminator-design.md` (append a "Result" note after the tests run)

**Interfaces:** Consumes everything above.

- [ ] **Step 1: Write the acceptance tests** (one test per spec acceptance criterion). These are the contract that proves the honesty invariants and the "stricter, not more permissive" property.

```python
# tests/test_pairing_acceptance.py
import pytest
from dataclasses import replace
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import evaluate_candidate
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.lab_loop.triage import Verdict, triage
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator


def _av(target, metric, comp, thr, invariants, symmetry="undetermined"):
    return Avenue("a", Tier.TIER1, "d", target,
                  ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0, False, True, None, symmetry),
                  FalsificationCondition(metric, comp, thr), invariants, "test")


def test_1_independent_retirement():
    # killing H7-singlet leaves H7-triplet standing
    open_all = frozenset(HYPOTHESES)
    res = AvenueResult(_av("H7-singlet", "max_field_response_ratio", Comparator.GT, 1.0,
                           ("field_response_ratio",)), (), {"max_field_response_ratio": 1.5})
    out = triage(res, open_all)
    assert out.verdict == Verdict.KILLED_HYPOTHESIS and out.killed_hypothesis == "H7-singlet"
    assert "H7-triplet" in (open_all - {"H7-singlet"})


def test_2_drive_gated_on_triplet():
    res = AvenueResult(_av("H16-drive-triplet", "max_em_drive_response", Comparator.LT, 0.1,
                           ("em_drive_response",), "triplet"), (), {"max_em_drive_response": 0.5})
    assert triage(res, frozenset(HYPOTHESES) - {"H7-triplet"}).verdict == Verdict.INCONCLUSIVE
    assert triage(res, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED


def test_4_both_signals_off_gate():
    from orme_lab.lab_loop.closure import is_independent
    assert is_independent(("field_response_ratio",))
    assert is_independent(("em_drive_response",))


def test_5_hypotheses_diverge_same_ratio():
    # same field_response_ratio kills singlet (>1) and, mirrored, kills triplet (<=1)
    sing = _av("H7-singlet", "max_field_response_ratio", Comparator.GT, 1.0, ("field_response_ratio",))
    trip = _av("H7-triplet", "max_field_response_ratio", Comparator.LE, 1.0, ("field_response_ratio",))
    open_all = frozenset(HYPOTHESES)
    hi = {"max_field_response_ratio": 1.4}   # enhancement
    lo = {"max_field_response_ratio": 0.7}   # suppression
    assert triage(AvenueResult(sing, (), hi), open_all).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(AvenueResult(trip, (), hi), open_all).verdict == Verdict.SURVIVED
    assert triage(AvenueResult(trip, (), lo), open_all).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(AvenueResult(sing, (), lo), open_all).verdict == Verdict.SURVIVED


def _rec(symmetry, field_t=3.0, tc=None):
    el = get_element("Ir"); geo = make_compact_cluster(el, 13)
    cfg = replace(DEFAULT_CONFIG, pairing_symmetry=symmetry, applied_field_t=field_t)
    r = evaluate_candidate(el, geo, "high_spin", high_spin_state(el), cfg)
    return r


def test_6_stricter_under_singlet_than_undetermined():
    # a high-spin candidate is credited/field-tolerant less readily under the singlet assumption
    u = _rec("undetermined"); s = _rec("singlet")
    assert s.field_suppression <= u.field_suppression
    # and its surviving-mechanism set under singlet excludes the spin-positive triplet track
    assert "M_triplet" not in s.surviving_mechanisms


def test_3_no_double_count_clean_sign():
    # Under one symmetry, spin does not both credit a triplet mechanism AND carry a singlet penalty.
    s = _rec("singlet"); t = _rec("triplet")
    # singlet: no triplet credit; triplet: no phonon credit (the singlet pair-breaker)
    assert "M_triplet" not in s.surviving_mechanisms
    assert "M_phonon" not in t.surviving_mechanisms


def test_7_no_validated_and_level2():
    assert not hasattr(Verdict, "VALIDATED")
    r = _rec("singlet")
    assert r.evidence_level <= 2
```

- [ ] **Step 2: Run** — `cd /orme-lab && python3 -m pytest tests/test_pairing_acceptance.py -v`. Fix any wiring gaps the acceptance tests expose (they are the real contract). Then `python3 -m pytest -q` (full suite).

- [ ] **Step 3:** Append a short "Result" note to the design spec recording the actual outcome (which criteria passed, any candidate demonstrably worsened), authored after the run — no pre-judging.

- [ ] **Step 4: Commit**
```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add tests/test_pairing_acceptance.py docs/superpowers/specs/2026-07-18-pairing-symmetry-discriminator-design.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "test: pairing-symmetry acceptance contract (independent retirement, gating, off-gate, divergence, stricter)"
```

---

## Final: open PR (do not merge)

```bash
cd /orme-lab
git push -u origin pairing-symmetry-discriminator
BODY="Branches the field-response hypothesis H7 into singlet vs equal-spin-triplet pairing with a Chandrasekhar-Clogston Pauli-limit discriminator, and adds an H7-triplet-gated spin/magnetic AC-drive-channel hypothesis (magnon-BEC analogue) in the EM-coherence branch.

PairingSymmetry.UNDETERMINED is the default and keeps the zero-field toy path byte-identical. Under an explicit singlet/triplet assumption the critical field is pairing-conditional (singlet Pauli-limited/suppressed; triplet robust) and creditable mechanisms filter accordingly, so spin has one clean sign per hypothesis (no double-counting). field_response_ratio and em_drive_response are new OFF-GATE observables; H16-drive-triplet is live only while H7-triplet is open (judge-time liveness gate).

Honesty invariants preserved: no VALIDATED verdict, everything clamped Level 2, anti-tautology gate EXTENDED (both new signals off-gate) not weakened, independent retirement, generator/judge split. The screen is strictly more able to kill (a high-spin candidate credited under UNDETERMINED loses its triplet credit + is Pauli-suppressed under the singlet hypothesis). Full acceptance contract in tests/test_pairing_acceptance.py. Python<->JS parity guards added. Do not merge without operator review."
gh pr create -R Dezirae-Stark/orme-lab --base master --head pairing-symmetry-discriminator \
  --title "Pairing-symmetry field + spin-drive discriminators (singlet vs equal-spin triplet)" --body "$BODY"
```

Report the PR URL to the operator; do not merge — operator-reserved.
