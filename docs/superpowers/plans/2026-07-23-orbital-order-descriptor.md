# Computed orbital-order descriptor (QE projwfc) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the toy density-anisotropy descriptor with a value computed from real QE `projwfc.x` Löwdin d-occupations, and add a genuinely off-gate orbital-order parameter as a grounded against-triplet pairing discriminator — making the screen more discriminating, never more permissive, with evidence still clamped to Level 2.

**Architecture:** One QE run (`pw.x` SCF → `projwfc.x`) via a single `ORBITAL_ORDER` capability on `QuantumEspressoBackend` returns an `OrbitalResult` bundle with a gate-facing `anisotropy` (occupation-weighted d-orbital quadrupole) AND an off-gate `polarization` (frame-robust d-occupation imbalance in [0,1]) plus dominant-orbital metadata. Gated behind `LabConfig.compute_orbital_order` (default off) so the toy path is byte-identical. The polarization is a *different* contraction of the occupations than the gate anisotropy, so it passes the anti-tautology gate.

**Tech Stack:** Python 3 (stdlib), pytest, Quantum ESPRESSO 7.3.1 (`pw.x`, `projwfc.x`) at `/opt/qe/q-e-qe-7.3.1/bin`, ONCV pseudos at `/opt/orme-epw/pseudo`, vanilla JS (`web/*.js`).

## Global Constraints

- **No new Verdict members** (no VALIDATED/CONFIRMED). **Evidence stays Level 2** — a computed descriptor is NOT a higher evidence level.
- **Anti-tautology gate extended, not weakened:** `orbital_order_param` added to the pinned `OFF_GATE_INVARIANTS` and the golden `tests/lab_loop/test_closure.py` updated in lockstep. It must NOT be re-derivable from the gate's scalar inputs (the gate `anisotropy`).
- **Default path byte-identical:** `LabConfig.compute_orbital_order` defaults **False**; with it off / backend absent, every existing `CandidateRecord` field and metric is unchanged (decision-bearing + diagnostic). A regression is a bug.
- **No positive scoring term / no new hypothesis:** orbital order only ever acts as the *against-triplet* off-gate discriminator; never a positive SC/pairing score, never pairing/SC "evidence".
- **No fabricated values:** backend absent → `orbital_order_param=None`, `orbital_order_source="absent"`. The computed path only runs when QE is genuinely available.
- **Honest separability:** the descriptor is computed at fixed geometry + fixed magnetic config (computational isolation of cross-channel *feedback*), NOT physical separability — labeled so everywhere.
- **Determinism:** no time/RNG/order-dependent iteration.
- **Commit identity:** `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`; never emit AI-identity trailers.
- **Run tests:** `cd /orme-lab && python3 -m pytest`. Branch `orbital-order-descriptor`; PR at the end, do not merge.

## File structure

```
src/orme_lab/epw/
  qe_input.py          # + projwfc_input(approx, cfg, prefix)
  config.py            # + EPWConfig.projwfc_x = "projwfc.x"
  parse_projwfc.py     # NEW: parse_projwfc(text) -> OrbitalOccupations  (grounded on the Task 1 fixture)
  orbital_result.py    # NEW: OrbitalResult bundle (anisotropy, polarization, dominant_orbital, source, provenance)
src/orme_lab/
  orbital_order.py     # NEW: pure physics — d_polarization(occ), quadrupole_anisotropy(occ), dominant_orbital(occ)
  backends.py          # + Capability.ORBITAL_ORDER; DFTBackend.orbital_order stub; QuantumEspressoBackend impl + projwfc.x
  pipeline.py          # gated orbital_order() call; CandidateRecord.orbital_order_param / orbital_order_source; anisotropy override
  config.py            # LabConfig.compute_orbital_order = False
  lab_loop/
    closure.py         # + orbital_order_param in OFF_GATE_INVARIANTS
    avenue.py          # + max_orbital_order in METRIC_RANGES
    runner.py          # + metric aggregation (None-when-unmeasured) + validate_runnable flag guard
web/
  metrics.js           # orbital-order honesty entry (computed vs toy-fallback vs absent)
tests/
  fixtures/sample.projwfc          # NEW: REAL Ir projwfc output (Task 1)
  test_orbital_order.py            # physics core (Task 4)
  test_parse_projwfc.py            # parser vs real fixture (Task 3)
  test_orbital_backend.py          # backend seam + OrbitalResult (Task 5)
  test_orbital_pipeline.py         # pipeline wiring + provenance (Task 6)
  test_orbital_offgate.py          # off-gate + anti-tautology + against-triplet (Task 7)
  test_orbital_acceptance.py       # cross-cutting acceptance (Task 9)
  test_epw_qe_input.py, tests/lab_loop/test_closure.py   # extended
docs/
  epw-orbital-order-run.md         # NEW: live-run log + separability note (Task 9)
```

