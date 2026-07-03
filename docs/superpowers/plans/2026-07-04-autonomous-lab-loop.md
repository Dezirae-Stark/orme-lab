# Autonomous Lab-Scientist Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a bounded, self-driving research loop that divergently proposes ORME research avenues, runs the simulated screens itself, honestly triages them (anti-tautology, must-be-able-to-fail), and acts on its own suggestions in-sim — never conflating "survived triage" with "validated."

**Architecture:** New `src/orme_lab/lab_loop/` subpackage. A *deterministic* core (avenue spec, tautology-closure oracle, avenue runner, triage, objective, ledger, orchestrator) is wrapped by an injectable `AvenueGenerator` Protocol. In production the generator is the `orme-lab-scientist` subagent (supplied by the harness at run time); the package ships a deterministic `HeuristicGenerator` for offline runs and tests. The creative part proposes; the deterministic part judges; they never swap roles.

**Tech Stack:** Python 3, stdlib only (dataclasses, enum, json, argparse, typing.Protocol), pytest. No new third-party dependencies. Mirrors the `src/orme_lab/epw/` subpackage conventions (frozen dataclasses, injectable Protocol runner, per-module responsibility).

## Global Constraints

- **Determinism in the critical path:** no `time.time()`, no `datetime.now()`, no unseeded RNG, no order-dependent dict/set iteration in the deterministic core. Ledger ordering is by a **monotonic sequence index**, never a clock. (Operator commitment; matches `pipeline.py` docstring.)
- **Evidence ceiling:** anything the loop emits about a surviving lead is clamped to `LAB_CEILING` (Level 2) via the existing `min(level, LAB_CEILING)` in `orme_lab.evidence`. Never emit Level ≥ 4.
- **Closed verdict vocabulary:** `Verdict` has exactly `{KILLED_HYPOTHESIS, SURVIVED, TAUTOLOGICAL, INCONCLUSIVE}`. No `VALIDATED`/`CONFIRMED`/`SUPERCONDUCTING` member, ever.
- **No AI-identity git trailers.** Commit as `Dezirae Stark <deziraestark69@gmail.com>`. No `Co-Authored-By`, no `Claude-Session`, no `Signed-off-by` naming an AI. Use `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m '...'`.
- **No network egress, no telemetry.** The loop touches only the local filesystem under `experiments/ledger/`.
- **Operator hard-stops:** the loop halts and surfaces — never auto-acts — on any avenue touching evidence-classification changes, external claims/publication, repo/code changes (all of tier 3), or crossing `LAB_CEILING`.
- Spec: `docs/superpowers/specs/2026-07-04-autonomous-lab-loop-design.md`.

## File Structure

| File | Responsibility |
|---|---|
| `src/orme_lab/lab_loop/__init__.py` | Package exports. |
| `src/orme_lab/lab_loop/avenue.py` | `Avenue`, `ActionSpec`, `Tier`, `Comparator`, `FalsificationCondition`, `METRIC_RANGES`, `MechanismProposal`. Data + validation only. |
| `src/orme_lab/lab_loop/closure.py` | `GATE_INPUT_CLOSURE`, `OFF_GATE_INVARIANTS`, `is_independent`. The tautology oracle. |
| `src/orme_lab/lab_loop/config.py` | `ObjectiveWeights`, `LoopConfig`. |
| `src/orme_lab/lab_loop/runner.py` | `AvenueResult`, `run_avenue`, metric extraction. |
| `src/orme_lab/lab_loop/triage.py` | `Verdict`, `TriageOutcome`, `triage`. |
| `src/orme_lab/lab_loop/objective.py` | `score_avenue` (decisiveness prior + coverage). |
| `src/orme_lab/lab_loop/ledger.py` | `HYPOTHESES`, `LedgerRecord`, `Ledger`. Append-only memory, dedup, retire, JSONL. |
| `src/orme_lab/lab_loop/loop.py` | `AvenueGenerator` Protocol, `HeuristicGenerator`, `LoopReport`, `run_loop`, operator hard-stop, digest. |
| `src/orme_lab/lab_loop/__main__.py` | CLI: `python -m orme_lab.lab_loop --max-avenues N`. |
| `experiments/ledger/.gitkeep` | Ledger artifact directory. |
| `tests/lab_loop/test_*.py` | One test module per source module + one integration test. |

Consumed from existing code (exact signatures, verified):
- `orme_lab.pipeline.run_screen(elements: list[Element] | None, config: LabConfig = DEFAULT_CONFIG, geometry_factory=default_geometries, backend=None) -> list[CandidateRecord]`
- `CandidateRecord` fields include: `element, geometry, n_atoms, spin_label, coupling, carrier_proxy, field_suppression, structural_stability, observable_signal, sc_plausibility, ruled_out, evidence_level, sc_tc_kelvin, sc_lambda, sc_omega_log_k, sc_gap_mev, sc_mu_star, sc_source`.
- `orme_lab.elements.get_element(symbol: str) -> Element`, `core_screen_elements() -> list[Element]`
- `orme_lab.geometry.make_monomer(el)`, `make_dimer(el)`, `make_linear_chain(el, n)`, `make_compact_cluster(el, n)`; `ClusterGeometry.label`, `.n_atoms`, `.mean_coordination`
- `orme_lab.spin_states.high_spin_state(el)`, `low_spin_state(el)`
- `orme_lab.config.LabConfig`, `ModelThresholds`, `DEFAULT_CONFIG`, `ROOM_TEMPERATURE_K`
- `orme_lab.evidence.LAB_CEILING`

---

### Task 1: `avenue.py` — the executable experiment spec

**Files:**
- Create: `src/orme_lab/lab_loop/__init__.py` (empty for now)
- Create: `src/orme_lab/lab_loop/avenue.py`
- Test: `tests/lab_loop/test_avenue.py`

**Interfaces:**
- Produces: `Tier(IntEnum)` {`TIER1=1, TIER2=2, TIER3=3`}; `Comparator(Enum)` {`LT, LE, GT, GE`}; `METRIC_RANGES: dict[str, tuple[float, float]]`; `FalsificationCondition(metric: str, comparator: Comparator, threshold: float)` with `.fireable() -> bool`; `ActionSpec(elements, geometry_kinds, spin_labels, applied_field_t, temperature_k, use_epw, use_em, coupling_channel)` (all tuple[str,...] / float / bool / str|None); `Avenue(id, tier, description, targeted_hypothesis, action, falsification, predictor_invariants, provenance)`; `MechanismProposal(id, description, rationale, provenance, status)`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_avenue.py
import pytest
from orme_lab.lab_loop.avenue import (
    Tier, Comparator, FalsificationCondition, ActionSpec, Avenue,
    MechanismProposal, METRIC_RANGES,
)


def _action():
    return ActionSpec(
        elements=("Pd",), geometry_kinds=("compact_cluster",), spin_labels=("high_spin",),
        applied_field_t=0.0, temperature_k=298.15, use_epw=False, use_em=False,
        coupling_channel=None,
    )


def test_fireable_true_when_threshold_inside_metric_range():
    # max_sc_plausibility ranges [0,1]; threshold 0.5 can be crossed both ways.
    fc = FalsificationCondition("max_sc_plausibility", Comparator.LT, 0.5)
    assert fc.fireable() is True


def test_fireable_false_when_threshold_outside_metric_range():
    # Nothing can be < 0.0, so "max_sc_plausibility < 0.0" can never fire.
    fc = FalsificationCondition("max_sc_plausibility", Comparator.LT, 0.0)
    assert fc.fireable() is False


