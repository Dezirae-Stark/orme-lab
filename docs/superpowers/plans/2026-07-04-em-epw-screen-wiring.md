# EM + EPW Screen Wiring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Wire electromagnetic-coherence (real, grounded) and the EPW seam (honest plumbing) into the ORME screen so avenue flags `use_em`/`use_epw` actually change the result — making H12/H16 the first hypotheses with a real, varying, off-gate independent signal.

**Architecture:** EM lives in the core `pipeline.evaluate_candidate`, gated by a new `LabConfig.compute_em_coherence` flag; it feeds a groundable free-electron carrier density and the existing anisotropy into the existing `evaluate_em_coherence`, exposing `em_*` observables on `CandidateRecord`, into `OFF_GATE_INVARIANTS`, and as a lab-loop metric. The EPW seam threads an injectable `epw_backend` through `run_avenue`/`run_loop` with an honest `epw_status`; a test-only `FakeEPWBackend` proves the plumbing without QE binaries.

**Tech Stack:** Python 3, stdlib + existing `orme_lab` modules, pytest. No new third-party deps.

## Global Constraints

- **Determinism in the critical path:** no `time.time()`, no `datetime.now()`, no unseeded RNG, no order-dependent dict/set iteration. EM computation is pure.
- **Evidence ceiling unchanged:** `LAB_CEILING = 2`. EM/EPW results do not raise it.
- **No fabricated physics:** `free_electron_density` is a flagged toy free-electron estimate; the Pd (`s_electrons==0`) → dark limitation is documented in-code, not hidden. Coupling-channels are OUT of scope this cycle.
- **EM coherence is NOT superconductivity:** it is the H12 mundane alternative. Never let `em_coherence_score` read as SC evidence in any label, digest, or metric name.
- **EPW honesty:** the `FakeEPWBackend`/`FakeEPWRunner` mock lives under `tests/` only, never shipped in a production path. `epw_status="unavailable"` must be surfaced when EPW was requested but binaries are absent.
- **No AI-identity git trailers.** Commit as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m '...'`. No `Co-Authored-By` / `Signed-off-by` / `Claude-Session`.
- **Interpreter is `python3`**, not `python`.
- Spec: `docs/superpowers/specs/2026-07-04-em-epw-screen-wiring-design.md`.

## File Structure

| File | Change |
|---|---|
| `src/orme_lab/electromagnetic_coherence.py` | Add `free_electron_density(element)`. |
| `src/orme_lab/config.py` | Add `LabConfig.compute_em_coherence: bool = False`. |
| `src/orme_lab/pipeline.py` | Add `em_*` fields to `CandidateRecord`; compute EM in `evaluate_candidate` when flag on; update byte-identity docstring. |
| `src/orme_lab/lab_loop/closure.py` | Add `em_*` to `OFF_GATE_INVARIANTS`. |
| `src/orme_lab/lab_loop/avenue.py` | Add `max_em_coherence_score` to `METRIC_RANGES`. |
| `src/orme_lab/lab_loop/runner.py` | Emit `max_em_coherence_score`; thread `use_em`; add `epw_backend` param + `AvenueResult.epw_status`. |
| `src/orme_lab/lab_loop/loop.py` | Thread `epw_backend` through `run_loop`; digest surfaces EPW-unavailable. |
| `tests/lab_loop/_fake_epw.py` | Test-only `FakeEPWRunner` + `FakeEPWBackend`. |
| `tests/**` | New tests per task. |

Consumed signatures (verified):
- `orme_lab.electromagnetic_coherence.evaluate_em_coherence(number_density_m3, anisotropy_score, thresholds) -> CoherenceResult` with `.coherence_score: float`, `.regime: str`, `.mode.rabi_splitting_ev: float`, `.mode.coherence_lifetime_fs: float`.
- `orme_lab.elements.Element.s_electrons: int`, `.covalent_radius_ang: float`; `get_element(sym)`.
- `orme_lab.config.LabConfig` (frozen), `ModelThresholds`, `DEFAULT_CONFIG`.
- `orme_lab.pipeline.evaluate_candidate(element, geometry, spin_label, state, config, backend=None)`; `run_screen(elements, config, geometry_factory, backend)`; `CandidateRecord` (sc_* fields end at `sc_source: str = "toy"`).
- `orme_lab.backends.EPWBackend(config=None, runner=None)`, classmethod `available() -> bool` (hard-checks `pw.x`/`ph.x`/`epw.x`); `provides(SC_GAP)`.
- `orme_lab.lab_loop.runner.run_avenue(avenue, config=DEFAULT_CONFIG, backend=None, screen_fn=run_screen) -> AvenueResult`; `AvenueResult(avenue, records, metrics)`.
- `orme_lab.lab_loop.loop.run_loop(generator, config, loop_config, backend=None, screen_fn=run_screen) -> LoopReport`.

---

### Task 1: `free_electron_density` — groundable carrier density

**Files:**
- Modify: `src/orme_lab/electromagnetic_coherence.py`
- Test: `tests/test_free_electron_density.py`

**Interfaces:**
- Produces: `free_electron_density(element) -> float` (electrons/m³).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_free_electron_density.py
from orme_lab.electromagnetic_coherence import free_electron_density, plasmon_energy_ev
from orme_lab.elements import get_element


def test_gold_density_in_metal_range():
    n = free_electron_density(get_element("Au"))
    assert 5e28 < n < 2e29           # textbook metal free-electron density
    # and it yields a physically sane bulk plasmon energy
    assert 4.0 < plasmon_energy_ev(n) < 15.0


def test_palladium_is_dark_no_conduction_electrons():
    # Pd is [Kr]4d10 -> s_electrons == 0 -> free-electron model gives n = 0.
    assert free_electron_density(get_element("Pd")) == 0.0


def test_density_is_positive_for_s1_metals():
    for sym in ("Ag", "Pt", "Ir", "Os", "Rh", "Ru"):
        assert free_electron_density(get_element(sym)) > 0.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_free_electron_density.py -v`
Expected: FAIL — `ImportError: cannot import name 'free_electron_density'`.

- [ ] **Step 3: Write minimal implementation**

Add to `src/orme_lab/electromagnetic_coherence.py` (after the imports, near `plasmon_energy_ev`). Add `math` is already imported; import the Element type only for annotations:

```python
def free_electron_density(element) -> float:
    """Free-electron carrier density n (electrons per cubic metre), toy estimate.

    n = conduction_electrons / V_atom, with conduction_electrons = the valence
    s-electron count (the nearly-free carriers of the free-electron model) and
    V_atom the volume of a sphere of the covalent radius.

    This is the textbook metal plasmon density: Au (s=1, r=1.36 A) -> ~9.5e28 /m^3
    -> plasmon ~9 eV, matching real gold.

    HONEST LIMITATION: a d-band metal with no valence s-electron (Pd, [Kr]4d10)
    returns n = 0 -> the EM channel is dark for it, because the free-electron
    model genuinely does not apply. That is a real caveat, not a fudge. Flagged
    toy, like every model in this package.
    """
    conduction_electrons = element.s_electrons
    if conduction_electrons <= 0:
        return 0.0
    radius_m = element.covalent_radius_ang * 1e-10
    v_atom = (4.0 / 3.0) * math.pi * radius_m**3
    if v_atom <= 0:
        return 0.0
    return conduction_electrons / v_atom
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_free_electron_density.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/electromagnetic_coherence.py tests/test_free_electron_density.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'em: free-electron carrier density (toy, Pd-dark caveat documented)'
```

---

### Task 2: EM in the pipeline — config flag + `em_*` record fields

**Files:**
- Modify: `src/orme_lab/config.py`
- Modify: `src/orme_lab/pipeline.py`
- Test: `tests/test_pipeline_em.py`

**Interfaces:**
- Consumes: `free_electron_density` (Task 1); `evaluate_em_coherence`.
- Produces: `LabConfig.compute_em_coherence: bool = False`; `CandidateRecord.em_coherence_score/em_regime/em_rabi_ev/em_lifetime_fs` (all default `None`).

- [ ] **Step 1: Write the failing test**

```python
# tests/test_pipeline_em.py
import dataclasses
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import run_screen
from orme_lab.elements import get_element


def _au_records(compute_em):
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_em_coherence=compute_em)
    return run_screen(elements=[get_element("Au")], config=cfg)


def test_em_absent_by_default():
    for r in run_screen(elements=[get_element("Au")]):
        assert r.em_coherence_score is None
        assert r.em_regime is None


def test_em_present_when_flag_on():
    recs = _au_records(True)
    # a connected Au geometry has carriers -> em fields populated (not None)
    assert any(r.em_coherence_score is not None for r in recs)
    for r in recs:
        if r.em_coherence_score is not None:
            assert 0.0 <= r.em_coherence_score <= 1.0
            assert r.em_regime in ("weak", "strong", "ultrastrong")


def test_em_is_deterministic():
    a = [(r.element, r.geometry, r.em_coherence_score) for r in _au_records(True)]
    b = [(r.element, r.geometry, r.em_coherence_score) for r in _au_records(True)]
    assert a == b


def test_palladium_em_is_dark_when_flag_on():
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_em_coherence=True)
    for r in run_screen(elements=[get_element("Pd")], config=cfg):
        # n=0 -> plasmon 0 -> weak regime -> coherence 0.0 (dark), never None here
        assert r.em_coherence_score == 0.0
        assert r.em_regime == "weak"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_pipeline_em.py -v`
Expected: FAIL — `TypeError` on `replace(... compute_em_coherence=...)` (field absent) / `AttributeError: em_coherence_score`.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/config.py`, add the field to `LabConfig` (after `applied_field_t`/`random_seed`, before `output_dir`):

```python
    compute_em_coherence: bool = False
    """When True, the screen also computes the electromagnetic-coherence channel
    (plasmon/polariton) per candidate and records em_* observables. Off by
    default so the toy path's values stay byte-identical."""
```

In `src/orme_lab/pipeline.py`, add fields to `CandidateRecord` immediately after `sc_source`:

```python
    # Electromagnetic-coherence channel (H12/H16). Computed only when
    # config.compute_em_coherence is True; None otherwise. This is the
    # coherence question, NOT superconductivity -- a high score is the H12
    # mundane alternative, never SC evidence.
    em_coherence_score: float | None = None
    em_regime: str | None = None
    em_rabi_ev: float | None = None
    em_lifetime_fs: float | None = None
```

In `src/orme_lab/pipeline.py`, imports (top): add

```python
from .electromagnetic_coherence import evaluate_em_coherence, free_electron_density
```

In `evaluate_candidate`, after the EPW block and before `level = min(...)`, compute EM:

```python
    # EM-coherence seam (H12/H16). Off-gate signal, gated by config flag. A high
    # coherence score is the H12 mundane alternative, NOT superconductivity.
    em_score = em_regime = em_rabi = em_lifetime = None
    if config.compute_em_coherence:
        n = free_electron_density(element)
        coh = evaluate_em_coherence(n, anisotropy, th)
        em_score = coh.coherence_score
        em_regime = coh.regime
        em_rabi = coh.mode.rabi_splitting_ev
        em_lifetime = coh.mode.coherence_lifetime_fs
```

Then pass them into the `CandidateRecord(...)` constructor (add these kwargs alongside the `sc_*` ones):

```python
        em_coherence_score=em_score,
        em_regime=em_regime,
        em_rabi_ev=em_rabi,
        em_lifetime_fs=em_lifetime,
```

Update the module docstring byte-identity note (around line 16) to:

```python
    Determinism: given the same :class:`~orme_lab.config.LabConfig`, a screen
    produces byte-identical output. No wall-clock, no unseeded RNG. Records are
    sorted by a total, tie-broken key so ordering is stable. This byte-identity
    guarantee applies to the toy path (``backend=None``, ``compute_em_coherence``
    off); the schema always includes the ``em_*`` columns (``None`` when EM is
    off). With a live EPW backend the ``sc_*`` columns are not byte-reproducible.
```

Note: `th = config.thresholds` is already bound at the top of `evaluate_candidate`; `anisotropy` and `element` are already in scope.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_pipeline_em.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/config.py src/orme_lab/pipeline.py tests/test_pipeline_em.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'em: compute EM coherence in the screen (config-gated), em_* record fields'
```

---

### Task 3: EM observables are off-gate (closure)

**Files:**
- Modify: `src/orme_lab/lab_loop/closure.py`
- Test: `tests/lab_loop/test_closure.py` (extend)

**Interfaces:**
- Consumes: the `em_*` field names (Task 2).
- Produces: `em_*` names in `OFF_GATE_INVARIANTS`.

- [ ] **Step 1: Write the failing test**

Add to `tests/lab_loop/test_closure.py`:

```python
def test_em_observables_are_off_gate():
    from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, GATE_INPUT_CLOSURE
    for f in ("em_coherence_score", "em_regime", "em_rabi_ev", "em_lifetime_fs"):
        assert f in OFF_GATE_INVARIANTS
    # EM is a distinct channel from the SC gate -> must stay disjoint.
    assert GATE_INPUT_CLOSURE.isdisjoint(OFF_GATE_INVARIANTS)


def test_em_predictor_is_independent():
    from orme_lab.lab_loop.closure import is_independent
    assert is_independent(("em_coherence_score",)) is True
```

Also update the existing exact-pin test `test_offgate_set_is_pinned_exactly` to include the four `em_*` names in its expected frozenset.

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_closure.py -v`
Expected: FAIL — `em_coherence_score` not in `OFF_GATE_INVARIANTS`; the pinned-set test also fails.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/lab_loop/closure.py`, extend `OFF_GATE_INVARIANTS`:

```python
OFF_GATE_INVARIANTS: frozenset[str] = frozenset({
    "sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev", "sc_mu_star",
    # Electromagnetic-coherence channel (H12/H16): a distinct, independent signal
    # from the SC AND-gate. This is what makes H12/H16 genuinely (not formally)
    # testable in the lab loop.
    "em_coherence_score", "em_regime", "em_rabi_ev", "em_lifetime_fs",
})
```

Update the module docstring line that says "the only genuinely off-gate signal today is the EPW block" to also name the EM-coherence channel.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_closure.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/closure.py tests/lab_loop/test_closure.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: EM observables are off-gate (H12/H16 gain a real independent signal)'
```

---

### Task 4: EM as a lab-loop falsification metric + thread `use_em`

**Files:**
- Modify: `src/orme_lab/lab_loop/avenue.py`
- Modify: `src/orme_lab/lab_loop/runner.py`
- Test: `tests/lab_loop/test_runner_em.py`

**Interfaces:**
- Consumes: EM record fields (Task 2); `compute_em_coherence` (Task 2).
- Produces: `METRIC_RANGES["max_em_coherence_score"] = (0.0, 1.0)`; runner emits `max_em_coherence_score`; `run_avenue` threads `avenue.action.use_em`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_runner_em.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, METRIC_RANGES,
)
from orme_lab.lab_loop.runner import run_avenue


def _em_avenue(elements, use_em):
    return Avenue(
        id="em", tier=Tier.TIER1, description="em probe", targeted_hypothesis="H12",
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, use_epw=False, use_em=use_em, coupling_channel=None),
        falsification=FalsificationCondition("max_em_coherence_score", Comparator.LT, 0.05),
        predictor_invariants=("em_coherence_score",), provenance="t",
    )


def test_metric_range_declared():
    assert METRIC_RANGES["max_em_coherence_score"] == (0.0, 1.0)


def test_use_em_off_gives_zero_metric():
    m = run_avenue(_em_avenue(("Au",), use_em=False)).metrics
    assert m["max_em_coherence_score"] == 0.0     # None-safe -> 0.0 when not computed


def test_use_em_on_varies_by_element():
    au = run_avenue(_em_avenue(("Au",), use_em=True)).metrics["max_em_coherence_score"]
    pd = run_avenue(_em_avenue(("Pd",), use_em=True)).metrics["max_em_coherence_score"]
    assert au >= 0.0 and pd == 0.0                # Pd is dark; Au may light up
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_runner_em.py -v`
Expected: FAIL — `KeyError: 'max_em_coherence_score'`.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/lab_loop/avenue.py`, add to `METRIC_RANGES`:

```python
    "max_em_coherence_score": (0.0, 1.0),
```

In `src/orme_lab/lab_loop/runner.py`, add `"max_em_coherence_score"` to `_METRIC_KEYS`, add the reducer to `_metrics` (the `_max` helper already skips `None`):

```python
        "max_em_coherence_score": _max("em_coherence_score"),
```

In `run_avenue`, extend the `replace(...)` that already sets field/temperature so it also threads `use_em`:

```python
    run_config = replace(
        config,
        applied_field_t=action.applied_field_t,
        temperature_k=action.temperature_k,
        compute_em_coherence=action.use_em,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_runner_em.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/avenue.py src/orme_lab/lab_loop/runner.py tests/lab_loop/test_runner_em.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: max_em_coherence_score falsification metric; run_avenue threads use_em'
```

---

### Task 5: EPW seam — `epw_backend` param + honest `epw_status`

**Files:**
- Modify: `src/orme_lab/lab_loop/runner.py`
- Create: `tests/lab_loop/_fake_epw.py`
- Test: `tests/lab_loop/test_runner_epw.py`

**Interfaces:**
- Consumes: `EPWBackend`, `run_avenue` (existing).
- Produces: `run_avenue(..., epw_backend=None)`; `AvenueResult.epw_status: str` in `{"not_requested","ran","unavailable"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/_fake_epw.py
"""Test-only EPW double. NEVER shipped as production. Proves the seam plumbing
without QE binaries by returning a synthetic .a2f that flows through the real
spectral -> allen_dynes path."""
from orme_lab.backends import EPWBackend

# 11 whitespace columns per row: omega(meV) then the SAME a2f value in all 10
# smearing columns (so any configured smearing_column picks up signal). A
# triangular a2f peaked at 20 meV yields a finite positive lambda.
_SYNTHETIC_A2F = "\n".join(
    f"{omega:.4f} " + " ".join([f"{a2f:.4f}"] * 10)
    for omega, a2f in [
        (0.0, 0.0), (10.0, 0.5), (20.0, 1.0), (30.0, 0.5), (40.0, 0.0),
    ]
)


class FakeEPWRunner:
    def run(self, approx, cfg) -> str:
        return _SYNTHETIC_A2F


class FakeEPWBackend(EPWBackend):
    """EPWBackend whose availability is forced True and whose runner is the fake,
    so the pipeline SC_GAP gate (provides AND available) fires in tests."""
    def __init__(self):
        super().__init__(runner=FakeEPWRunner())

    @classmethod
    def available(cls) -> bool:
        return True
```

```python
# tests/lab_loop/test_runner_epw.py
from orme_lab.backends import EPWBackend
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import run_avenue
from tests.lab_loop._fake_epw import FakeEPWBackend


def _epw_avenue(use_epw):
    # compact_cluster: a monomer would be ApproximantUndefined -> not_applicable.
    return Avenue(
        id="epw", tier=Tier.TIER1, description="epw probe", targeted_hypothesis="H5",
        action=ActionSpec(("Pd",), ("compact_cluster",), ("low_spin",),
                          0.0, 20.0, use_epw=use_epw, use_em=False, coupling_channel=None),
        falsification=FalsificationCondition("max_sc_lambda", Comparator.GT, 0.1),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_not_requested_when_use_epw_false():
    res = run_avenue(_epw_avenue(use_epw=False))
    assert res.epw_status == "not_requested"


def test_ran_with_fake_backend():
    res = run_avenue(_epw_avenue(use_epw=True), epw_backend=FakeEPWBackend())
    assert res.epw_status == "ran"
    assert any(r.sc_source.startswith("epw") for r in res.records)
    assert any(r.sc_lambda is not None for r in res.records)


def test_unavailable_when_real_backend_and_no_binaries():
    # Real EPWBackend: available() hard-checks pw.x/ph.x/epw.x, absent here.
    res = run_avenue(_epw_avenue(use_epw=True), epw_backend=EPWBackend())
    assert res.epw_status == "unavailable"
    assert all(r.sc_lambda is None for r in res.records)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_runner_epw.py -v`
Expected: FAIL — `run_avenue` has no `epw_backend` param / `AvenueResult` has no `epw_status`.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/lab_loop/runner.py`, add `epw_status` to `AvenueResult`:

```python
@dataclass(frozen=True)
class AvenueResult:
    avenue: Avenue
    records: tuple[CandidateRecord, ...]
    metrics: dict[str, float]
    epw_status: str = "not_requested"
```

Change `run_avenue`'s signature to accept `epw_backend=None` and select the backend + compute status:

```python
def run_avenue(
    avenue: Avenue,
    config: LabConfig = DEFAULT_CONFIG,
    backend=None,
    screen_fn=run_screen,
    epw_backend=None,
) -> AvenueResult:
```

Inside `run_avenue`, after computing `run_config` and before calling `screen_fn`, choose the effective backend when EPW is requested:

```python
    use_epw = avenue.action.use_epw
    effective_backend = backend
    epw_available = False
    if use_epw and epw_backend is not None:
        epw_available = epw_backend.available()
        if epw_available:
            effective_backend = epw_backend
```

Pass `effective_backend` to `screen_fn(... backend=effective_backend)` (replace the existing `backend=backend`). After building `records_t`, compute the status:

```python
    if not use_epw:
        epw_status = "not_requested"
    elif any(r.sc_source.startswith("epw") for r in records_t):
        epw_status = "ran"
    else:
        epw_status = "unavailable"
```

Return it: `return AvenueResult(avenue=avenue, records=records_t, metrics=_metrics(records_t), epw_status=epw_status)`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_runner_epw.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/runner.py tests/lab_loop/_fake_epw.py tests/lab_loop/test_runner_epw.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: EPW seam in run_avenue (injectable backend, honest epw_status)'
```

---

### Task 6: Thread `epw_backend` through `run_loop`; digest surfaces unavailable

**Files:**
- Modify: `src/orme_lab/lab_loop/loop.py`
- Test: `tests/lab_loop/test_loop_epw.py`

**Interfaces:**
- Consumes: `run_avenue(..., epw_backend=...)`, `AvenueResult.epw_status` (Task 5).
- Produces: `run_loop(..., epw_backend=None)`; digest includes an EPW-unavailable line when any run avenue had `epw_status == "unavailable"`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_loop_epw.py
from orme_lab.backends import EPWBackend
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.loop import run_loop


def _av(use_epw):
    return Avenue(
        id="epw-unavail", tier=Tier.TIER1, description="d", targeted_hypothesis="H5",
        action=ActionSpec(("Pd",), ("compact_cluster",), ("low_spin",),
                          0.0, 20.0, use_epw=use_epw, use_em=False, coupling_channel=None),
        falsification=FalsificationCondition("max_sc_lambda", Comparator.GT, 0.1),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_digest_flags_epw_unavailable():
    rep = run_loop(OneShot([_av(use_epw=True)]), epw_backend=EPWBackend(),
                   loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                          convergence_rounds=1))
    assert "epw" in rep.digest.lower()
    assert "unavailable" in rep.digest.lower()
    assert "validated" not in rep.digest.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_loop_epw.py -v`
Expected: FAIL — `run_loop` has no `epw_backend` param.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/lab_loop/loop.py`, add `epw_backend=None` to `run_loop`'s signature, track statuses, and pass it to `run_avenue`:

```python
def run_loop(
    generator: AvenueGenerator,
    config: LabConfig = DEFAULT_CONFIG,
    loop_config: LoopConfig = DEFAULT_LOOP_CONFIG,
    backend=None,
    screen_fn=run_screen,
    epw_backend=None,
) -> LoopReport:
```

Add a collector near the other loop state (e.g. beside `skipped`):

```python
    epw_unavailable: list[str] = []
```

Where the avenue is run (the `run_avenue(best, ...)` call), pass the backend and record unavailability:

```python
        result = run_avenue(best, config=config, backend=backend,
                            screen_fn=screen_fn, epw_backend=epw_backend)
        if result.epw_status == "unavailable" and best.id not in epw_unavailable:
            epw_unavailable.append(best.id)
```

Pass `epw_unavailable` into `_digest(...)` (extend its signature with `epw_unavailable=None`) and append a section:

```python
    if epw_unavailable:
        lines.append("")
        lines.append("## EPW requested but binaries unavailable (sc_* NOT computed)")
        for aid in epw_unavailable:
            lines.append(f"- {aid}: pw.x/ph.x/epw.x not present; no electron-phonon Tc")
```

Update the `_digest(ledger, stopped_reason, skipped)` call site to also pass `epw_unavailable`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_loop_epw.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/loop.py tests/lab_loop/test_loop_epw.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: thread epw_backend through run_loop; digest surfaces EPW-unavailable honestly'
```

---

### Task 7: Keystone — H12 becomes genuinely testable; full-suite green

**Files:**
- Test: `tests/lab_loop/test_em_keystone.py`

**Interfaces:**
- Consumes: the whole EM path (Tasks 1–4).

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_em_keystone.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _h12(aid, elements):
    # H12 avenue: predictor is the off-gate EM signal -> non-tautological.
    # Falsifier fires (max_em_coherence_score < 0.05) when the EM channel is dark.
    return Avenue(
        id=aid, tier=Tier.TIER1, description="H12 EM coherence probe",
        targeted_hypothesis="H12",
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, use_epw=False, use_em=True, coupling_channel=None),
        falsification=FalsificationCondition("max_em_coherence_score", Comparator.LT, 0.05),
        predictor_invariants=("em_coherence_score",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_h12_predictor_is_not_tautological():
    # A Pd-only (dark) H12 avenue is judged on the merits, not dropped as tautological.
    rep = run_loop(OneShot([_h12("H12-pd", ("Pd",))]),
                   loop_config=LoopConfig(max_avenues=2, proposals_per_round=2,
                                          convergence_rounds=1))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts.get("H12-pd") != Verdict.TAUTOLOGICAL.value


def test_h12_kills_on_dark_panel_and_the_signal_is_real():
    # Pd is EM-dark -> max_em_coherence_score = 0.0 < 0.05 -> falsifier FIRES -> H12 killed.
    rep = run_loop(OneShot([_h12("H12-pd", ("Pd",))]),
                   loop_config=LoopConfig(max_avenues=2, proposals_per_round=2,
                                          convergence_rounds=1))
    rec = {r.avenue_id: r for r in rep.ledger.records}["H12-pd"]
    assert rec.verdict == Verdict.KILLED_HYPOTHESIS.value
    assert rec.metrics["max_em_coherence_score"] == 0.0
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python3 -m pytest tests/lab_loop/test_em_keystone.py -v`
Expected: if Tasks 1–4 are correct this may PASS immediately. If it FAILS, fix the implicated module — do NOT edit the test to match a bug.

- [ ] **Step 3: Make it pass**

No new production code should be required. If a test fails, treat it as a real defect in the EM path and fix there.

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: all prior tests plus the new EM/EPW tests PASS. If any pre-existing test asserted an exact `CandidateRecord`/CSV column set, update it to include the `em_*` columns (schema-widening, spec §6) — the values on the toy path are unchanged.

- [ ] **Step 5: Commit**

```bash
git add tests/lab_loop/test_em_keystone.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: keystone test — H12 genuinely testable via real off-gate EM signal'
```

---

## Self-Review (against the spec)

**Spec coverage:**
- §4.1 free-electron density + Pd-dark → Task 1.
- §4.2 config flag + pipeline EM computation → Task 2.
- §4.3 em_* record fields → Task 2.
- §4.4 off-gate closure + loop metric + thread use_em → Tasks 3, 4.
- §5 EPW seam (epw_backend, epw_status, FakeEPWBackend, unavailable) → Tasks 5, 6.
- §6 schema/determinism impact → Task 2 (docstring), Task 7 Step 4 (column-exact test updates).
- §7 honesty guards → Task 2 (EM≠SC comment), Task 5/6 (mock test-only, unavailable surfaced), Global Constraints.
- §8 test strategy items 1–10 → Tasks 1 (1), 2 (2,3), 3 (4), 4 (5), 7 (6), 5 (7,8,9), 7 Step 4 (10).

**Placeholder scan:** none — every step carries real code and a runnable command. §9 spec open-questions are resolved in the plan (density home = electromagnetic_coherence.py; em_regime needs no numeric companion — the score suffices; epw_backend is loop-API-only, not CLI, this cycle).

**Type consistency:** `em_coherence_score/em_regime/em_rabi_ev/em_lifetime_fs` identical across Tasks 2, 3, 4, 7. `epw_status` values `{"not_requested","ran","unavailable"}` identical across Tasks 5, 6. `run_avenue(..., epw_backend=None)` and `run_loop(..., epw_backend=None)` consistent. `max_em_coherence_score` consistent across Tasks 4, 7.

**Operator-reserved:** writes only under `src/orme_lab/`, `tests/`, `docs/superpowers/`. No evidence-classification change, no repo-visibility change, pushes nothing. Merge/push are operator decisions at finish time.