---

### Task 1: Capture REAL Ir projwfc output (LIVE QE — grounds every later task)

**Files:**
- Create: `tests/fixtures/sample.projwfc` (real output), `scratch notes` inline in the deck writer comments.

**Why first:** the projwfc file format is the core unknown. Every parser/physics task builds on the REAL columns, not a guess. QE is live now and may be torn down next session.

- [ ] **Step 1: Generate an Ir SCF deck** using the existing machinery. Read `src/orme_lab/epw/runs/pgm.py` (`pgm_config`) and `src/orme_lab/epw/qe_input.py` (`scf_input`). In a scratch dir, build an Ir monomer/compact approximant `build_approximant(...)`, an `EPWConfig` via `pgm_config("Ir", ...)` (ONCV pseudo at `/opt/orme-epw/pseudo/Ir_ONCV_PBE_sr.upf`, semicore handling as in the Ir EPW recipe), and write `scf_input(approx, cfg, prefix)` to `scf.in`.

- [ ] **Step 2: Run pw.x SCF live.**
```bash
cd <scratch> && /opt/qe/q-e-qe-7.3.1/bin/pw.x < scf.in > scf.out 2>&1
grep -c "JOB DONE" scf.out   # expect 1; if convergence fails, tune per docs/epw-ir-lambda-run.md (Fermi windows / semicore)
```

- [ ] **Step 3: Write and run a minimal projwfc deck.**
```
&projwfc
  prefix = '<same prefix>'
  outdir = './'
  filproj = 'ir.proj'
  lwrite_overlaps = .false.
/
```
Run: `/opt/qe/q-e-qe-7.3.1/bin/projwfc.x < projwfc.in > projwfc.out 2>&1`; expect "JOB DONE". Inspect the outputs (`projwfc.out`, `ir.proj.projwfc_up`, `*.pdos_atm*` files).

- [ ] **Step 4: Capture the fixture + document the format.** Copy the file that carries the per-atom (l=2, m) Löwdin occupations / state labels into `tests/fixtures/sample.projwfc`. In a comment block at the top of `src/orme_lab/epw/parse_projwfc.py` (created in Task 3), record the EXACT column layout you observed (state index, atom, wfc, l, m, occupation) so the parser and every reviewer work from ground truth, not the QE manual alone.

- [ ] **Step 5: Commit the fixture.**
```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' add tests/fixtures/sample.projwfc
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m "test: real Ir projwfc Löwdin-occupation fixture (live QE)"
```
If QE cannot be made to converge for Ir this session, STOP and report BLOCKED — do NOT fabricate a fixture; the whole point is real output.

---

### Task 2: projwfc deck writer + config

**Files:** Modify `src/orme_lab/epw/qe_input.py`, `src/orme_lab/epw/config.py`; Test `tests/test_epw_qe_input.py`.

**Interfaces:** Produces `projwfc_input(approx, cfg, prefix) -> str`; `EPWConfig.projwfc_x: str = "projwfc.x"`.