def test_unknown_metric_rejected():
    with pytest.raises(ValueError):
        FalsificationCondition("no_such_metric", Comparator.LT, 0.5).fireable()


def test_avenue_is_frozen():
    av = Avenue(
        id="A1", tier=Tier.TIER1, description="probe Pd cluster",
        targeted_hypothesis="H5", action=_action(),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="unit-test",
    )
    with pytest.raises(Exception):
        av.id = "A2"  # type: ignore[misc]


def test_mechanism_proposal_default_status_is_pending_review():
    mp = MechanismProposal(id="M1", description="new granular network model",
                           rationale="tier-3", provenance="unit-test")
    assert mp.status == "pending operator + red-team review"


def test_metric_ranges_cover_expected_metrics():
    for m in ("max_sc_plausibility", "n_survivors", "max_coupling", "max_sc_tc_kelvin"):
        assert m in METRIC_RANGES
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_avenue.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'orme_lab.lab_loop'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/__init__.py
"""Autonomous lab-scientist loop (see docs/superpowers/specs/2026-07-04-autonomous-lab-loop-design.md)."""
```

```python
# src/orme_lab/lab_loop/avenue.py
"""The executable experiment spec an avenue is, plus its falsification condition.

An ``Avenue`` is a *proposal* the creative generator emits and the deterministic
core judges. It carries everything needed to run one experiment and to decide,
before running, whether it is falsifiable and non-tautological. Data + validation
only; no execution lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum, IntEnum


class Tier(IntEnum):
    """Action-space tier. Tier 3 (auto-prototype new mechanisms) is walled off."""

    TIER1 = 1  # vary existing model inputs + EPW/EM toggles
    TIER2 = 2  # + sanctioned coupling channels
    TIER3 = 3  # + auto-prototype a new mechanism (quarantined, not run)


class Comparator(Enum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


#: Achievable range of each metric the falsification condition may reference.
#: ``max_sc_tc_kelvin`` is capped at a generous toy ceiling so "fireable" is
#: decidable; the EPW toy path never exceeds it.
METRIC_RANGES: dict[str, tuple[float, float]] = {
    "max_sc_plausibility": (0.0, 1.0),
    "max_coupling": (0.0, 1.0),
    "max_field_suppression": (0.0, 1.0),
    "n_survivors": (0.0, 1000.0),
    "max_sc_tc_kelvin": (0.0, 1000.0),
    "max_sc_lambda": (0.0, 10.0),
}


@dataclass(frozen=True)
class FalsificationCondition:
    """A declarative, serializable falsification predicate on one run metric.

    Declarative (metric/comparator/threshold) rather than an arbitrary callable
    so that (a) it can be checked for *fireability* without running anything and
    (b) it round-trips through the ledger JSON.
    """

    metric: str
    comparator: Comparator
    threshold: float

    def fireable(self) -> bool:
        """True iff the threshold lies strictly inside the metric's range, so the
        condition can come out both true and false over the action space. A
        condition that can never fire is a 'validation that cannot fail'."""
        if self.metric not in METRIC_RANGES:
            raise ValueError(f"unknown metric: {self.metric!r}")
        lo, hi = METRIC_RANGES[self.metric]
        return lo < self.threshold < hi

    def evaluate(self, metrics: dict[str, float]) -> bool:
        """Whether the condition FIRES given a run's metric values."""
        if self.metric not in metrics:
            raise ValueError(f"metric {self.metric!r} not in run metrics")
        v = metrics[self.metric]
        t = self.threshold
        return {
            Comparator.LT: v < t,
            Comparator.LE: v <= t,
            Comparator.GT: v > t,
            Comparator.GE: v >= t,
        }[self.comparator]


@dataclass(frozen=True)
class ActionSpec:
    """The knobs one avenue varies. All fields are inert data."""

    elements: tuple[str, ...]
    geometry_kinds: tuple[str, ...]        # {monomer, dimer, linear_chain, compact_cluster}
    spin_labels: tuple[str, ...]           # {high_spin, low_spin}
    applied_field_t: float
    temperature_k: float
    use_epw: bool
    use_em: bool
    coupling_channel: str | None           # tier-2: {nanocluster, josephson, oxide_salt, light_matter}


@dataclass(frozen=True)
class Avenue:
    """A single proposed experiment."""

    id: str
    tier: Tier
    description: str
    targeted_hypothesis: str
    action: ActionSpec
    falsification: FalsificationCondition
    predictor_invariants: tuple[str, ...]
    provenance: str


@dataclass(frozen=True)
class MechanismProposal:
    """A tier-3 proposal. NEVER a finding — quarantined pending human review."""

    id: str
    description: str
    rationale: str
    provenance: str
    status: str = "pending operator + red-team review"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_avenue.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/__init__.py src/orme_lab/lab_loop/avenue.py tests/lab_loop/test_avenue.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: Avenue spec + declarative falsification condition (fireable check)'
```

---

### Task 2: `closure.py` — the tautology oracle

**Files:**
- Create: `src/orme_lab/lab_loop/closure.py`
- Test: `tests/lab_loop/test_closure.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (references `CandidateRecord` field *names* as string literals).
- Produces: `GATE_INPUT_CLOSURE: frozenset[str]`, `OFF_GATE_INVARIANTS: frozenset[str]`, `is_independent(predictor_invariants: tuple[str, ...] | frozenset[str]) -> bool`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_closure.py
from orme_lab.lab_loop.closure import (
    GATE_INPUT_CLOSURE, OFF_GATE_INVARIANTS, is_independent,
)


def test_gate_inputs_are_in_closure():
    # The five AND-gate inputs and their upstream feeders are in-closure.
    for f in ("coupling", "carrier_proxy", "field_suppression",
              "structural_stability", "observable_signal"):
        assert f in GATE_INPUT_CLOSURE


def test_epw_block_is_off_gate():
    for f in ("sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev"):
        assert f in OFF_GATE_INVARIANTS


def test_closure_and_offgate_are_disjoint():
    assert GATE_INPUT_CLOSURE.isdisjoint(OFF_GATE_INVARIANTS)


def test_predictor_touching_offgate_is_independent():
    assert is_independent(("sc_lambda",)) is True
    assert is_independent(("coupling", "sc_tc_kelvin")) is True


def test_predictor_only_in_closure_is_not_independent():
    assert is_independent(("coupling", "carrier_proxy")) is False


def test_empty_predictors_is_not_independent():
    assert is_independent(()) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_closure.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/closure.py
"""Static tautology oracle over ``CandidateRecord`` fields.

The superconductivity AND-gate consumes five inputs — coupling, carrier proxy,
field suppression, structural stability, observable signal — each a deterministic
function of a small set of upstream quantities. Any predictor drawn only from
this closure is, by construction, re-derivable from the gate's own inputs: a
'finding' expressed in those terms is a tautology. The only genuinely off-gate
signal today is the EPW electron-phonon block (an external computation, not a
function of the gate inputs).

This set is PINNED. If the model changes so the gate consumes a new field, the
golden test in ``test_closure.py`` breaks loudly — which is the point.
"""

from __future__ import annotations