- [ ] **Step 1: Failing test** (mirror the existing deck substring tests at `tests/test_epw_qe_input.py`):
```python
def test_projwfc_input_has_namelist_and_prefix():
    from orme_lab.epw.qe_input import projwfc_input
    from orme_lab.epw.approximant import build_approximant
    from orme_lab.epw.config import EPWConfig
    approx = build_approximant("Ir", "compact_cluster")
    deck = projwfc_input(approx, EPWConfig(), "orme")
    assert "&projwfc" in deck.lower()
    assert "prefix" in deck and "orme" in deck
    assert "filproj" in deck
```
- [ ] **Step 2: Run → FAIL** (`cd /orme-lab && python3 -m pytest tests/test_epw_qe_input.py -k projwfc -v`).
- [ ] **Step 3: Implement.** Add `projwfc_x: str = "projwfc.x"` to `EPWConfig`. Add `projwfc_input(approx, cfg, prefix)` reusing the `_control`-style prefix/outdir idiom, writing the `&projwfc` namelist from Task 1's working deck (prefix, `outdir='./'`, `filproj`).
- [ ] **Step 4: Run → PASS**, then full suite.
- [ ] **Step 5: Commit** `feat: projwfc.x deck writer + EPWConfig.projwfc_x`.

---

### Task 3: parse_projwfc + OrbitalOccupations (against the REAL fixture)

**Files:** Create `src/orme_lab/epw/parse_projwfc.py`; Test `tests/test_parse_projwfc.py`.

**Interfaces:** Produces `OrbitalOccupations` (frozen: `per_atom: tuple[tuple[float, ...], ...]` — for each metal atom, the five d-orbital (l=2) Löwdin occupations, m-ordered) and `parse_projwfc(text) -> OrbitalOccupations`.

- [ ] **Step 1: Read the real fixture** `tests/fixtures/sample.projwfc` and the format comment from Task 1. The parser is format-dependent — implement against the ACTUAL columns, not the manual.
- [ ] **Step 2: Failing test:**
```python
def test_parse_real_ir_projwfc_gives_five_d_occupations():
    from pathlib import Path
    from orme_lab.epw.parse_projwfc import parse_projwfc
    text = (Path(__file__).parent / "fixtures" / "sample.projwfc").read_text()
    occ = parse_projwfc(text)
    assert len(occ.per_atom) >= 1
    for atom in occ.per_atom:
        assert len(atom) == 5              # five d orbitals (l=2, m=-2..2)
        assert all(0.0 <= x <= 2.0 for x in atom)   # Löwdin occupations per (l,m), spin-summed
```
- [ ] **Step 3: Run → FAIL**, then implement `parse_projwfc` extracting per-atom l=2 occupations from the real format. Frozen `OrbitalOccupations` dataclass.
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: parse projwfc Löwdin d-occupations (grounded on real Ir fixture)`.

---

### Task 4: orbital-order physics core (pure functions)

**Files:** Create `src/orme_lab/orbital_order.py`; Test `tests/test_orbital_order.py`.

**Interfaces:** Produces `d_polarization(occ: tuple[float,...]) -> float` (in [0,1]); `quadrupole_anisotropy(occ) -> float` (in [0,1]); `dominant_orbital(occ) -> str`; `_D_LABELS`.

- [ ] **Step 1: Failing tests** (hand-worked, format-independent):
```python
# tests/test_orbital_order.py
import pytest
from orme_lab.orbital_order import d_polarization, quadrupole_anisotropy, dominant_orbital


def test_equal_filling_zero_polarization():
    assert d_polarization((0.4, 0.4, 0.4, 0.4, 0.4)) == pytest.approx(0.0)


def test_single_orbital_dominant_high_polarization():
    p = d_polarization((2.0, 0.0, 0.0, 0.0, 0.0))
    assert p == pytest.approx(1.0)


def test_polarization_monotone_in_imbalance():
    assert d_polarization((1.0, 0.5, 0.5, 0.5, 0.5)) < d_polarization((1.8, 0.2, 0.2, 0.2, 0.2))


def test_polarization_bounded_unit_interval():
    for occ in [(0,0,0,0,0), (2,2,2,2,2), (1.3,0.1,0.9,0.0,0.7)]:
        assert 0.0 <= d_polarization(occ) <= 1.0


def test_quadrupole_anisotropy_bounded_and_zero_for_spherical():
    # equal d-occupation is spherically symmetric -> zero shape anisotropy
    assert quadrupole_anisotropy((0.4,)*5) == pytest.approx(0.0, abs=1e-9)
    assert 0.0 <= quadrupole_anisotropy((1.5, 0.1, 0.1, 0.1, 0.1)) <= 1.0


def test_dominant_orbital_names_the_max():
    assert dominant_orbital((0.1, 0.1, 0.9, 0.1, 0.1)) == "dxy" or isinstance(dominant_orbital((0.1,0.1,0.9,0.1,0.1)), str)
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** `src/orme_lab/orbital_order.py`:
```python
"""Orbital-order descriptors from Löwdin d-occupations (Level 2, MODEL-DERIVED proxies).

d_polarization: frame-robust orbital-order parameter P in [0,1] — normalized departure of the
five d-orbital occupations from equal filling (0 = degenerate, 1 = one orbital dominant).
Grounded: occupation-imbalance definition of orbital order (Tokura & Nagaosa, Science 288, 462,
2000; Fernandes/Chubukov/Schmalian, Nat. Phys. 10, 97, 2014). Off-gate pairing discriminator:
high P is generically triplet pair-breaking / lifts the interorbital-triplet degeneracy
(Ramires & Sigrist, PRB 94, 104501; Clepkens/Lindquist/Kee, PRR 3, 013001).

quadrupole_anisotropy: gate-facing charge-density shape anisotropy — occupation-weighted d-orbital
quadrupole, a d-manifold APPROXIMATION to the density shape (not a full charge-density cube).

Computed at fixed geometry + fixed magnetic config: this isolates cross-channel FEEDBACK by
construction, NOT physical separability (orbital/magnetic/lattice order are symmetry-locked).
"""
from __future__ import annotations

import math

_D_LABELS = ("dz2", "dxz", "dyz", "dxy", "dx2y2")  # m-ordered; align to the projwfc (l=2,m) order in parse_projwfc

# Diagonal quadrupole (3z^2-r^2 -> Q_zz) weights per real d-orbital, normalized; used for the
# occupation-weighted shape tensor. Standard angular quadrupole signs of the real d-harmonics.
_QZZ = {"dz2": +2.0, "dxz": +1.0, "dyz": +1.0, "dxy": -2.0, "dx2y2": -2.0}


def d_polarization(occ: "tuple[float, ...]") -> float:
    """Orbital-order parameter P in [0,1]: normalized d-occupation imbalance (0 = equal filling)."""
    n = len(occ)
    total = sum(occ)
    if total <= 0.0 or n == 0:
        return 0.0
    mean = total / n
    # normalized mean-absolute deviation from equal filling; max deviation is when all charge is
    # in one orbital (dev = 2*mean*(n-1)/n summed) -> normalize to [0,1].
    dev = sum(abs(x - mean) for x in occ)
    dev_max = 2.0 * mean * (n - 1)
    return 0.0 if dev_max <= 0.0 else min(1.0, dev / dev_max)


def quadrupole_anisotropy(occ: "tuple[float, ...]") -> float:
    """Gate-facing d-manifold charge-shape anisotropy in [0,1] from occupation-weighted quadrupole."""
    total = sum(occ)
    if total <= 0.0:
        return 0.0
    qzz = sum(w * o for w, o in zip((_QZZ[l] for l in _D_LABELS), occ)) / total
    # |Q_zz| normalized by its max magnitude (2.0) -> [0,1] departure from spherical (Q_zz=0).
    return min(1.0, abs(qzz) / 2.0)


def dominant_orbital(occ: "tuple[float, ...]") -> str:
    """Label of the most-occupied d-orbital (symmetry metadata; non-scoring provenance)."""
    return _D_LABELS[max(range(len(occ)), key=lambda i: occ[i])]
```
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: orbital-order physics core (d-polarization + quadrupole anisotropy)`.

---

### Task 5: OrbitalResult + QuantumEspressoBackend ORBITAL_ORDER seam + runner stage

**Files:** Create `src/orme_lab/epw/orbital_result.py`; Modify `src/orme_lab/backends.py`, `src/orme_lab/epw/runner.py`; Test `tests/test_orbital_backend.py`.

**Interfaces:** Produces `Capability.ORBITAL_ORDER = "orbital_order"`; `DFTBackend.orbital_order(element, geometry, state) -> OrbitalResult` (stub); `QuantumEspressoBackend.orbital_order` (`@implemented`, `binary_requires` += `projwfc.x`); `OrbitalResult(anisotropy, polarization, dominant_orbital, source, provenance)` with `toy_absent`/`not_applicable`/`failed`/`from_occupations` constructors + per-atom aggregation (mean over metal atoms).

- [ ] **Step 1: Failing test** (fixture/fake-runner, no live QE — mirror `tests/test_epw_backend.py`):
```python
def test_orbital_result_from_occupations_aggregates():
    from orme_lab.epw.orbital_result import OrbitalResult
    r = OrbitalResult.from_occupations(((2.0,0.0,0.0,0.0,0.0),(2.0,0.0,0.0,0.0,0.0)), source="epw")
    assert r.polarization == pytest.approx(1.0)
    assert 0.0 <= r.anisotropy <= 1.0
    assert r.provenance and r.source == "epw"