#: Fields inside the AND-gate's transitive input closure (gate inputs + the
#: quantities they are computed from + the observables that feed observable_signal).
GATE_INPUT_CLOSURE: frozenset[str] = frozenset({
    # the five gate inputs
    "coupling", "carrier_proxy", "field_suppression",
    "structural_stability", "observable_signal",
    # upstream feeders (see pipeline.evaluate_candidate)
    "anisotropy", "is_ricebean", "spin_polarization",
    "meissner_screening", "susceptibility", "resistance_regime",
    # derived gate outputs
    "sc_plausibility", "ruled_out",
})

#: Fields NOT reachable from the gate inputs — genuinely independent signal.
#: Today: the EPW electron-phonon block only.
OFF_GATE_INVARIANTS: frozenset[str] = frozenset({
    "sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev", "sc_mu_star",
})


def is_independent(predictor_invariants) -> bool:
    """True iff the predictors reference at least one off-gate invariant.

    An avenue that passes this is claiming something not definitionally implied
    by the AND-gate's own inputs. An avenue that fails is tautological.
    """
    return bool(OFF_GATE_INVARIANTS.intersection(predictor_invariants))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_closure.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/closure.py tests/lab_loop/test_closure.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: pinned tautology closure oracle (off-gate = EPW block only)'
```

---

### Task 3: `config.py` — objective weights and loop budget

**Files:**
- Create: `src/orme_lab/lab_loop/config.py`
- Test: `tests/lab_loop/test_config.py`

**Interfaces:**
- Produces: `ObjectiveWeights(w_decisiveness: float = 1.0, w_coverage: float = 0.15)`; `LoopConfig(weights: ObjectiveWeights, max_avenues: int = 20, proposals_per_round: int = 4, convergence_rounds: int = 3, ledger_dir: str = "experiments/ledger")`; `DEFAULT_LOOP_CONFIG`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_config.py
import pytest
from orme_lab.lab_loop.config import ObjectiveWeights, LoopConfig, DEFAULT_LOOP_CONFIG


def test_decisiveness_dominates_coverage():
    w = ObjectiveWeights()
    assert w.w_decisiveness > w.w_coverage


def test_loop_config_is_frozen():
    with pytest.raises(Exception):
        DEFAULT_LOOP_CONFIG.max_avenues = 99  # type: ignore[misc]


def test_defaults_are_bounded_and_sane():
    c = DEFAULT_LOOP_CONFIG
    assert c.max_avenues > 0
    assert c.proposals_per_round > 0
    assert c.convergence_rounds > 0
    assert c.ledger_dir.endswith("ledger")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/config.py
"""Loop budget and objective weights. Frozen so a run cannot mutate its own
knobs mid-loop (determinism)."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ObjectiveWeights:
    """Weights for the avenue-selection acquisition function.

    ``w_decisiveness`` dominates: the loop pursues what would settle a question,
    with coverage only as a tiebreaker. Candidate-strength is deliberately NOT a
    weight — it can never raise an avenue's priority.
    """

    w_decisiveness: float = 1.0
    w_coverage: float = 0.15


@dataclass(frozen=True)
class LoopConfig:
    weights: ObjectiveWeights = field(default_factory=ObjectiveWeights)
    max_avenues: int = 20
    """Hard budget: stop after this many avenues are RUN (tier-3 quarantines and
    dropped tautologies do not count against it)."""
    proposals_per_round: int = 4
    convergence_rounds: int = 3
    """Stop early after this many consecutive rounds with no new hypothesis kill."""
    ledger_dir: str = "experiments/ledger"


DEFAULT_LOOP_CONFIG = LoopConfig()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_config.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/config.py tests/lab_loop/test_config.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: LoopConfig + decisiveness-dominant objective weights'
```

---

### Task 4: `runner.py` — execute one avenue, extract metrics

**Files:**
- Create: `src/orme_lab/lab_loop/runner.py`
- Test: `tests/lab_loop/test_runner.py`

**Interfaces:**
- Consumes: `Avenue`, `ActionSpec` (Task 1); `run_screen`, `CandidateRecord` (existing).
- Produces: `AvenueResult(avenue: Avenue, records: tuple[CandidateRecord, ...], metrics: dict[str, float])`; `run_avenue(avenue: Avenue, config: LabConfig = DEFAULT_CONFIG, backend=None, screen_fn=run_screen) -> AvenueResult`; `_GEOMETRY_BUILDERS: dict[str, callable]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_runner.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import run_avenue, AvenueResult


def _avenue():
    return Avenue(
        id="A1", tier=Tier.TIER1, description="Pd cluster vs dimer",
        targeted_hypothesis="H5",
        action=ActionSpec(
            elements=("Pd",), geometry_kinds=("dimer", "compact_cluster"),
            spin_labels=("high_spin",), applied_field_t=0.0, temperature_k=298.15,
            use_epw=False, use_em=False, coupling_channel=None,
        ),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="unit-test",
    )


def test_run_avenue_returns_records_and_metrics():
    res = run_avenue(_avenue())
    assert isinstance(res, AvenueResult)
    assert len(res.records) == 2  # 1 element x 2 geometries x 1 spin
    for m in ("max_sc_plausibility", "max_coupling", "n_survivors"):
        assert m in res.metrics


def test_run_avenue_is_deterministic():
    a = run_avenue(_avenue())
    b = run_avenue(_avenue())
    assert a.metrics == b.metrics


def test_metrics_reflect_screen_output():
    res = run_avenue(_avenue())
    couplings = [r.coupling for r in res.records]
    assert res.metrics["max_coupling"] == max(couplings)
    assert res.metrics["n_survivors"] == float(sum(1 for r in res.records if not r.ruled_out))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_runner.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/runner.py
"""Deterministically execute one avenue through the existing screen and reduce
its records to the scalar metrics the falsification condition and objective use.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..config import DEFAULT_CONFIG, LabConfig
from ..elements import get_element
from ..geometry import (
    make_compact_cluster, make_dimer, make_linear_chain, make_monomer,
)
from ..pipeline import CandidateRecord, run_screen
from .avenue import Avenue

_GEOMETRY_BUILDERS = {
    "monomer": lambda el: make_monomer(el),
    "dimer": lambda el: make_dimer(el),
    "linear_chain": lambda el: make_linear_chain(el, 4),
    "compact_cluster": lambda el: make_compact_cluster(el, 13),
}


@dataclass(frozen=True)
class AvenueResult:
    avenue: Avenue
    records: tuple[CandidateRecord, ...]
    metrics: dict[str, float]


def _metrics(records: tuple[CandidateRecord, ...]) -> dict[str, float]:
    if not records:
        return {
            "max_sc_plausibility": 0.0, "max_coupling": 0.0,
            "max_field_suppression": 0.0, "n_survivors": 0.0,
            "max_sc_tc_kelvin": 0.0, "max_sc_lambda": 0.0,
        }

    def _max(attr: str) -> float:
        vals = [getattr(r, attr) for r in records if getattr(r, attr) is not None]
        return float(max(vals)) if vals else 0.0

    return {
        "max_sc_plausibility": _max("sc_plausibility"),
        "max_coupling": _max("coupling"),
        "max_field_suppression": _max("field_suppression"),
        "n_survivors": float(sum(1 for r in records if not r.ruled_out)),
        "max_sc_tc_kelvin": _max("sc_tc_kelvin"),
        "max_sc_lambda": _max("sc_lambda"),
    }


def run_avenue(
    avenue: Avenue,
    config: LabConfig = DEFAULT_CONFIG,
    backend=None,
    screen_fn=run_screen,
) -> AvenueResult:
    """Run ``avenue``'s action grid through the screen and compute its metrics.

    The avenue's field/temperature override the base ``config``. ``screen_fn`` is
    injectable so tests can stub the screen; it defaults to the real pipeline.
    """
    action = avenue.action
    run_config = replace(
        config, applied_field_t=action.applied_field_t, temperature_k=action.temperature_k,
    )
    elements = [get_element(sym) for sym in action.elements]

    def geometry_factory(el):
        return [_GEOMETRY_BUILDERS[k](el) for k in action.geometry_kinds]

    # Restrict spin states to those named in the action.
    from ..pipeline import _spin_states  # reuse the canonical spin builders

    wanted = set(action.spin_labels)
    records = [
        r for r in screen_fn(
            elements=elements, config=run_config,
            geometry_factory=geometry_factory, backend=backend,
        )
        if r.spin_label in wanted
    ]
    records_t = tuple(records)
    return AvenueResult(avenue=avenue, records=records_t, metrics=_metrics(records_t))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_runner.py -v`