def test_qe_backend_declares_orbital_order():
    from orme_lab.backends import QuantumEspressoBackend, Capability
    assert Capability.ORBITAL_ORDER in QuantumEspressoBackend.declared_capabilities
    assert "projwfc.x" in QuantumEspressoBackend.binary_requires
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** `OrbitalResult` frozen dataclass (nullable numeric fields + `source`/`provenance`; `from_occupations(per_atom, source)` computes `polarization = mean(d_polarization(a) for a in per_atom)`, `anisotropy = mean(quadrupole_anisotropy(a) ...)`, `dominant_orbital` of the mean occupation; null-object `toy_absent`/`not_applicable`/`failed`). Add `Capability.ORBITAL_ORDER` + `DFTBackend.orbital_order(...)` stub. On `QuantumEspressoBackend`: `declared_capabilities` += `ORBITAL_ORDER`, `binary_requires` += `"projwfc.x"`, and an `@implemented(Capability.ORBITAL_ORDER) orbital_order(...)` that lazily builds the approximant, runs SCF+projwfc via an injectable runner, parses with `parse_projwfc`, and returns `OrbitalResult.from_occupations(...)`; wrap in try/except → `OrbitalResult.failed(...)` (never abort the screen). Add the projwfc stage to `LiveEPWRunner` (a `_run(cfg.projwfc_x, projwfc_input(...), converge=False)` after SCF, reading the `filproj` file) OR a dedicated lightweight runner method — implementer's call, matching the EPW runner style.
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: OrbitalResult + QuantumEspressoBackend ORBITAL_ORDER seam (projwfc)`.

---

### Task 6: pipeline wiring + provenance + fallback

**Files:** Modify `src/orme_lab/config.py`, `src/orme_lab/pipeline.py`; Test `tests/test_orbital_pipeline.py`.

**Interfaces:** `LabConfig.compute_orbital_order: bool = False`; `CandidateRecord.orbital_order_param: float | None = None`, `orbital_order_source: str = "toy"`.

- [ ] **Step 1: Failing tests:**
```python
def test_default_path_byte_identical_and_inert():
    # flag off -> no orbital_order_param, anisotropy from the toy path, source "toy"
    r = _rec(compute_orbital_order=False)
    assert r.orbital_order_param is None
    assert r.orbital_order_source == "toy"


def test_computed_overrides_anisotropy_and_sets_param(fake_qe_backend):
    r = _rec(compute_orbital_order=True, backend=fake_qe_backend)  # fake returns a known OrbitalResult
    assert r.orbital_order_source == "computed"
    assert r.orbital_order_param is not None
    assert r.anisotropy == pytest.approx(fake_qe_backend._orbital.anisotropy)