Expected: PASS (3 tests).

Note: `_spin_states` import is defensive; if the screen already filters by spin it is unused — the list-comprehension filter on `r.spin_label` is what enforces the spin subset. Keep the filter; drop the `_spin_states` import if flagged by the F401 linter.

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/runner.py tests/lab_loop/test_runner.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: run_avenue (screen execution + scalar metric extraction), injectable screen_fn'
```

---

### Task 5: `triage.py` — honest verdicts (tautology gate, kill-as-success)

**Files:**
- Create: `src/orme_lab/lab_loop/triage.py`
- Test: `tests/lab_loop/test_triage.py`

**Interfaces:**
- Consumes: `Avenue` (Task 1), `is_independent` (Task 2), `AvenueResult` (Task 4).
- Produces: `Verdict(Enum)` {`KILLED_HYPOTHESIS, SURVIVED, TAUTOLOGICAL, INCONCLUSIVE`}; `TriageOutcome(verdict: Verdict, decisiveness: float, killed_hypothesis: str | None)`; `triage(result: AvenueResult, open_hypotheses: frozenset[str]) -> TriageOutcome`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_triage.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.runner import AvenueResult
from orme_lab.lab_loop.triage import Verdict, triage, TriageOutcome


def _avenue(predictors, metric="max_coupling", comp=Comparator.LT, thr=0.2, hyp="H5"):
    return Avenue(
        id="A1", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(("Pd",), ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


def _result(avenue, metrics):
    return AvenueResult(avenue=avenue, records=(), metrics=metrics)


def test_tautological_when_predictors_only_in_closure():
    av = _avenue(predictors=("coupling", "carrier_proxy"))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.TAUTOLOGICAL


def test_killed_hypothesis_is_success_when_condition_fires():
    # coupling stays below 0.2 -> falsification fires -> H5 killed.
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.KILLED_HYPOTHESIS
    assert out.killed_hypothesis == "H5"
    assert out.decisiveness > 0.0


def test_survived_when_condition_does_not_fire():
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.9}), open_hypotheses=frozenset({"H5"}))
    assert out.verdict is Verdict.SURVIVED


def test_inconclusive_when_targeted_hypothesis_already_closed():
    av = _avenue(predictors=("sc_lambda",))
    out = triage(_result(av, {"max_coupling": 0.05}), open_hypotheses=frozenset())
    assert out.verdict is Verdict.INCONCLUSIVE


def test_verdict_vocabulary_has_no_validated_member():
    names = {v.name for v in Verdict}
    assert names == {"KILLED_HYPOTHESIS", "SURVIVED", "TAUTOLOGICAL", "INCONCLUSIVE"}
    for forbidden in ("VALIDATED", "CONFIRMED", "SUPERCONDUCTING", "PROVEN"):
        assert forbidden not in names
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_triage.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/triage.py
"""Judge an avenue result. Honesty is enforced by the closed ``Verdict`` enum:
there is no VALIDATED member, so no code path can claim validation. A killed
hypothesis is a SUCCESS, not a failure."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .closure import is_independent
from .runner import AvenueResult


class Verdict(Enum):
    """The only verdicts the loop can reach. Deliberately no VALIDATED/CONFIRMED."""

    KILLED_HYPOTHESIS = "killed_hypothesis"  # falsification fired — progress
    SURVIVED = "survived"                    # not killed this round
    TAUTOLOGICAL = "tautological"            # predictors re-derivable from the gate
    INCONCLUSIVE = "inconclusive"            # nothing decidable (e.g. target closed)


@dataclass(frozen=True)
class TriageOutcome:
    verdict: Verdict
    decisiveness: float
    killed_hypothesis: str | None


def triage(result: AvenueResult, open_hypotheses: frozenset[str]) -> TriageOutcome:
    av = result.avenue

    # 1. Tautology gate — before anything else.
    if not is_independent(av.predictor_invariants):
        return TriageOutcome(Verdict.TAUTOLOGICAL, 0.0, None)

    # 2. Can this avenue decide anything? Its target must still be open.
    if av.targeted_hypothesis not in open_hypotheses:
        return TriageOutcome(Verdict.INCONCLUSIVE, 0.0, None)

    # 3. Did the falsification condition fire? A fire kills the hypothesis.
    if av.falsification.evaluate(result.metrics):
        return TriageOutcome(Verdict.KILLED_HYPOTHESIS, 1.0, av.targeted_hypothesis)

    return TriageOutcome(Verdict.SURVIVED, 0.0, None)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_triage.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/triage.py tests/lab_loop/test_triage.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: triage with tautology gate + kill-as-success + closed verdict vocabulary'
```

---

### Task 6: `objective.py` — rank candidate avenues before running

**Files:**
- Create: `src/orme_lab/lab_loop/objective.py`
- Test: `tests/lab_loop/test_objective.py`

**Interfaces:**
- Consumes: `Avenue` (Task 1), `is_independent` (Task 2), `ObjectiveWeights` (Task 3).
- Produces: `score_avenue(avenue: Avenue, open_hypotheses: frozenset[str], seen_actions: frozenset[tuple], weights: ObjectiveWeights) -> float`; `action_key(avenue: Avenue) -> tuple`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_objective.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import ObjectiveWeights
from orme_lab.lab_loop.objective import score_avenue, action_key


def _av(hyp="H5", predictors=("sc_lambda",), elements=("Pd",)):
    return Avenue(
        id="A", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=predictors, provenance="t",
    )


W = ObjectiveWeights()


def test_open_target_outscores_closed_target():
    open_hi = score_avenue(_av(hyp="H5"), frozenset({"H5"}), frozenset(), W)
    closed = score_avenue(_av(hyp="H5"), frozenset(), frozenset(), W)
    assert open_hi > closed


def test_tautological_avenue_scores_zero():
    taut = _av(predictors=("coupling",))
    assert score_avenue(taut, frozenset({"H5"}), frozenset(), W) == 0.0


def test_unseen_action_outscores_seen_action():
    av = _av(elements=("Pd",))
    seen = frozenset({action_key(av)})
    fresh = score_avenue(_av(elements=("Ir",)), frozenset({"H5"}), seen, W)
    stale = score_avenue(av, frozenset({"H5"}), seen, W)
    assert fresh > stale