```
(Provide a `fake_qe_backend` fixture whose `provides(ORBITAL_ORDER)` is True, `available()` True, and `orbital_order(...)` returns a canned `OrbitalResult`.)
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** Add the config flag (default False). Add the two `CandidateRecord` fields (defaults keep the toy path byte-identical). In `evaluate_candidate`, after the toy `anisotropy` is computed, add a gated block: `if config.compute_orbital_order and backend and backend.provides(Capability.ORBITAL_ORDER) and backend.available(): oo = backend.orbital_order(element, geometry, state); if oo.anisotropy is not None: anisotropy = oo.anisotropy; ricebean = is_ricebean(anisotropy, th); orbital_order_param = oo.polarization; orbital_order_source = "computed"` — else `orbital_order_param=None, orbital_order_source="toy"` (or "absent" if the flag was on but the backend failed). Must run BEFORE `carrier_coherence_proxy` so the gate consumes the computed anisotropy. Pass both new fields to the `CandidateRecord(...)` constructor.
- [ ] **Step 4: Run → PASS**, full suite (byte-identical default pinned).
- [ ] **Step 5: Commit** `feat: pipeline consumes computed orbital-order (gated, default byte-identical) + provenance`.

---

### Task 7: off-gate discriminator + anti-tautology + against-triplet falsification

**Files:** Modify `src/orme_lab/lab_loop/closure.py`, `avenue.py`, `runner.py`; Test `tests/test_orbital_offgate.py`, `tests/lab_loop/test_closure.py`.

**Interfaces:** `orbital_order_param` ∈ `OFF_GATE_INVARIANTS`; `max_orbital_order: (0.0, 1.0)` ∈ `METRIC_RANGES`; runner aggregates it (None-when-unmeasured); `validate_runnable` requires `compute_orbital_order` for a `max_orbital_order` falsifier.

- [ ] **Step 1: Failing tests:**
```python
def test_orbital_order_is_off_gate():
    from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, GATE_INPUT_CLOSURE, is_independent
    assert "orbital_order_param" in OFF_GATE_INVARIANTS
    assert "orbital_order_param" not in GATE_INPUT_CLOSURE
    assert is_independent(("orbital_order_param",))


def test_metric_and_ranges_present():
    from orme_lab.lab_loop.avenue import METRIC_RANGES
    assert METRIC_RANGES["max_orbital_order"] == (0.0, 1.0)


def test_high_orbital_order_kills_triplet():
    # an H7-triplet avenue with falsifier max_orbital_order > 0.5 fires on a high-P run
    ...  # build AvenueResult(metrics={"max_orbital_order": 0.8}) -> triage -> KILLED_HYPOTHESIS


def test_anti_tautology_moves_pairing_not_from_gate_inputs():
    # two candidates: identical gate scalars (anisotropy, coupling, spin) but different P ->
    # the H7-triplet falsifier fires for the high-P one, survives for the low-P one.
    ...
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** (mirror the `field_response_ratio` off-gate wiring exactly): add `orbital_order_param` to `OFF_GATE_INVARIANTS` (closure.py) + update golden `tests/lab_loop/test_closure.py`; `max_orbital_order: (0.0, 1.0)` to `METRIC_RANGES`; `runner._METRIC_KEYS` + `_NONE_WHEN_UNMEASURED` + `_max_or_none("orbital_order_param")`; `validate_runnable` guard requiring `avenue.action` compute flag / `use` for a `max_orbital_order` falsifier. Provide `ActionSpec`/config plumbing so an avenue can request `compute_orbital_order` (mirror `use_em`). Document the against-triplet semantics + provenance/uncertainty on the avenue.
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: orbital_order_param off-gate + against-triplet falsification (anti-tautology verified)`.

---

### Task 8: web honesty labels

**Files:** Modify `web/metrics.js`; Test: none (JS honesty label).

- [ ] **Step 1:** Add a `metrics.js` entry for orbital order: title "Orbital-order parameter (model-derived)", `confidence: "Computed from QE projwfc Löwdin occupations when the backend is live; toy-fallback / absent otherwise. Level 2 — a descriptor, not evidence; orbital order is a normal-state ordering, NOT superconductivity."`, `source: "src/orme_lab/orbital_order.py"`. Label the three provenance states (computed / toy-fallback / absent) so an outside viewer cannot over-read it. Match the existing "Toy (Level 2)" wording convention.
- [ ] **Step 2:** `cd /orme-lab && node --check web/metrics.js` (syntax) + `python3 -m pytest -q` (nothing Python broke).
- [ ] **Step 3: Commit** `feat(web): orbital-order honesty label (model-derived vs toy-fallback vs absent)`.

---

### Task 9: acceptance contract + LIVE end-to-end validation + changelog

**Files:** Create `tests/test_orbital_acceptance.py`, `docs/epw-orbital-order-run.md`; Modify the design spec (append a Result note).

- [ ] **Step 1: Acceptance tests** (one per spec criterion 1–7): inert-without-backend + toy-fallback flagged; computed differs from toy on ≥1 candidate (fake backend); anti-tautology (moves a pairing outcome not from gate inputs); can worsen standing (H7-triplet killed by high P); no VALIDATED + Level-2 + provenance correct on every path; guardrail (no positive SC/pairing score on the toy path); golden closure test green.
- [ ] **Step 2: LIVE end-to-end validation (criterion 8).** With QE live, run one real candidate (Ir compact cluster) through `evaluate_candidate` with `compute_orbital_order=True` and a real `QuantumEspressoBackend`:
```bash
cd /orme-lab && python3 -c "
from orme_lab.config import DEFAULT_CONFIG
from dataclasses import replace
from orme_lab.pipeline import evaluate_candidate
from orme_lab.backends import QuantumEspressoBackend
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
el=get_element('Ir'); geo=make_compact_cluster(el,13)
cfg=replace(DEFAULT_CONFIG, compute_orbital_order=True)
r=evaluate_candidate(el, geo, 'high_spin', high_spin_state(el), cfg, backend=QuantumEspressoBackend())
print('source', r.orbital_order_source, 'P', r.orbital_order_param, 'anisotropy', r.anisotropy)
assert r.orbital_order_source=='computed'
assert r.orbital_order_param is not None and 0.0<=r.orbital_order_param<=1.0
assert 0.0<=r.anisotropy<=1.0
print('LIVE ORBITAL-ORDER VALIDATION PASSED')
"
```
Record the actual numbers in `docs/epw-orbital-order-run.md` with the separability note (fixed geometry+spin config; computational isolation, not physical separability) and the precondition-met confirmation. If QE cannot run, report the deterministic suite green + the live step BLOCKED (do not fake it).
- [ ] **Step 3: Full suite** `cd /orme-lab && python3 -m pytest -q`.
- [ ] **Step 4: Commit** `test: orbital-order acceptance contract + live Ir validation; docs run-log`.

---

## Final: open PR (do not merge)

```bash
cd /orme-lab
git push -u origin orbital-order-descriptor
BODY="Replaces the toy density-anisotropy with a value computed from real QE projwfc.x Löwdin d-occupations, and adds an off-gate orbital-order parameter (d-occupation polarization) as a grounded against-triplet pairing discriminator. Precondition MET: QE projwfc live; validated end-to-end on Ir (docs/epw-orbital-order-run.md). One ORBITAL_ORDER capability returns an OrbitalResult bundle (gate anisotropy + off-gate polarization) from one pw.x+projwfc.x run; gated behind LabConfig.compute_orbital_order (default off) so the toy path is byte-identical. Evidence stays Level 2 (a computed descriptor is not a raised level); anti-tautology gate EXTENDED (orbital_order_param off-gate, distinct contraction from the gate anisotropy) not weakened; no new hypothesis, no positive scoring term; honest separability (computational isolation, not physical). Prior-art grounded (Tokura-Nagaosa; Fernandes/Chubukov/Schmalian; Ramires-Sigrist; Clepkens-Kee). Do not merge without operator review."
gh pr create -R Dezirae-Stark/orme-lab --base master --head orbital-order-descriptor \
  --title "Computed orbital-order descriptor (QE projwfc) + against-triplet off-gate discriminator" --body "$BODY"
```
Report the PR URL; do not merge — operator-reserved.