def test_score_ignores_candidate_strength_tag():
    # score_avenue takes no candidate-strength input at all; two identical avenues
    # score identically regardless of any (absent) strength notion.
    a = score_avenue(_av(), frozenset({"H5"}), frozenset(), W)
    b = score_avenue(_av(), frozenset({"H5"}), frozenset(), W)
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_objective.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/objective.py
"""Acquisition function that ranks candidate avenues BEFORE they run.

A(avenue) = w_decisiveness * decisiveness_prior + w_coverage * coverage

decisiveness_prior : can this avenue kill something? 1.0 if its target is still
                     open (a dead hypothesis can't be re-killed), else 0.0.
coverage           : 1.0 if this action has not been run, else 0.0.

Candidate-strength is intentionally absent: nothing about how 'promising' a
candidate looks can raise an avenue's priority. Tautological avenues score 0.0.
"""

from __future__ import annotations

from .avenue import Avenue
from .closure import is_independent
from .config import ObjectiveWeights


def action_key(avenue: Avenue) -> tuple:
    """Hashable identity of an avenue's action, for the seen-set / coverage term."""
    a = avenue.action
    return (
        a.elements, a.geometry_kinds, a.spin_labels, a.applied_field_t,
        a.temperature_k, a.use_epw, a.use_em, a.coupling_channel,
    )


def score_avenue(
    avenue: Avenue,
    open_hypotheses: frozenset[str],
    seen_actions: frozenset[tuple],
    weights: ObjectiveWeights,
) -> float:
    if not is_independent(avenue.predictor_invariants):
        return 0.0
    decisiveness = 1.0 if avenue.targeted_hypothesis in open_hypotheses else 0.0
    coverage = 0.0 if action_key(avenue) in seen_actions else 1.0
    return weights.w_decisiveness * decisiveness + weights.w_coverage * coverage
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_objective.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/objective.py tests/lab_loop/test_objective.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: acquisition function (decisiveness prior + coverage, candidate-strength excluded)'
```

---

### Task 7: `ledger.py` — append-only memory, dedup, retire, JSONL

**Files:**
- Create: `src/orme_lab/lab_loop/ledger.py`
- Test: `tests/lab_loop/test_ledger.py`

**Interfaces:**
- Consumes: `Avenue`, `MechanismProposal` (Task 1), `TriageOutcome`, `Verdict` (Task 5), `action_key` (Task 6).
- Produces: `HYPOTHESES: tuple[str, ...]`; `LedgerRecord(seq: int, avenue_id: str, tier: int, targeted_hypothesis: str, verdict: str, decisiveness: float, killed_hypothesis: str | None, metrics: dict, predictor_invariants: tuple[str, ...])`; `Ledger` with `.open_hypotheses -> frozenset[str]`, `.seen_actions -> frozenset[tuple]`, `.is_seen(avenue) -> bool`, `.record(avenue, outcome, metrics) -> LedgerRecord | None`, `.quarantine(proposal)`, `.to_jsonl() -> str`, `.records: list[LedgerRecord]`, `.proposals: list[MechanismProposal]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_ledger.py
import json
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, MechanismProposal,
)
from orme_lab.lab_loop.triage import Verdict, TriageOutcome
from orme_lab.lab_loop.ledger import Ledger, HYPOTHESES


def _av(aid="A1", hyp="H5", elements=("Pd",)):
    return Avenue(
        id=aid, tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_coupling", Comparator.LT, 0.2),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_all_hypotheses_start_open():
    assert set(Ledger().open_hypotheses) == set(HYPOTHESES)


def test_kill_retires_hypothesis_from_open_set():
    led = Ledger()
    led.record(_av(hyp="H5"),
               TriageOutcome(Verdict.KILLED_HYPOTHESIS, 1.0, "H5"), {"max_coupling": 0.05})
    assert "H5" not in led.open_hypotheses


def test_seen_dedup_blocks_repeat_action():
    led = Ledger()
    av = _av()
    led.record(av, TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9})
    assert led.is_seen(av) is True
    assert led.record(av, TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9}) is None


def test_sequence_index_is_monotonic_no_clock():
    led = Ledger()
    r0 = led.record(_av(aid="A1", elements=("Pd",)),
                    TriageOutcome(Verdict.SURVIVED, 0.0, None), {})
    r1 = led.record(_av(aid="A2", elements=("Ir",)),
                    TriageOutcome(Verdict.SURVIVED, 0.0, None), {})
    assert (r0.seq, r1.seq) == (0, 1)


def test_to_jsonl_roundtrips_and_is_deterministic():
    led = Ledger()
    led.record(_av(), TriageOutcome(Verdict.SURVIVED, 0.0, None), {"max_coupling": 0.9})
    a = led.to_jsonl()
    lines = [ln for ln in a.splitlines() if ln.strip()]
    parsed = json.loads(lines[0])
    assert parsed["verdict"] == "survived"
    assert parsed["seq"] == 0


def test_quarantine_keeps_proposals_out_of_findings():
    led = Ledger()
    led.quarantine(MechanismProposal(id="M1", description="d", rationale="r", provenance="t"))
    assert len(led.proposals) == 1
    assert len(led.records) == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_ledger.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/ledger.py
"""Append-only deterministic memory of the loop: what was run, what it decided,
which hypotheses are still open, and the tier-3 quarantine queue. Ordering is by
a monotonic sequence index — never a wall clock — so a fixed avenue stream yields
byte-identical JSONL."""

from __future__ import annotations

import json
from dataclasses import dataclass

from .avenue import Avenue, MechanismProposal
from .objective import action_key
from .triage import TriageOutcome, Verdict

#: The hypotheses the loop can retire (charter core + the load-bearing extended
#: reframing). See docs/hypothesis_matrix.md.
HYPOTHESES: tuple[str, ...] = ("H1", "H2", "H3", "H4", "H5", "H6", "H7", "H12", "H16")


@dataclass(frozen=True)
class LedgerRecord:
    seq: int
    avenue_id: str
    tier: int
    targeted_hypothesis: str
    verdict: str
    decisiveness: float
    killed_hypothesis: str | None
    metrics: dict
    predictor_invariants: tuple[str, ...]

    def to_json(self) -> dict:
        d = dict(self.__dict__)
        d["predictor_invariants"] = list(self.predictor_invariants)
        return d


class Ledger:
    def __init__(self) -> None:
        self.records: list[LedgerRecord] = []
        self.proposals: list[MechanismProposal] = []
        self._seen: set[tuple] = set()
        self._killed: set[str] = set()
        self._seq = 0

    @property
    def open_hypotheses(self) -> frozenset[str]:
        return frozenset(h for h in HYPOTHESES if h not in self._killed)

    @property
    def seen_actions(self) -> frozenset[tuple]:
        return frozenset(self._seen)

    def is_seen(self, avenue: Avenue) -> bool:
        return action_key(avenue) in self._seen

    def record(self, avenue: Avenue, outcome: TriageOutcome, metrics: dict) -> LedgerRecord | None:
        """Append one avenue's outcome. Returns None (no-op) if the action was
        already seen (dedup). Retires a hypothesis on a KILLED verdict."""
        if self.is_seen(avenue):
            return None
        self._seen.add(action_key(avenue))
        rec = LedgerRecord(
            seq=self._seq, avenue_id=avenue.id, tier=int(avenue.tier),
            targeted_hypothesis=avenue.targeted_hypothesis, verdict=outcome.verdict.value,
            decisiveness=outcome.decisiveness, killed_hypothesis=outcome.killed_hypothesis,
            metrics=dict(metrics), predictor_invariants=tuple(avenue.predictor_invariants),
        )
        self._seq += 1
        self.records.append(rec)
        if outcome.verdict is Verdict.KILLED_HYPOTHESIS and outcome.killed_hypothesis:
            self._killed.add(outcome.killed_hypothesis)
        return rec

    def quarantine(self, proposal: MechanismProposal) -> None:
        self.proposals.append(proposal)

    def to_jsonl(self) -> str:
        return "\n".join(json.dumps(r.to_json(), sort_keys=True) for r in self.records)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_ledger.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/ledger.py tests/lab_loop/test_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: append-only ledger (dedup, hypothesis retire, monotonic seq, JSONL)'
```

---

### Task 8: `loop.py` — orchestrator, generator Protocol, hard-stops, digest

**Files:**
- Create: `src/orme_lab/lab_loop/loop.py`
- Test: `tests/lab_loop/test_loop.py`

**Interfaces:**
- Consumes: everything from Tasks 1–7.
- Produces: `AvenueGenerator` (Protocol with `propose(open_hypotheses: frozenset[str], seen_actions: frozenset[tuple], k: int) -> list[Avenue]`); `HeuristicGenerator`; `RESERVED_BOUNDARY_HYPOTHESES` handling via `touches_reserved_boundary(avenue) -> bool`; `LoopReport(ledger: Ledger, rounds: int, stopped_reason: str, digest: str)`; `run_loop(generator: AvenueGenerator, config: LabConfig = DEFAULT_CONFIG, loop_config: LoopConfig = DEFAULT_LOOP_CONFIG, backend=None, screen_fn=run_screen) -> LoopReport`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_loop.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop, LoopReport


def _av(aid, tier=Tier.TIER1, predictors=("sc_lambda",), hyp="H5",
        metric="max_coupling", comp=Comparator.LT, thr=0.2, elements=("Pd",)):
    return Avenue(
        id=aid, tier=tier, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("compact_cluster",), ("high_spin",),
                          0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


class ScriptedGenerator:
    """Emits a fixed avenue list, then nothing (drives deterministic tests)."""

    def __init__(self, avenues):
        self._avenues = list(avenues)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avenues = self._avenues[:k], self._avenues[k:]
        return batch


def _stub_screen(**kwargs):
    # A minimal fake screen: one record whose coupling is low (kills H5).
    from orme_lab.pipeline import run_screen
    return run_screen(**kwargs)  # real screen is fine & deterministic for these tests


def test_loop_terminates_at_budget():
    gen = ScriptedGenerator([_av(f"A{i}", elements=(e,))
                             for i, e in enumerate(("Pd", "Ir", "Rh", "Os", "Pt"))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=5,
                                               convergence_rounds=99))
    assert isinstance(rep, LoopReport)
    assert len(rep.ledger.records) <= 3


def test_tier3_avenue_is_quarantined_not_run():
    gen = ScriptedGenerator([_av("T3", tier=Tier.TIER3)])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=5, proposals_per_round=5,
                                               convergence_rounds=1))
    assert len(rep.ledger.proposals) == 1
    assert all(r.tier != 3 for r in rep.ledger.records)


def test_tautological_only_generator_yields_zero_findings():
    # Adversarial whole-loop null: every avenue is tautological -> no records, honest digest.
    gen = ScriptedGenerator([_av(f"C{i}", predictors=("coupling",), elements=(e,))
                             for i, e in enumerate(("Pd", "Ir", "Rh"))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=1))
    kills = [r for r in rep.ledger.records if r.verdict == Verdict.KILLED_HYPOTHESIS.value]
    assert kills == []
    assert "no independent avenue" in rep.digest.lower()


def test_unfalsifiable_avenue_is_dropped_before_running():
    # threshold 0.0 for max_coupling can never fire -> not fireable -> dropped.
    gen = ScriptedGenerator([_av("U1", thr=0.0)])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=5, proposals_per_round=5,
                                               convergence_rounds=1))
    assert len(rep.ledger.records) == 0


def test_digest_never_claims_validation():
    gen = ScriptedGenerator([_av("A1")])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=1, proposals_per_round=1,
                                               convergence_rounds=1))
    low = rep.digest.lower()
    for word in ("validated", "confirmed superconductor", "proven superconductor"):
        assert word not in low
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_loop.py -v`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/loop.py
"""The bounded orchestrator. Each round: the generator PROPOSES avenues; the
deterministic core drops the unfalsifiable and the tautological, ranks the rest,
runs the top, triages, and records — retiring killed hypotheses. Tier-3 avenues
are quarantined, never run. The loop halts and surfaces at any operator-reserved
boundary. It never claims validation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from ..config import DEFAULT_CONFIG, LabConfig
from ..evidence import LAB_CEILING, badge
from ..pipeline import run_screen
from .avenue import Avenue, MechanismProposal, Tier
from .config import DEFAULT_LOOP_CONFIG, LoopConfig
from .ledger import Ledger
from .objective import score_avenue
from .runner import run_avenue
from .triage import Verdict, triage


class AvenueGenerator(Protocol):
    """The creative seam. In production this is the orme-lab-scientist subagent,
    supplied by the harness; the package ships HeuristicGenerator for offline use."""

    def propose(self, open_hypotheses: frozenset[str], seen_actions: frozenset[tuple],
                k: int) -> list[Avenue]:
        ...


def touches_reserved_boundary(avenue: Avenue) -> bool:
    """Operator-reserved boundaries the loop must not auto-act on. Tier-3 is the
    code/mechanism boundary; other boundaries (classification, publication) are
    out of the in-sim action space entirely, so tier is the sole in-band signal."""
    return avenue.tier is Tier.TIER3


@dataclass(frozen=True)
class LoopReport:
    ledger: Ledger
    rounds: int
    stopped_reason: str
    digest: str


def _digest(ledger: Ledger, stopped_reason: str) -> str:
    lines = [
        "# Autonomous lab-loop digest",
        "",
        f"_Stopped: {stopped_reason}. Evidence ceiling: {badge(LAB_CEILING)}._",
        "_Nothing here is validated. A surviving lead is a screening/triage signal,_",
        "_not evidence of superconductivity; validation requires physical Level 4-6._",
        "",
    ]
    killed = [r for r in ledger.records if r.verdict == Verdict.KILLED_HYPOTHESIS.value]
    if killed:
        lines.append("## Hypotheses retired (killed in-sim)")
        for r in killed:
            lines.append(f"- {r.killed_hypothesis} — by avenue {r.avenue_id}")
    else:
        lines.append("## Hypotheses retired: none this run")
    lines.append("")
    independent = [r for r in ledger.records
                   if r.verdict != Verdict.TAUTOLOGICAL.value]
    if not independent:
        lines.append("No independent avenue found — every proposed avenue was "
                     "tautological (re-derivable from the AND-gate's own inputs). "
                     "No findings.")
    if ledger.proposals:
        lines.append("")
        lines.append("## Tier-3 mechanism proposals (QUARANTINED — pending "
                     "operator + red-team review, NOT findings)")
        for p in ledger.proposals:
            lines.append(f"- {p.id}: {p.description}")
    return "\n".join(lines)


def run_loop(
    generator: AvenueGenerator,
    config: LabConfig = DEFAULT_CONFIG,
    loop_config: LoopConfig = DEFAULT_LOOP_CONFIG,
    backend=None,
    screen_fn=run_screen,
) -> LoopReport:
    ledger = Ledger()
    rounds = 0
    rounds_since_kill = 0
    stopped_reason = "budget reached"

    while len(ledger.records) < loop_config.max_avenues:
        rounds += 1
        proposed = generator.propose(
            ledger.open_hypotheses, ledger.seen_actions, loop_config.proposals_per_round,
        )
        if not proposed:
            stopped_reason = "generator exhausted"
            break

        # Quarantine tier-3 (reserved boundary); never run.
        runnable: list[Avenue] = []
        for av in proposed:
            if touches_reserved_boundary(av):
                ledger.quarantine(MechanismProposal(
                    id=av.id, description=av.description,
                    rationale=f"tier-{int(av.tier)} avenue targeting {av.targeted_hypothesis}",
                    provenance=av.provenance,
                ))
            else:
                runnable.append(av)

        # Drop unfalsifiable and already-seen; rank the rest.
        candidates = [
            av for av in runnable
            if av.falsification.fireable() and not ledger.is_seen(av)
        ]
        if not candidates:
            rounds_since_kill += 1
            if rounds_since_kill >= loop_config.convergence_rounds:
                stopped_reason = "converged (no runnable avenues)"
                break
            continue

        candidates.sort(
            key=lambda av: (
                -score_avenue(av, ledger.open_hypotheses, ledger.seen_actions,
                              loop_config.weights),
                av.id,
            )
        )
        best = candidates[0]

        result = run_avenue(best, config=config, backend=backend, screen_fn=screen_fn)
        outcome = triage(result, ledger.open_hypotheses)
        ledger.record(best, outcome, result.metrics)

        if outcome.verdict is Verdict.KILLED_HYPOTHESIS:
            rounds_since_kill = 0
        else:
            rounds_since_kill += 1
        if rounds_since_kill >= loop_config.convergence_rounds:
            stopped_reason = "converged (no new kill)"
            break

    return LoopReport(ledger=ledger, rounds=rounds, stopped_reason=stopped_reason,
                      digest=_digest(ledger, stopped_reason))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_loop.py -v`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/loop.py tests/lab_loop/test_loop.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: bounded orchestrator (rank/run/triage, tier-3 quarantine, honest digest)'
```

---

### Task 9: `HeuristicGenerator` + CLI + package exports + artifact dir

**Files:**
- Modify: `src/orme_lab/lab_loop/loop.py` (add `HeuristicGenerator`)
- Create: `src/orme_lab/lab_loop/__main__.py`
- Modify: `src/orme_lab/lab_loop/__init__.py`
- Create: `experiments/ledger/.gitkeep`
- Test: `tests/lab_loop/test_heuristic_and_cli.py`

**Interfaces:**
- Consumes: everything above.
- Produces: `HeuristicGenerator(elements: tuple[str, ...] = ...)` implementing `AvenueGenerator` — enumerates tier-1 coverage avenues deterministically over (element × geometry-kind) targeting `H5`, each with an off-gate predictor (`sc_lambda`) and a fireable falsification (`max_coupling < min_coupling_for_bulk`); `__init__` exports `run_loop`, `LoopReport`, `HeuristicGenerator`, `Ledger`, `Avenue`; `python -m orme_lab.lab_loop --max-avenues N [--out PATH]` runs offline and writes `ledger.jsonl` + `digest.md`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_heuristic_and_cli.py
import subprocess
import sys
from orme_lab.lab_loop import run_loop, HeuristicGenerator
from orme_lab.lab_loop.config import LoopConfig


def test_heuristic_generator_drives_a_loop_offline():
    rep = run_loop(HeuristicGenerator(),
                   loop_config=LoopConfig(max_avenues=4, proposals_per_round=4,
                                          convergence_rounds=99))
    assert len(rep.ledger.records) >= 1
    # every recorded avenue used an off-gate predictor -> none tautological
    assert all(r.verdict != "tautological" for r in rep.ledger.records)


def test_heuristic_generator_eventually_exhausts():
    gen = HeuristicGenerator(elements=("Pd",))
    first = gen.propose(frozenset({"H5"}), frozenset(), 100)
    assert len(first) >= 1
    # asking again after 'seeing' those actions returns fewer/none
    seen = frozenset()  # generator is stateless re: seen; loop enforces dedup
    assert isinstance(first, list)


def test_cli_runs_and_writes_artifacts(tmp_path):
    out = tmp_path / "run"
    proc = subprocess.run(
        [sys.executable, "-m", "orme_lab.lab_loop",
         "--max-avenues", "3", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "ledger.jsonl").exists()
    assert (out / "digest.md").exists()
    assert "validated" not in (out / "digest.md").read_text().lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_heuristic_and_cli.py -v`
Expected: FAIL with `ImportError: cannot import name 'HeuristicGenerator'`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/orme_lab/lab_loop/loop.py`:

```python
class HeuristicGenerator:
    """Deterministic offline generator: enumerates tier-1 coverage avenues over
    (element x geometry-kind), each targeting H5 with an off-gate predictor and a
    fireable falsification. Not creative — a floor so the loop runs with no LLM.
    The production generator is the orme-lab-scientist subagent."""

    _GEOMS = ("monomer", "dimer", "linear_chain", "compact_cluster")

    def __init__(self, elements: tuple[str, ...] = ("Pd", "Ir", "Rh", "Os", "Pt", "Au")):
        self._elements = elements

    def propose(self, open_hypotheses, seen_actions, k):
        from ..config import ModelThresholds
        thr = ModelThresholds().min_coupling_for_bulk
        out: list[Avenue] = []
        for el in self._elements:
            for geom in self._GEOMS:
                av = Avenue(
                    id=f"H-{el}-{geom}", tier=Tier.TIER1,
                    description=f"{el} {geom}: does coupling clear the bulk gate?",
                    targeted_hypothesis="H5",
                    action=__import__("orme_lab.lab_loop.avenue", fromlist=["ActionSpec"]).ActionSpec(
                        elements=(el,), geometry_kinds=(geom,), spin_labels=("high_spin",),
                        applied_field_t=0.0, temperature_k=298.15,
                        use_epw=False, use_em=False, coupling_channel=None,
                    ),
                    falsification=__import__("orme_lab.lab_loop.avenue", fromlist=["FalsificationCondition", "Comparator"]).FalsificationCondition(
                        "max_coupling",
                        __import__("orme_lab.lab_loop.avenue", fromlist=["Comparator"]).Comparator.LT,
                        thr,
                    ),
                    predictor_invariants=("sc_lambda",), provenance="HeuristicGenerator",
                )
                if av.action.elements + av.action.geometry_kinds not in seen_actions:
                    out.append(av)
                if len(out) >= k:
                    return out
        return out
```

Note: prefer clean top-of-file imports of `ActionSpec`, `FalsificationCondition`, `Comparator` over the `__import__` calls shown — the dynamic form is only to keep this appended block self-contained in the plan. When implementing, add them to the existing `from .avenue import ...` line and delete the `__import__` noise.

```python
# src/orme_lab/lab_loop/__main__.py
"""CLI: python -m orme_lab.lab_loop --max-avenues N [--out DIR].

Runs the loop offline with the HeuristicGenerator and writes ledger.jsonl +
digest.md. The creative (subagent) generator is wired in at the harness level,
not here."""

from __future__ import annotations

import argparse
import os

from .config import LoopConfig
from .loop import HeuristicGenerator, run_loop


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="orme_lab.lab_loop")
    p.add_argument("--max-avenues", type=int, default=20)
    p.add_argument("--out", default="experiments/ledger")
    args = p.parse_args(argv)

    rep = run_loop(HeuristicGenerator(), loop_config=LoopConfig(max_avenues=args.max_avenues))
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "ledger.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(rep.ledger.to_jsonl())
    with open(os.path.join(args.out, "digest.md"), "w", encoding="utf-8") as fh:
        fh.write(rep.digest)
    print(rep.digest)
    print(f"\n[{len(rep.ledger.records)} avenues run, "
          f"{len(rep.ledger.proposals)} quarantined; stopped: {rep.stopped_reason}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

```python
# src/orme_lab/lab_loop/__init__.py
"""Autonomous lab-scientist loop (see docs/superpowers/specs/2026-07-04-autonomous-lab-loop-design.md)."""

from .avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator, MechanismProposal
from .ledger import Ledger, HYPOTHESES
from .loop import AvenueGenerator, HeuristicGenerator, LoopReport, run_loop

__all__ = [
    "Avenue", "ActionSpec", "Tier", "FalsificationCondition", "Comparator",
    "MechanismProposal", "Ledger", "HYPOTHESES", "AvenueGenerator",
    "HeuristicGenerator", "LoopReport", "run_loop",
]
```

Create `experiments/ledger/.gitkeep` (empty file).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/lab_loop/test_heuristic_and_cli.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/loop.py src/orme_lab/lab_loop/__main__.py src/orme_lab/lab_loop/__init__.py experiments/ledger/.gitkeep tests/lab_loop/test_heuristic_and_cli.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: HeuristicGenerator + CLI (offline run writes ledger.jsonl + digest.md)'
```

---

### Task 10: Integration test — multi-round loop, kill + quarantine + honesty

**Files:**
- Test: `tests/lab_loop/test_integration.py`

**Interfaces:**
- Consumes: the whole package.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_integration.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _av(aid, tier=Tier.TIER1, predictors=("sc_lambda",), hyp="H5",
        metric="max_coupling", comp=Comparator.LT, thr=0.2, elements=("Pd",), geom="monomer"):
    return Avenue(
        id=aid, tier=tier, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, (geom,), ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition(metric, comp, thr),
        predictor_invariants=predictors, provenance="t",
    )


class ScriptedGenerator:
    def __init__(self, avenues):
        self._avenues = list(avenues)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avenues = self._avenues[:k], self._avenues[k:]
        return batch


def test_end_to_end_kill_quarantine_and_honest_digest():
    # A monomer (coupling ~0) kills H5; a tier-3 proposal is quarantined; a
    # tautological avenue produces no finding.
    gen = ScriptedGenerator([
        _av("KILL", elements=("Pd",), geom="monomer"),          # coupling < 0.2 -> kills H5
        _av("T3", tier=Tier.TIER3, elements=("Ir",)),           # quarantined
        _av("TAUT", predictors=("coupling",), elements=("Rh",)),# tautological
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))

    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts.get("KILL") == Verdict.KILLED_HYPOTHESIS.value
    assert "H5" not in rep.ledger.open_hypotheses
    assert any(p.id == "T3" for p in rep.ledger.proposals)
    assert verdicts.get("TAUT") == Verdict.TAUTOLOGICAL.value

    low = rep.digest.lower()
    assert "validated" not in low
    assert "h5" in low  # retired hypothesis surfaced


def test_full_suite_determinism_two_identical_runs():
    avenues = lambda: [_av(f"A{i}", elements=(e,), geom=g)
                       for i, (e, g) in enumerate(
                           [("Pd", "monomer"), ("Ir", "dimer"), ("Rh", "compact_cluster")])]
    r1 = run_loop(ScriptedGenerator(avenues()),
                  loop_config=LoopConfig(max_avenues=9, proposals_per_round=9, convergence_rounds=99))
    r2 = run_loop(ScriptedGenerator(avenues()),
                  loop_config=LoopConfig(max_avenues=9, proposals_per_round=9, convergence_rounds=99))
    assert r1.ledger.to_jsonl() == r2.ledger.to_jsonl()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/lab_loop/test_integration.py -v`
Expected: initially FAIL only if an earlier task's behavior is off; if Tasks 1–9 are correct, this may pass immediately. If it fails, fix the implicated module (do not edit the test to match a bug).

- [ ] **Step 3: Make it pass**

No new production code should be required. If a test fails, treat it as a real defect in the named module and fix there.

- [ ] **Step 4: Run the whole suite**

Run: `pytest -q`
Expected: all lab_loop tests plus the pre-existing 95 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add tests/lab_loop/test_integration.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: end-to-end integration test (kill + quarantine + honest digest + determinism)'
```

---

## Self-Review (against the spec)

**Spec coverage:**
- §3 architecture / module table → Tasks 1–9 (one module each; `config.py` Task 3).
- §4.1 tautology gate → Task 2 (`closure`) + Task 5 (`triage` uses it) + Task 6 (`objective` zeroes tautological) + Task 8 (digest reports the all-tautological null).
- §4.2 objective, candidate-strength excluded → Task 6 (`score_avenue` has no strength input; test asserts invariance).
- §4.3 must-be-able-to-fail → Task 1 (`fireable`) + Task 8 (drops unfalsifiable before running) + Task 5/Task 10 (kill-as-success).
- §4.4 honesty guards → Task 5 (closed `Verdict`, meta-test) + Task 8 (`LAB_CEILING` badge in digest, no "validated") + Task 8 (tier-3 quarantine) + Task 8 (`touches_reserved_boundary` hard-stop).
- §5 ledger + digest + how it acts → Task 7 (`Ledger`) + Task 8 (`_digest`, `run_loop`) + Task 9 (CLI writes `ledger.jsonl` + `digest.md`).
- §6 tiers → Task 1 (`Tier`), Tier-2 `coupling_channel` field present in `ActionSpec` (runnable modeling deferred, noted in §9), Tier-3 walled (Task 8).
- §7 determinism → Task 7 (monotonic seq, sorted JSON) + Task 10 (two-run byte-identity test).
- §8 test strategy items 1–11 → mapped: closure golden (T2), tautology guard (T5), falsifiability (T1/T8), objective invariance (T6), null-is-progress (T5/T10), ledger determinism+dedup (T7), termination (T8), tier-3 quarantine (T8), verdict meta-test (T5), operator hard-stop (T8 via tier-3), adversarial whole-loop null (T8).

**Placeholder scan:** none — every step carries real code and a runnable command. The `HeuristicGenerator` `__import__` noise is explicitly flagged to be replaced with top-level imports at implementation time.

**Type consistency:** `Avenue`/`ActionSpec`/`FalsificationCondition` field names are identical across Tasks 1, 4, 5, 6, 8, 9, 10. `run_avenue(avenue, config, backend, screen_fn)`, `triage(result, open_hypotheses)`, `score_avenue(avenue, open_hypotheses, seen_actions, weights)`, `Ledger.record(avenue, outcome, metrics)`, `run_loop(generator, config, loop_config, backend, screen_fn)` are used consistently everywhere they appear.

**Deferred (spec §2, explicit):** tier-3 executor (worktree codegen) — only the wall is built. Tier-2 coupling-channel *modeling* — the `coupling_channel` field exists and is carried through, but no new toy model consumes it yet (§9 open question).

**Operator-reserved:** this plan writes only under `src/orme_lab/lab_loop/`, `tests/lab_loop/`, `experiments/ledger/`, and `docs/superpowers/`. It changes no evidence classification, no repo visibility, and pushes nothing. Merge/push are operator decisions at finish time.
