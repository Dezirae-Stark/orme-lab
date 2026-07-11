# Hudson Optical-Coherence Branch (Branch B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Branch B — the Hudson optical-coherence mechanism — as a first-class, *independently tracked* branch beside the existing conventional-superconductivity gate (Branch A), so the lab can test Hudson's actual proposed transmission mechanism (a resonantly accessible, macroscopically coherent hybrid light–matter phase) on its own terms without conflating it with ordinary DC superconductivity.

**Architecture:** Branch B builds on the already-shipped `electromagnetic_coherence.py` mode algebra (Rabi splitting, cooperativity, Q, lifetime, strong/ultrastrong regimes). It adds the decisive layer that module lacks: coupled-oscillator **mode composition** (photonic/electronic Hopfield fractions `f_ph`/`f_el`) and the **anticrossing** dispersion; the **Hudson optical order parameter** `O_H = {ω₀, Q, g, τ_coh, L_coh, f_ph, f_el}`; a **broadband resonance survey** (RF→µW→THz→IR→vis→near-UV, because Hudson tuned with RF while calling the state "light"); the load-bearing **ring-down persistence gate** that separates ordinary driven-dissipative polariton physics from a self-sustaining mode; and the **causal magnetism↔coherence link** `C(ω)=∂M/∂P_drive`. Persistence and the causal link are **default-blocked**: the simulation cannot assert them — they require an external lab measurement fed in — exactly as `identity.py` default-blocks crediting. Branch B's fields are registered as `OFF_GATE_INVARIANTS` (independent of the SC AND-gate, same argument as the existing `em_coherence_*` fields), and a two-branch verdict object reports Branch A and Branch B as independent verdicts, with the full "Hudson-type optical superconductive phase" only ever a top-level *prediction* — never a merged score.

**Tech Stack:** Python 3 (stdlib only — `math`, `dataclasses`, `enum`), pytest. No new dependencies. Extends `orme_lab.electromagnetic_coherence`, `orme_lab.config`, `orme_lab.pipeline`, `orme_lab.lab_loop.closure`, `orme_lab.validator`.

## Global Constraints

Every task's requirements implicitly include this section.

- **Determinism (critical path).** No `time.time()`, no unseeded RNG, no order-dependent dict/set iteration in any computed result. All survey bands and result tuples are emitted in a fixed, documented order. Seeded `random.Random(seed)` is the only permitted randomness (none is needed here).
- **Evidence ceilings.** Screens/verdicts clamp to `LAB_CEILING` (Level 2, `SIMULATION_CANDIDATE`). Designs/predictions clamp to `PREDICTION_CEILING` (Level 3, `LABORATORY_PREDICTION`). Nothing Branch B computes may assert Level 4+; a Level-4 (`INITIAL_OBSERVATION`) value may appear ONLY as an `evidence_level_if_confirmed` on a decisive experiment, never as a produced `evidence_level`.
- **No fabricated physics or citations.** Every Branch-B quantity is an explicitly-flagged **surrogate/toy**, bounded, with a source comment for any real physical form used. Permitted forms are textbook and named generically: coupled two-oscillator diagonalization, Hopfield mode-composition weights, cavity-QED cooperativity. Do **not** invent a citation (author/year/venue) for any of them. Do not characterize any paper's contents.
- **Branch independence (load-bearing).** Branch B never sets, reads, or rescues Branch A's `credited_sc_lead`, and vice versa. All Branch-B `CandidateRecord` fields go in `closure.OFF_GATE_INVARIANTS`, never `GATE_INPUT_CLOSURE`. The full "Hudson optical superconductive phase" (claim level 8) is the conjunction of both branches at the TOP only, and is emitted as a *prediction*, never as a crediting verdict and never as a blended numeric score.
- **Default-block extraordinary claims.** `classify_persistence` returns `DRIVEN_DISSIPATIVE` (the conservative null) unless an external measured ring-down time is supplied; `magnetism_tracks_resonance` returns `False`/unestablished unless an external measured `∂M/∂P` at resonance is supplied. Persistence and causal magnetism are laboratory inputs, not simulation outputs.
- **Falsification surface, not credence.** Branch B's job is to make the coherent-mode claim survive the mundane alternatives (fluorescence, Raman, thermal emission, Mie scattering, metallic-nanoparticle plasmon, cavity leakage, microwave heating, dielectric resonance, stray TX↔RX coupling). A high coherence score is never, by itself, evidence for Hudson.
- **Commits.** Author and commit as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`. NEVER emit AI-identity trailers (`Co-Authored-By:`, `Signed-off-by:`, `Claude-Session:` naming Claude/Anthropic) in the commit author, committer, message body, OR any PR body.
- **No network egress / no telemetry.** Loopback only; Branch B performs no I/O.
- **Out of scope (deliberately deferred to the next plan).** The full `G_Hudson = G_identity ∧ G_transport ∧ G_magnetism ∧ G_replication` ledger (HC-01..HC-08); claim-hierarchy levels 9 (independent reproduction) and 10 (practical transduction), which require real labs; and any web/3D visualization of Branch B. This plan delivers Branch B and the two-branch verdict scaffold the ledger will later consume.

---

## File Structure

- `src/orme_lab/hudson_optical.py` **(create)** — Branch B core: mode composition + anticrossing, `OpticalOrderParameter` (`O_H`), broadband survey, ring-down persistence gate, causal magnetism link, `HudsonOpticalResult` + `evaluate_hudson_optical`. One responsibility: the optical-coherence branch physics and its evidence ladder.
- `src/orme_lab/branch_verdict.py` **(create)** — the two-branch independent verdict object (`BranchVerdict`) that combines a Branch-A `CandidateRecord` and a Branch-B `HudsonOpticalResult` without letting either cross into the other.
- `src/orme_lab/config.py` **(modify)** — add Branch-B thresholds to `ModelThresholds` and the `SPEED_OF_LIGHT` constant.
- `src/orme_lab/pipeline.py` **(modify)** — `CandidateRecord` gains Branch-B fields; `evaluate_candidate` computes and attaches a `HudsonOpticalResult`; `as_csv_row` renders the new fields.
- `src/orme_lab/lab_loop/closure.py` **(modify)** — `OFF_GATE_INVARIANTS` gains the Branch-B field names (independent of the SC gate).
- `src/orme_lab/validator.py` **(modify)** — promote the excitonic/optical route from a *mundane alternative* to a first-class **Branch-B decisive-experiment set** (broadband survey, anticrossing, g⁽¹⁾/g⁽²⁾ coherence, resonant injection, energy-transfer geometry, `∂M/∂P`, ring-down as the decisive test).
- `tests/test_hudson_optical.py` **(create)**, `tests/test_branch_verdict.py` **(create)** — Branch-B unit tests.
- `tests/test_closure.py` **(modify)** — update the pinned golden sets.
- `tests/test_validator.py` **(modify)** — assert the Branch-B decisive experiments.

---

### Task 1: Mode composition, anticrossing, and Branch-B config

**Files:**
- Modify: `src/orme_lab/config.py` (add constant + threshold fields)
- Create: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: `orme_lab.electromagnetic_coherence.ElectromagneticMode` (fields `mode_energy_ev`, `coupling_energy_ev`, `cavity_loss_ev`, `matter_loss_ev`; properties `rabi_splitting_ev`, `quality_factor`, `coherence_lifetime_fs`); `orme_lab.config.ModelThresholds`.
- Produces: `polariton_branches(matter_ev, photon_ev, coupling_ev) -> tuple[float, float]` (lower, upper); `mode_composition(matter_ev, photon_ev, coupling_ev) -> tuple[float, float]` (`f_ph`, `f_el`) of the LOWER polariton; `is_anticrossing(coupling_ev, linewidth_ev) -> bool`; `SPEED_OF_LIGHT` constant; `ModelThresholds` fields `hudson_min_photon_fraction`, `hudson_metastable_ratio`, `hudson_persistent_ratio`, `hudson_group_velocity_fraction`.

- [ ] **Step 1: Add the constant and thresholds to `config.py`**

In `config.py`, add near the other physical constants (after `EV_IN_JOULES`):

```python
SPEED_OF_LIGHT = 2.99792458e8            # m/s (exact, SI definition)
```

In the `ModelThresholds` dataclass, add after `min_cooperativity_for_coherence`:

```python
    # --- Branch B (Hudson optical-coherence) -----------------------------------
    #: Minimum photonic (Hopfield) fraction of the lower polariton for the mode to
    #: count as a genuine light-matter HYBRID rather than a bare matter excitation.
    hudson_min_photon_fraction: float = 0.20
    #: measured/predicted ring-down ratio at/above which a decayed mode is
    #: "metastable" (long-lived but not self-sustaining).
    hudson_metastable_ratio: float = 10.0
    #: measured/predicted ring-down ratio at/above which the mode is treated as
    #: effectively self-sustaining ("persistent") — Hudson's extraordinary claim.
    hudson_persistent_ratio: float = 1.0e6
    #: group velocity as a fraction of c, for the toy spatial-coherence-length
    #: surrogate L_coh = frac * c * tau_coh. Flagged toy; TODO(dft): compute v_g.
    hudson_group_velocity_fraction: float = 0.01
```

- [ ] **Step 2: Write the failing test for composition and anticrossing**

Create `tests/test_hudson_optical.py`:

```python
"""Tests for the Hudson optical-coherence branch (Branch B)."""
from __future__ import annotations

import math

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.hudson_optical import (
    is_anticrossing,
    mode_composition,
    polariton_branches,
)

TH = DEFAULT_CONFIG.thresholds


def test_polariton_branches_split_by_rabi_at_resonance():
    # On resonance (matter == photon), the branches are separated by 2g (the Rabi
    # splitting), symmetric about the shared bare energy.
    lower, upper = polariton_branches(2.0, 2.0, 0.3)
    assert math.isclose(upper - lower, 0.6, rel_tol=1e-9)   # 2g
    assert math.isclose((upper + lower) / 2, 2.0, rel_tol=1e-9)


def test_mode_composition_is_5050_on_resonance():
    f_ph, f_el = mode_composition(2.0, 2.0, 0.3)
    assert math.isclose(f_ph, 0.5, rel_tol=1e-9)
    assert math.isclose(f_el, 0.5, rel_tol=1e-9)
    assert math.isclose(f_ph + f_el, 1.0, rel_tol=1e-12)


def test_lower_polariton_is_photon_like_when_photon_below_matter():
    # matter well ABOVE photon -> the lower polariton tracks the photon -> photon-like.
    f_ph, f_el = mode_composition(3.0, 1.0, 0.05)
    assert f_ph > 0.9
    assert f_el < 0.1


def test_anticrossing_requires_splitting_above_linewidth():
    assert is_anticrossing(0.30, linewidth_ev=0.10) is True    # 2g=0.6 > 0.10
    assert is_anticrossing(0.02, linewidth_ev=0.10) is False   # 2g=0.04 < 0.10
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.hudson_optical'`.

- [ ] **Step 4: Write the minimal implementation**

Create `src/orme_lab/hudson_optical.py` with the module docstring and these functions:

```python
"""Hudson optical-coherence branch (Branch B).

Hudson described the proposed ORME phase not as an ordinary zero-resistance metal
but as a resonantly accessible, macroscopically coherent hybrid light-matter state:
a single frequency of light circulating internally, carriers entering as paired
electrons through resonant frequency matching, and a circulating mode producing the
Meissner response. Read literally ("two electrons become pure light") this is
incompatible with condensed-matter physics — Cooper pairs are charge-2e composite
bosons, not photons. The defensible, testable translation (see
``docs/terminology_translation.md`` and ``electromagnetic_coherence.py``) is a
hybrid eigenstate

    |P> = alpha|2e> + beta|photon> + chi|X>

with a MEASURABLE photonic fraction f_ph and electronic fraction f_el.

This branch is DISTINCT from superconductivity (Branch A). A material can be a
room-temperature polariton condensate without being an electrical superconductor,
and vice versa. Branch B therefore adds FALSIFICATION SURFACE, not credence: a high
coherence score is never, by itself, evidence for Hudson — it must survive the
mundane alternatives (fluorescence, Raman, thermal emission, Mie scattering,
nanoparticle plasmons, cavity leakage). The two load-bearing, EXTRAORDINARY claims —
that the mode is self-sustaining (persistent ring-down) and that magnetism tracks the
optical resonance — are default-blocked: the simulation cannot assert them; they
require an external laboratory measurement fed in.

All physics here is toy/surrogate, bounded, and flagged. Real forms used are
textbook: coupled two-oscillator diagonalization and Hopfield mode-composition
weights. TODO(dft): replace bare couplings with computed mode overlaps.
"""
from __future__ import annotations

import math

from .config import ModelThresholds


def polariton_branches(matter_ev: float, photon_ev: float, coupling_ev: float) -> tuple[float, float]:
    """Lower/upper polariton energies from a coupled two-oscillator diagonalization.

    H = [[matter_ev, g], [g, photon_ev]]; eigenvalues
        E_pm = (matter+photon)/2 +/- sqrt((delta/2)^2 + g^2),  delta = matter - photon.
    On resonance the splitting is 2g (the vacuum Rabi splitting). Returns
    (lower, upper).
    """
    mean = 0.5 * (matter_ev + photon_ev)
    half = math.sqrt((0.5 * (matter_ev - photon_ev)) ** 2 + coupling_ev**2)
    return mean - half, mean + half


def mode_composition(matter_ev: float, photon_ev: float, coupling_ev: float) -> tuple[float, float]:
    """Photonic (Hopfield) and electronic fractions of the LOWER polariton.

    f_ph = (1/2)(1 + delta / Omega),  f_el = 1 - f_ph,
    with delta = matter - photon and Omega = sqrt(delta^2 + 4 g^2). On resonance
    (delta=0) both are 1/2; when matter >> photon the lower branch is photon-like
    (f_ph -> 1). Deterministic; bounded to [0, 1].
    """
    delta = matter_ev - photon_ev
    omega = math.sqrt(delta**2 + 4.0 * coupling_ev**2)
    if omega <= 0:
        return 0.5, 0.5
    f_ph = 0.5 * (1.0 + delta / omega)
    f_ph = min(1.0, max(0.0, f_ph))
    return f_ph, 1.0 - f_ph


def is_anticrossing(coupling_ev: float, linewidth_ev: float) -> bool:
    """A resolvable avoided crossing: the Rabi splitting 2g exceeds the linewidth.

    Two UNRELATED peaks that cross as the environment is tuned is the null; a genuine
    hybrid mode shows a minimum gap of 2g > linewidth at resonance.
    """
    return 2.0 * coupling_ev > linewidth_ev
```

- [ ] **Step 5: Run the test to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (4 tests).

- [ ] **Step 6: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/config.py src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): polariton mode composition + anticrossing (Branch B foundation)"
```

---

### Task 2: The Hudson optical order parameter `O_H`

**Files:**
- Modify: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: `ElectromagneticMode`, `mode_composition`, `config.SPEED_OF_LIGHT`, `ModelThresholds.hudson_group_velocity_fraction`.
- Produces: `@dataclass(frozen=True) OpticalOrderParameter` with fields `omega0_ev, quality_factor, coupling_ev, tau_coh_fs, l_coh_nm, f_photon, f_electron`; classmethod-style builder `order_parameter_from_mode(mode, matter_ev, thresholds) -> OpticalOrderParameter`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_optical.py`:

```python
from orme_lab.electromagnetic_coherence import ElectromagneticMode
from orme_lab.hudson_optical import OpticalOrderParameter, order_parameter_from_mode


def _resonant_mode(mode_ev=2.0, g=0.3, kappa=0.05, gamma=0.05):
    return ElectromagneticMode(mode_energy_ev=mode_ev, coupling_energy_ev=g,
                               cavity_loss_ev=kappa, matter_loss_ev=gamma)


def test_order_parameter_bundles_the_seven_quantities():
    m = _resonant_mode()
    oh = order_parameter_from_mode(m, matter_ev=2.0, thresholds=TH)
    assert isinstance(oh, OpticalOrderParameter)
    assert oh.omega0_ev == 2.0
    assert oh.coupling_ev == 0.3
    assert oh.quality_factor == m.quality_factor
    assert oh.tau_coh_fs == m.coherence_lifetime_fs
    # on resonance the composition is 50/50
    assert math.isclose(oh.f_photon, 0.5, rel_tol=1e-9)
    assert math.isclose(oh.f_electron, 0.5, rel_tol=1e-9)
    # spatial coherence length is a positive surrogate = frac * c * tau
    assert oh.l_coh_nm > 0.0


def test_order_parameter_is_frozen():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    try:
        oh.omega0_ev = 1.0  # type: ignore[misc]
        assert False, "OpticalOrderParameter must be immutable"
    except Exception:
        pass
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ImportError: cannot import name 'OpticalOrderParameter'`.

- [ ] **Step 3: Implement**

Add to `src/orme_lab/hudson_optical.py` (add `from dataclasses import dataclass` and `from .config import ModelThresholds, SPEED_OF_LIGHT` to imports):

```python
@dataclass(frozen=True)
class OpticalOrderParameter:
    """O_H = {omega0, Q, g, tau_coh, L_coh, f_ph, f_el} — the Hudson optical order
    parameter. All quantities are toy/surrogate and bounded; f_photon + f_electron
    == 1 by construction."""

    omega0_ev: float        # bare resonance energy
    quality_factor: float   # Q = omega / kappa
    coupling_ev: float      # light-matter coupling g
    tau_coh_fs: float       # temporal coherence lifetime
    l_coh_nm: float         # spatial coherence length (surrogate)
    f_photon: float         # photonic (Hopfield) fraction of the lower polariton
    f_electron: float       # electronic fraction (= 1 - f_photon)


def order_parameter_from_mode(mode, matter_ev: float,
                              thresholds: ModelThresholds) -> OpticalOrderParameter:
    """Assemble O_H for one coupled mode.

    The spatial coherence length is a flagged surrogate L_coh = frac * c * tau_coh
    (a propagating coherent mode travels ~v_g * tau before dephasing; v_g is
    unknown here, so ``hudson_group_velocity_fraction`` stands in for v_g/c).
    """
    f_ph, f_el = mode_composition(matter_ev, mode.mode_energy_ev, mode.coupling_energy_ev)
    tau_s = mode.coherence_lifetime_fs * 1e-15 if math.isfinite(mode.coherence_lifetime_fs) else math.inf
    if math.isinf(tau_s):
        l_coh_nm = math.inf
    else:
        l_coh_m = thresholds.hudson_group_velocity_fraction * SPEED_OF_LIGHT * tau_s
        l_coh_nm = l_coh_m * 1e9
    return OpticalOrderParameter(
        omega0_ev=mode.mode_energy_ev,
        quality_factor=mode.quality_factor,
        coupling_ev=mode.coupling_energy_ev,
        tau_coh_fs=mode.coherence_lifetime_fs,
        l_coh_nm=l_coh_nm,
        f_photon=f_ph,
        f_electron=f_el,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): O_H optical order parameter"
```

---

### Task 3: Ring-down persistence gate (default-blocked)

**Files:**
- Modify: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: `OpticalOrderParameter`, `ModelThresholds` (`hudson_metastable_ratio`, `hudson_persistent_ratio`), `orme_lab.evidence.EvidenceLevel`.
- Produces: `class Persistence(str, Enum)` = `{DRIVEN_DISSIPATIVE, METASTABLE, PERSISTENT}`; `@dataclass(frozen=True) PersistenceResult(persistence, ratio, predicted_fs, measured_fs, evidence_level_if_confirmed, note)`; `classify_persistence(o_h, *, measured_ringdown_fs=None, thresholds) -> PersistenceResult`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_optical.py`:

```python
from orme_lab.evidence import EvidenceLevel
from orme_lab.hudson_optical import Persistence, classify_persistence


def test_persistence_defaults_to_driven_dissipative_without_measurement():
    # The simulation CANNOT assert persistence. With no measured ring-down, the
    # conservative null is driven-dissipative.
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=None, thresholds=TH)
    assert r.persistence is Persistence.DRIVEN_DISSIPATIVE
    assert r.measured_fs is None
    assert "requires an external" in r.note


def test_measured_ringdown_below_metastable_is_driven_dissipative():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 2, thresholds=TH)
    assert r.persistence is Persistence.DRIVEN_DISSIPATIVE     # ratio 2 < 10


def test_measured_ringdown_metastable_band():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 100, thresholds=TH)
    assert r.persistence is Persistence.METASTABLE            # 10 <= 100 < 1e6


def test_measured_ringdown_persistent_reaches_observation_if_confirmed():
    oh = order_parameter_from_mode(_resonant_mode(), matter_ev=2.0, thresholds=TH)
    r = classify_persistence(oh, measured_ringdown_fs=oh.tau_coh_fs * 1e7, thresholds=TH)
    assert r.persistence is Persistence.PERSISTENT
    # a MEASURED persistent ring-down is an observation, not a simulation output
    assert r.evidence_level_if_confirmed == int(EvidenceLevel.INITIAL_OBSERVATION)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ImportError: cannot import name 'Persistence'`.

- [ ] **Step 3: Implement**

Add to `src/orme_lab/hudson_optical.py` (add `from enum import Enum` and `from .evidence import EvidenceLevel` to imports):

```python
class Persistence(str, Enum):
    """Post-drive ring-down class of the coherent mode."""
    DRIVEN_DISSIPATIVE = "driven_dissipative"   # decays on the mode timescale; needs pumping
    METASTABLE = "metastable"                   # long-lived but not self-sustaining
    PERSISTENT = "persistent"                   # effectively self-sustaining (Hudson's claim)


@dataclass(frozen=True)
class PersistenceResult:
    persistence: Persistence
    ratio: float | None            # measured / model-predicted decay time (None if unmeasured)
    predicted_fs: float            # driven-dissipative expectation (~ mode lifetime)
    measured_fs: float | None      # externally supplied ring-down time
    evidence_level_if_confirmed: int
    note: str


def classify_persistence(o_h: OpticalOrderParameter, *,
                         measured_ringdown_fs: float | None,
                         thresholds: ModelThresholds) -> PersistenceResult:
    """Classify the mode's post-drive ring-down.

    Persistence is Hudson's EXTRAORDINARY claim, so it is default-blocked: the model's
    predicted decay time is the mode lifetime (driven-dissipative expectation), and
    without an external measured ring-down the result is DRIVEN_DISSIPATIVE. A supplied
    measurement is compared to the prediction; a genuinely self-sustaining mode
    (ratio >= persistent_ratio) is the only path to a Level-4 observation.
    """
    predicted = o_h.tau_coh_fs
    if measured_ringdown_fs is None:
        return PersistenceResult(
            Persistence.DRIVEN_DISSIPATIVE, None, predicted, None,
            int(EvidenceLevel.LABORATORY_PREDICTION),
            "no measured ring-down; conservative driven-dissipative null. Persistence "
            "requires an external post-drive ring-down measurement (a lab input).")
    if not math.isfinite(predicted) or predicted <= 0:
        # a lossless model prediction is degenerate; refuse to credit persistence from it
        return PersistenceResult(
            Persistence.DRIVEN_DISSIPATIVE, None, predicted, measured_ringdown_fs,
            int(EvidenceLevel.LABORATORY_PREDICTION),
            "model predicts no finite decay (degenerate); cannot ratio a measurement against it.")
    ratio = measured_ringdown_fs / predicted
    if ratio >= thresholds.hudson_persistent_ratio:
        cls, note = Persistence.PERSISTENT, "measured ring-down >> mode lifetime: effectively self-sustaining."
    elif ratio >= thresholds.hudson_metastable_ratio:
        cls, note = Persistence.METASTABLE, "measured ring-down long but finite: metastable, not self-sustaining."
    else:
        cls, note = Persistence.DRIVEN_DISSIPATIVE, "measured ring-down ~ mode lifetime: driven-dissipative."
    ev = int(EvidenceLevel.INITIAL_OBSERVATION) if cls is Persistence.PERSISTENT \
        else int(EvidenceLevel.LABORATORY_PREDICTION)
    return PersistenceResult(cls, ratio, predicted, measured_ringdown_fs, ev, note)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (10 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): default-blocked ring-down persistence gate"
```

---

### Task 4: Broadband resonance survey

**Files:**
- Modify: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: `ElectromagneticMode`, `orme_lab.electromagnetic_coherence.coupling_regime`, `ModelThresholds`.
- Produces: module constant `SURVEY_BANDS: tuple[tuple[str, float], ...]` (name, center energy eV), fixed order RF→near-UV; `@dataclass(frozen=True) BandResult(band, center_ev, regime, cooperativity)`; `resonance_survey(coupling_fraction, cavity_loss_ev, matter_loss_ev, thresholds) -> tuple[BandResult, ...]`; `strongest_band(results) -> BandResult | None`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_optical.py`:

```python
from orme_lab.hudson_optical import (
    SURVEY_BANDS,
    resonance_survey,
    strongest_band,
)


def test_survey_covers_rf_through_near_uv_in_fixed_order():
    names = [b[0] for b in SURVEY_BANDS]
    assert names == ["RF", "microwave", "THz", "IR", "visible", "near-UV"]
    # "light" is not restricted to visible: RF is the lowest band (Hudson tuned with RF)
    assert SURVEY_BANDS[0][1] < SURVEY_BANDS[-1][1]


def test_survey_is_deterministic_and_ordered():
    a = resonance_survey(0.05, 0.10, 0.05, TH)
    b = resonance_survey(0.05, 0.10, 0.05, TH)
    assert a == b
    assert [r.band for r in a] == [b[0] for b in SURVEY_BANDS]


def test_strongest_band_picks_max_cooperativity_among_non_weak():
    results = resonance_survey(0.05, 0.10, 0.05, TH)
    best = strongest_band(results)
    if best is not None:
        assert best.regime != "weak"
        assert all(best.cooperativity >= r.cooperativity for r in results if r.regime != "weak")


def test_strongest_band_is_none_when_all_weak():
    # crush coupling so no band reaches strong coupling
    results = resonance_survey(1e-6, 1.0, 1.0, TH)
    assert all(r.regime == "weak" for r in results)
    assert strongest_band(results) is None
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ImportError: cannot import name 'SURVEY_BANDS'`.

- [ ] **Step 3: Implement**

Add to `src/orme_lab/hudson_optical.py` (add `from .electromagnetic_coherence import ElectromagneticMode, coupling_regime` to imports):

```python
#: Representative center energies (eV) for each band of the broadband survey.
#: Hudson described RF tuning while calling the internal state "light"; photons
#: span the whole spectrum, so the survey must not start at visible. Values are
#: order-of-magnitude band centers (RF ~ MHz-GHz ... near-UV ~ 3.5 eV).
SURVEY_BANDS: tuple[tuple[str, float], ...] = (
    ("RF", 4.0e-6),
    ("microwave", 4.0e-4),
    ("THz", 4.0e-3),
    ("IR", 1.0e-1),
    ("visible", 2.3),
    ("near-UV", 3.5),
)


@dataclass(frozen=True)
class BandResult:
    band: str
    center_ev: float
    regime: str
    cooperativity: float


def resonance_survey(coupling_fraction: float, cavity_loss_ev: float,
                     matter_loss_ev: float,
                     thresholds: ModelThresholds) -> tuple[BandResult, ...]:
    """Sweep every survey band, classifying the coupling regime and cooperativity.

    Each band is a mode at that center energy with g = coupling_fraction * center.
    Order is fixed (``SURVEY_BANDS``) and deterministic.
    """
    out = []
    for name, center in SURVEY_BANDS:
        mode = ElectromagneticMode(mode_energy_ev=center,
                                   coupling_energy_ev=coupling_fraction * center,
                                   cavity_loss_ev=cavity_loss_ev,
                                   matter_loss_ev=matter_loss_ev)
        out.append(BandResult(name, center, coupling_regime(mode, thresholds), mode.cooperativity))
    return tuple(out)


def strongest_band(results: tuple[BandResult, ...]) -> BandResult | None:
    """The non-weak band with the highest cooperativity, or None if all are weak.

    Ties resolve to the earliest band in ``SURVEY_BANDS`` order (deterministic)."""
    non_weak = [r for r in results if r.regime != "weak"]
    if not non_weak:
        return None
    best = non_weak[0]
    for r in non_weak[1:]:
        if r.cooperativity > best.cooperativity:
            best = r
    return best
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (14 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): broadband RF->near-UV resonance survey"
```

---

### Task 5: Causal magnetism↔coherence link (default-blocked)

**Files:**
- Modify: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: `orme_lab.evidence.EvidenceLevel`.
- Produces: `@dataclass(frozen=True) CausalLink(tracks, dM_dP, on_resonance, evidence_level_if_confirmed, note)`; `magnetism_tracks_resonance(*, measured_dM_dP=None, on_resonance=None, min_response=1e-9) -> CausalLink`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_optical.py`:

```python
from orme_lab.hudson_optical import CausalLink, magnetism_tracks_resonance


def test_causal_link_defaults_to_unestablished_without_measurement():
    # Hudson linked the circulating mode to the Meissner response. Without a measured
    # dM/dP at resonance, the model cannot assert the causal link.
    link = magnetism_tracks_resonance(measured_dM_dP=None, on_resonance=None)
    assert link.tracks is False
    assert "requires" in link.note


def test_causal_link_requires_response_on_resonance():
    # a real dM/dP but measured OFF resonance does not support the causal claim
    off = magnetism_tracks_resonance(measured_dM_dP=1.0, on_resonance=False)
    assert off.tracks is False
    on = magnetism_tracks_resonance(measured_dM_dP=1.0, on_resonance=True)
    assert on.tracks is True
    assert on.evidence_level_if_confirmed == int(EvidenceLevel.INITIAL_OBSERVATION)


def test_causal_link_rejects_negligible_response():
    link = magnetism_tracks_resonance(measured_dM_dP=1e-15, on_resonance=True)
    assert link.tracks is False    # below min_response -> no anomaly
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ImportError: cannot import name 'CausalLink'`.

- [ ] **Step 3: Implement**

Add to `src/orme_lab/hudson_optical.py`:

```python
@dataclass(frozen=True)
class CausalLink:
    """The C(omega) = dM/dP_drive test: does the magnetic response track the optical
    resonance? An optical anomaly with NO linked magnetic anomaly does not support
    full Hudson."""
    tracks: bool
    dM_dP: float | None
    on_resonance: bool | None
    evidence_level_if_confirmed: int
    note: str


def magnetism_tracks_resonance(*, measured_dM_dP: float | None = None,
                               on_resonance: bool | None = None,
                               min_response: float = 1e-9) -> CausalLink:
    """Default-blocked causal-magnetism gate.

    Requires an externally measured dM/dP that (a) is measured ON resonance and
    (b) exceeds ``min_response``. Absent a measurement, or off resonance, the link is
    unestablished. A confirmed on-resonance magnetic response is a Level-4 observation.
    """
    if measured_dM_dP is None or on_resonance is None:
        return CausalLink(False, measured_dM_dP, on_resonance,
                          int(EvidenceLevel.LABORATORY_PREDICTION),
                          "unestablished: requires a measured dM/dP taken while sweeping "
                          "through the optical/RF resonance (a lab input).")
    tracks = bool(on_resonance) and abs(measured_dM_dP) >= min_response
    ev = int(EvidenceLevel.INITIAL_OBSERVATION) if tracks else int(EvidenceLevel.LABORATORY_PREDICTION)
    if not on_resonance:
        note = "magnetic response measured off resonance: does not support the causal link."
    elif not tracks:
        note = "magnetic response at/below the noise floor on resonance: no anomaly."
    else:
        note = "magnetic response appears/strengthens on resonance: causal link supported."
    return CausalLink(tracks, measured_dM_dP, on_resonance, ev, note)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (17 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): default-blocked causal magnetism<->coherence link"
```

---

### Task 6: `HudsonOpticalResult` + claim-level ladder + `evaluate_hudson_optical`

**Files:**
- Modify: `src/orme_lab/hudson_optical.py`
- Test: `tests/test_hudson_optical.py`

**Interfaces:**
- Consumes: everything above; `orme_lab.evidence.EvidenceLevel, LAB_CEILING`.
- Produces: `class HudsonClaim(IntEnum)` (levels 1..8); `@dataclass(frozen=True) HudsonOpticalResult(order_parameter, regime, persistence, causal_link, strongest_band, supported, evidence_level)` with `supported: frozenset[HudsonClaim]`, property `highest_supported`, method `explain()`; `evaluate_hudson_optical(*, number_density_m3, anisotropy_score, thresholds, matter_ev=None, coupling_fraction=0.05, cavity_loss_ev=0.10, matter_loss_ev=0.05, effective_mass_ratio=1.0, measured_ringdown_fs=None, measured_dM_dP=None, dM_dP_on_resonance=None) -> HudsonOpticalResult`. `matter_ev=None` means "on resonance with the computed mode" — the caller need not know the plasmon energy.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_optical.py`:

```python
from orme_lab.evidence import LAB_CEILING
from orme_lab.hudson_optical import (
    HudsonClaim,
    HudsonOpticalResult,
    evaluate_hudson_optical,
)


def _strong_coherent(**kw):
    # a strongly-coupled, coherent candidate (high density -> real plasmon, strong g)
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4,
                                   thresholds=TH, matter_ev=9.0, coupling_fraction=0.3,
                                   cavity_loss_ev=0.02, matter_loss_ev=0.02, **kw)


def test_levels_are_independent_none_implies_the_next():
    # Strong coupling (L3) supported by SIMULATION, but transport (L5, needs persistence)
    # and magnetism (L7, needs dM/dP) are NOT — because both are default-blocked.
    r = _strong_coherent()
    assert HudsonClaim.STRONG_COUPLING in r.supported
    assert HudsonClaim.LOW_LOSS_TRANSPORT not in r.supported     # no measured ring-down
    assert HudsonClaim.MAGNETISM_COUPLED not in r.supported      # no measured dM/dP
    assert HudsonClaim.HUDSON_PHASE not in r.supported           # conjunction at the top


def test_full_stack_supported_only_with_both_lab_inputs():
    r = _strong_coherent(measured_ringdown_fs=1e30,             # persistent
                         measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert HudsonClaim.LOW_LOSS_TRANSPORT in r.supported
    assert HudsonClaim.MAGNETISM_COUPLED in r.supported
    assert HudsonClaim.HUDSON_PHASE in r.supported


def test_result_evidence_level_is_clamped_to_lab_ceiling():
    # What the SIMULATION produces never exceeds Level 2, even with lab inputs folded in.
    r = _strong_coherent(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert r.evidence_level <= int(LAB_CEILING)


def test_weak_candidate_supports_at_most_resonance_detection():
    r = evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.0,
                                thresholds=TH, matter_ev=9.0, coupling_fraction=1e-6,
                                cavity_loss_ev=1.0, matter_loss_ev=1.0)
    assert HudsonClaim.STRONG_COUPLING not in r.supported
    assert r.explain()   # non-empty, mentions the branch is not superconductivity evidence
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: FAIL — `ImportError: cannot import name 'HudsonClaim'`.

- [ ] **Step 3: Implement**

Add to `src/orme_lab/hudson_optical.py` (add `from enum import Enum, IntEnum`, and `from .evidence import EvidenceLevel, LAB_CEILING`, and `from .electromagnetic_coherence import ElectromagneticMode, coupling_regime, evaluate_em_coherence`):

```python
class HudsonClaim(IntEnum):
    """Hudson optical-coherence claim hierarchy (Branch B). Each level is an
    INDEPENDENT finding: a supported level does NOT imply the one below it. Levels
    9 (independent reproduction) and 10 (practical transduction) require real labs
    and are out of this module's scope."""
    RESONANCE_DETECTED = 1        # an EM resonance exists
    RESONANCE_ASSIGNED = 2        # assigned to the candidate material
    STRONG_COUPLING = 3           # strong light-matter coupling (hybrid mode)
    MACRO_COHERENCE = 4           # macroscopic optical coherence
    LOW_LOSS_TRANSPORT = 5        # low-loss coherent energy transport (persistence)
    ELECTRONIC_COUPLING = 6       # electronic coupling to the coherent mode
    MAGNETISM_COUPLED = 7         # magnetic response coupled to the coherent mode
    HUDSON_PHASE = 8              # full Hudson-type optical superconductive phase


@dataclass(frozen=True)
class HudsonOpticalResult:
    order_parameter: OpticalOrderParameter
    regime: str
    persistence: PersistenceResult
    causal_link: CausalLink
    strongest_band: "BandResult | None"
    supported: frozenset            # frozenset[HudsonClaim]
    evidence_level: int             # clamped to LAB_CEILING

    @property
    def highest_supported(self) -> int:
        return max((int(c) for c in self.supported), default=0)

    def explain(self) -> str:
        levels = ", ".join(str(int(c)) for c in sorted(self.supported)) or "none"
        return (
            f"Branch B (Hudson optical coherence): {self.regime} coupling; supported "
            f"claim levels {{{levels}}}. Persistence={self.persistence.persistence.value}; "
            f"causal magnetism tracks resonance={self.causal_link.tracks}. This is NOT "
            f"evidence of DC superconductivity (Branch A); a coherent optical mode without "
            f"a linked persistent, magnetically-coupled state remains an ordinary "
            f"driven-dissipative response. All quantities are toy/surrogate."
        )


def evaluate_hudson_optical(*, number_density_m3: float, anisotropy_score: float,
                            thresholds: ModelThresholds, matter_ev: float | None = None,
                            coupling_fraction: float = 0.05, cavity_loss_ev: float = 0.10,
                            matter_loss_ev: float = 0.05, effective_mass_ratio: float = 1.0,
                            measured_ringdown_fs: float | None = None,
                            measured_dM_dP: float | None = None,
                            dM_dP_on_resonance: bool | None = None) -> HudsonOpticalResult:
    """Full Branch-B evaluation for one candidate.

    Simulation-supportable levels (1-4, 6) come from the mode algebra; levels 5
    (transport/persistence) and 7 (causal magnetism) are default-blocked and require
    the optional measured inputs. Level 8 (full Hudson phase) is the conjunction of
    the strong-coupling, coherence, transport, electronic, and magnetism levels — a
    top-level PREDICTION, never a crediting verdict. ``evidence_level`` is what the
    SIMULATION produces and is clamped to LAB_CEILING regardless of folded lab inputs.
    """
    coh = evaluate_em_coherence(number_density_m3, anisotropy_score, thresholds,
                                coupling_fraction=coupling_fraction, cavity_loss_ev=cavity_loss_ev,
                                matter_loss_ev=matter_loss_ev, effective_mass_ratio=effective_mass_ratio)
    mode = coh.mode
    mev = mode.mode_energy_ev if matter_ev is None else matter_ev   # None -> on resonance
    o_h = order_parameter_from_mode(mode, mev, thresholds)
    persistence = classify_persistence(o_h, measured_ringdown_fs=measured_ringdown_fs, thresholds=thresholds)
    link = magnetism_tracks_resonance(measured_dM_dP=measured_dM_dP, on_resonance=dM_dP_on_resonance)
    survey = resonance_survey(coupling_fraction, cavity_loss_ev, matter_loss_ev, thresholds)
    best = strongest_band(survey)

    s: set = set()
    if mode.mode_energy_ev > 0:
        s.add(HudsonClaim.RESONANCE_DETECTED)
        s.add(HudsonClaim.RESONANCE_ASSIGNED)           # assigned to this candidate's carriers
    strong = coh.regime != "weak"
    if strong:
        s.add(HudsonClaim.STRONG_COUPLING)
    # macroscopic coherence: a genuine hybrid (photon fraction above floor) in a
    # non-weak regime with a positive coherence score.
    if strong and o_h.f_photon >= thresholds.hudson_min_photon_fraction and coh.coherence_score > 0:
        s.add(HudsonClaim.MACRO_COHERENCE)
    # electronic coupling to the mode: a non-negligible electronic (matter) fraction.
    if strong and o_h.f_electron >= thresholds.hudson_min_photon_fraction:
        s.add(HudsonClaim.ELECTRONIC_COUPLING)
    # transport (level 5) requires a persistent (or at least metastable) measured ring-down.
    if persistence.persistence in (Persistence.PERSISTENT, Persistence.METASTABLE):
        s.add(HudsonClaim.LOW_LOSS_TRANSPORT)
    # magnetism (level 7) requires the measured causal link.
    if link.tracks:
        s.add(HudsonClaim.MAGNETISM_COUPLED)
    # full Hudson phase (level 8): conjunction at the top — the coherent, transporting,
    # electronically-coupled, magnetically-coupled state.
    if {HudsonClaim.STRONG_COUPLING, HudsonClaim.MACRO_COHERENCE, HudsonClaim.LOW_LOSS_TRANSPORT,
        HudsonClaim.ELECTRONIC_COUPLING, HudsonClaim.MAGNETISM_COUPLED}.issubset(s):
        s.add(HudsonClaim.HUDSON_PHASE)

    ev = int(min(EvidenceLevel(int(LAB_CEILING)),
                 EvidenceLevel.SIMULATION_CANDIDATE if s else EvidenceLevel.CONCEPT))
    return HudsonOpticalResult(o_h, coh.regime, persistence, link, best, frozenset(s), ev)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_optical.py -q`
Expected: PASS (21 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_optical.py tests/test_hudson_optical.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): HudsonOpticalResult + independent claim-level ladder"
```

---

### Task 7: Wire Branch B into the pipeline record

**Files:**
- Modify: `src/orme_lab/pipeline.py` (`CandidateRecord`, `evaluate_candidate`, `as_csv_row`)
- Test: `tests/test_pipeline.py` (append)

**Grounding (verified against `pipeline.py` at plan time):** the EM channel lives at the `if config.compute_em_coherence:` block; inside it `n = free_electron_density(element)`, `anisotropy` is already in scope (computed at the density-anisotropy seam, always), and `th = config.thresholds`. `DEFAULT_CONFIG.compute_em_coherence` is **`False`**, and `compute_em_coherence` is a field of `LabConfig` (the flag), NOT `ModelThresholds`. Branch B therefore gets its OWN flag and must not depend on the EM flag being on.

**Interfaces:**
- Consumes: `evaluate_hudson_optical`; `free_electron_density(element)` (hoisted to a single computation of `n`); the `anisotropy` local; `th = config.thresholds`.
- Produces: `LabConfig` gains `compute_hudson_optical: bool = False`; `CandidateRecord` new fields `hudson_regime: str | None = None`, `hudson_photon_fraction: float | None = None`, `hudson_persistence: str | None = None`, `hudson_highest_claim: int = 0`, `hudson_supported_levels: tuple[int, ...] = ()`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_pipeline.py`:

```python
def test_candidate_record_carries_branch_b_fields():
    from dataclasses import replace
    from orme_lab.config import DEFAULT_CONFIG
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate

    cfg = replace(DEFAULT_CONFIG, compute_hudson_optical=True)   # Branch B is opt-in
    el = get_element("Au")
    rec = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                             high_spin_state(el), cfg)
    # Branch B fields present and independent of the SC verdict
    assert rec.hudson_regime in ("weak", "strong", "ultrastrong")
    assert isinstance(rec.hudson_supported_levels, tuple)
    assert rec.hudson_highest_claim >= 0
    # default (no lab inputs): transport (5) and magnetism (7) cannot be supported
    assert 5 not in rec.hudson_supported_levels
    assert 7 not in rec.hudson_supported_levels
    # csv row renders the new fields without error
    row = rec.as_csv_row()
    assert "hudson_regime" in row and "hudson_supported_levels" in row


def test_branch_b_off_by_default():
    from orme_lab.config import DEFAULT_CONFIG
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate

    el = get_element("Au")
    rec = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                             high_spin_state(el), DEFAULT_CONFIG)   # flag off
    assert rec.hudson_regime is None and rec.hudson_supported_levels == ()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_pipeline.py -k branch_b -q`
Expected: FAIL — `TypeError: ... unexpected keyword argument 'compute_hudson_optical'` (or `AttributeError: hudson_regime`).

- [ ] **Step 3: Implement**

In `config.py` `LabConfig`, add next to `compute_em_coherence`:

```python
    #: Compute Branch B (Hudson optical-coherence) for each candidate. Off by
    #: default (like the EM channel); the base SC screen stays lightweight.
    compute_hudson_optical: bool = False
```

In `pipeline.py` `CandidateRecord`, add after the `surviving_mechanisms` field:

```python
    # --- Branch B (Hudson optical coherence) — independent of the SC AND-gate ---
    hudson_regime: str | None = None
    hudson_photon_fraction: float | None = None
    hudson_persistence: str | None = None
    hudson_highest_claim: int = 0
    hudson_supported_levels: tuple[int, ...] = ()
```

In `evaluate_candidate`, **hoist the carrier density** so it is a single source of truth for both channels. Replace the `n = free_electron_density(element)` line inside the `if config.compute_em_coherence:` block with a hoisted computation placed just above that block:

```python
    n = free_electron_density(element)          # carrier density: shared by EM + Branch B
    em_score = em_regime = em_rabi = em_lifetime = None
    if config.compute_em_coherence:
        coh = evaluate_em_coherence(n, anisotropy, th)
        em_score = coh.coherence_score
        em_regime = coh.regime
        em_rabi = coh.mode.rabi_splitting_ev
        em_lifetime = coh.mode.coherence_lifetime_fs

    # Branch B (Hudson optical coherence): opt-in, independent of the EM flag and of
    # the SC AND-gate. matter_ev omitted -> evaluated on resonance with the computed mode.
    hud_regime = hud_photon = hud_persistence = None
    hud_highest = 0
    hud_levels: tuple[int, ...] = ()
    if config.compute_hudson_optical:
        from .hudson_optical import evaluate_hudson_optical
        hud = evaluate_hudson_optical(number_density_m3=n, anisotropy_score=anisotropy,
                                      thresholds=th, coupling_fraction=0.05)
        hud_regime = hud.regime
        hud_photon = hud.order_parameter.f_photon
        hud_persistence = hud.persistence.persistence.value
        hud_highest = hud.highest_supported
        hud_levels = tuple(sorted(int(c) for c in hud.supported))
```

Pass the five locals into the `CandidateRecord(...)` construction:

```python
        hudson_regime=hud_regime,
        hudson_photon_fraction=hud_photon,
        hudson_persistence=hud_persistence,
        hudson_highest_claim=hud_highest,
        hudson_supported_levels=hud_levels,
```

In `as_csv_row`, join `hudson_supported_levels` with `"|"` (the method already does this for `surviving_mechanisms` — mirror it) and add the scalar `hudson_*` fields to the emitted dict.

**Do NOT** introduce a second carrier-density computation — the hoisted `n` is the single source (determinism + single source of truth). Branch B computes its own coherence result internally via `evaluate_hudson_optical`; that is intentional (Branch B must stand alone even when the EM channel is off), and is not a duplicate of `n`.

- [ ] **Step 4: Run to verify it passes + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_pipeline.py -q && python3 -m pytest -q`
Expected: PASS (new tests green; full suite green — `DEFAULT_CONFIG` leaves Branch B off, so existing screen tests are unaffected).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/config.py src/orme_lab/pipeline.py tests/test_pipeline.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): opt-in Branch-B result on CandidateRecord"
```

---

### Task 8: Register Branch B as off-gate-independent in the closure oracle

**Files:**
- Modify: `src/orme_lab/lab_loop/closure.py` (`OFF_GATE_INVARIANTS`)
- Test: `tests/test_closure.py` (update golden)

**Interfaces:**
- Consumes: nothing new.
- Produces: `OFF_GATE_INVARIANTS` gains `"hudson_regime"`, `"hudson_photon_fraction"`, `"hudson_persistence"`, `"hudson_highest_claim"`, `"hudson_supported_levels"`. These are genuinely independent of the SC AND-gate (same argument as the `em_coherence_*` fields).

- [ ] **Step 1: Read the golden test**

Run: `cd /orme-lab && grep -n "OFF_GATE_INVARIANTS\|GATE_INPUT_CLOSURE\|hudson\|em_coherence" tests/test_closure.py`
Note the exact pinned frozenset(s) the golden test compares against.

- [ ] **Step 2: Update the golden test first (it should now fail against the un-updated source)**

In `tests/test_closure.py`, add the five `hudson_*` names to the expected `OFF_GATE_INVARIANTS` golden set (alongside the `em_coherence_*` and `identity_*` entries). Do NOT add them to the `GATE_INPUT_CLOSURE` golden.

- [ ] **Step 3: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_closure.py -q`
Expected: FAIL — the source `OFF_GATE_INVARIANTS` is missing the five `hudson_*` names.

- [ ] **Step 4: Implement**

In `closure.py`, extend `OFF_GATE_INVARIANTS` with a commented block:

```python
    # Hudson optical-coherence channel (Branch B): a distinct, independent signal
    # from the SC AND-gate — the resonantly-accessible hybrid light-matter mode, its
    # persistence, and its claim-level ladder. Never re-derivable from the gate inputs.
    "hudson_regime", "hudson_photon_fraction", "hudson_persistence",
    "hudson_highest_claim", "hudson_supported_levels",
```

- [ ] **Step 5: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_closure.py -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/lab_loop/closure.py tests/test_closure.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): pin Branch-B fields as off-gate-independent in closure"
```

---

### Task 9: Two-branch verdict object

**Files:**
- Create: `src/orme_lab/branch_verdict.py`
- Test: `tests/test_branch_verdict.py`

**Interfaces:**
- Consumes: `orme_lab.pipeline.CandidateRecord`, `orme_lab.hudson_optical.HudsonOpticalResult, HudsonClaim`.
- Produces: `@dataclass(frozen=True) BranchVerdict(element, branch_a_credited, branch_b_levels, hudson_phase_predicted)`; `combine_branches(record, hudson) -> BranchVerdict`; method `explain()`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_branch_verdict.py`:

```python
"""Tests for the two-branch (A: SC / B: Hudson optical) verdict."""
from __future__ import annotations

from orme_lab.config import DEFAULT_CONFIG
from orme_lab.branch_verdict import BranchVerdict, combine_branches
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.hudson_optical import HudsonClaim, evaluate_hudson_optical
from orme_lab.identity import IdentityWitness
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state

TH = DEFAULT_CONFIG.thresholds


def _record(sym, identity=None):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG, identity=identity)


def _hudson(**kw):
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4,
                                   thresholds=TH, matter_ev=9.0, coupling_fraction=0.3,
                                   cavity_loss_ev=0.02, matter_loss_ev=0.02, **kw)


def test_branches_are_reported_independently():
    w = IdentityWitness("Au", "metallic", "sub-nm-cluster", 0.0, ("XRD",))
    rec = _record("Au", identity=w)
    hud = _hudson()                                  # strong coupling, no lab inputs
    v = combine_branches(rec, hud)
    assert isinstance(v, BranchVerdict)
    assert v.branch_a_credited == rec.credited_sc_lead
    assert HudsonClaim.STRONG_COUPLING in v.branch_b_levels
    # Branch B (no persistence, no magnetism) cannot predict the full Hudson phase
    assert v.hudson_phase_predicted is False


def test_hudson_phase_predicted_only_with_full_branch_b_stack():
    rec = _record("Au", identity=IdentityWitness("Au", "metallic", "sub-nm-cluster", 0.0, ("XRD",)))
    hud = _hudson(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    v = combine_branches(rec, hud)
    assert HudsonClaim.HUDSON_PHASE in hud.supported
    assert v.hudson_phase_predicted is True


def test_branch_b_does_not_set_branch_a():
    # A candidate with NO identity witness is not credited in Branch A regardless of a
    # strong Branch B — the optical branch never rescues the SC gate.
    rec = _record("Au")                              # no identity -> not credited
    hud = _hudson(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    v = combine_branches(rec, hud)
    assert v.branch_a_credited is False
    assert HudsonClaim.HUDSON_PHASE in v.branch_b_levels
    assert "independent" in v.explain().lower()
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_branch_verdict.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.branch_verdict'`.

- [ ] **Step 3: Implement**

Create `src/orme_lab/branch_verdict.py`:

```python
"""Two-branch verdict: Branch A (conventional superconductivity) and Branch B
(Hudson optical coherence) reported as INDEPENDENT results.

The branches must not be merged prematurely. A material can be a room-temperature
polariton condensate (Branch B) without being an electrical superconductor (Branch A),
and vice versa. This object reports each branch's verdict separately; the full
"Hudson-type optical superconductive phase" is the conjunction at the TOP only, and
is emitted as a PREDICTION (``hudson_phase_predicted``), never as a crediting verdict
and never as a blended numeric score. Branch B never sets Branch A's crediting and
vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hudson_optical import HudsonClaim, HudsonOpticalResult
from .pipeline import CandidateRecord


@dataclass(frozen=True)
class BranchVerdict:
    element: str
    branch_a_credited: bool               # SC lead credited (identity ∧ gate ∧ mechanism)
    branch_b_levels: frozenset            # frozenset[HudsonClaim] independently supported
    hudson_phase_predicted: bool          # claim level 8 — a top-level PREDICTION only

    def explain(self) -> str:
        b = ", ".join(str(int(c)) for c in sorted(self.branch_b_levels)) or "none"
        return (
            f"{self.element}: Branch A (superconductivity) credited={self.branch_a_credited}; "
            f"Branch B (Hudson optical) supported levels {{{b}}}. The two branches are "
            f"INDEPENDENT — neither rescues the other. Full Hudson optical superconductive "
            f"phase (level 8) predicted={self.hudson_phase_predicted} (a laboratory "
            f"prediction, not a crediting verdict)."
        )


def combine_branches(record: CandidateRecord, hudson: HudsonOpticalResult) -> BranchVerdict:
    """Assemble the independent two-branch verdict. Reads each branch's own verdict;
    performs no cross-branch arithmetic."""
    return BranchVerdict(
        element=record.element,
        branch_a_credited=record.credited_sc_lead,
        branch_b_levels=hudson.supported,
        hudson_phase_predicted=HudsonClaim.HUDSON_PHASE in hudson.supported,
    )
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_branch_verdict.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/branch_verdict.py tests/test_branch_verdict.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): independent two-branch verdict (A: SC / B: optical)"
```

---

### Task 10: Promote the optical route to first-class Branch-B decisive experiments in the validator

**Files:**
- Modify: `src/orme_lab/validator.py`
- Test: `tests/test_validator.py` (append)

**Interfaces:**
- Consumes: `CandidateRecord.hudson_supported_levels` (Task 7), the existing `_test` helper and `AdversarialTest`/`ValidationSuite` in `validator.py`.
- Produces: `_branch_b_tests(record) -> tuple[AdversarialTest, ...]` emitting the Branch-B decisive experiments; `design_validation` appends them; the ring-down test is `decisive=True` with `ev_conf=_INITIAL_OBS`, all others carry their honest `decisive` flags. The existing generic branch table and mechanism-routed tests are unchanged.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_validator.py`:

```python
def test_branch_b_decisive_experiments_present():
    # Branch B is a first-class experiment set, no longer only a "mundane alternative".
    s = design_validation(_record("Au"))
    ms = _measurements(s)
    for m in ("broadband resonance survey", "polariton anticrossing",
              "optical coherence (g1/g2)", "resonant injection ring-down",
              "energy-transfer geometry", "magnetism vs resonance (dM/dP)"):
        assert m in ms, m


def test_ringdown_is_the_decisive_branch_b_test():
    s = design_validation(_record("Au"))
    rd = next(t for t in s.tests if t.measurement == "resonant injection ring-down")
    assert rd.decisive is True
    assert rd.evidence_level_if_confirmed == 4        # persistent ring-down = an observation
    # its mundane alternative is the ordinary driven-dissipative polariton condensate
    assert any("driven-dissipative" in alt[0] or "driven-dissipative" in alt[1]
               for alt in rd.mundane_alternatives)


def test_broadband_survey_is_not_visible_only():
    s = design_validation(_record("Au"))
    surv = next(t for t in s.tests if t.measurement == "broadband resonance survey")
    assert "RF" in surv.claimed_signature or "RF" in surv.note
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_validator.py -q`
Expected: FAIL — the Branch-B measurements are not emitted.

- [ ] **Step 3: Implement**

In `validator.py`, add a `_branch_b_tests(record)` function that returns these `AdversarialTest`s (via the existing `_test` helper), then append `tests.extend(_branch_b_tests(record))` in `design_validation` after the mechanism-routed loop:

```python
def _branch_b_tests(record) -> tuple:
    """Branch B (Hudson optical coherence) decisive experiments. Optical coherence is
    Hudson's PRIMARY claim here, not a mundane alternative to SC — but it must still
    survive the ordinary optical explanations (fluorescence, Raman, thermal, Mie,
    nanoparticle plasmon, cavity leakage), and the decisive test is the post-drive
    ring-down that separates a self-sustaining mode from a driven-dissipative one."""
    return (
        _test("broadband resonance survey", "VNA S11/S21 + FTIR + THz-TDS + UV-Vis",
              "a resonance somewhere RF->near-UV assignable to the material (light is NOT "
              "restricted to visible; Hudson tuned with RF)",
              [("no resonance / substrate feature", "no material-assigned peak"),
               ("thermal/blackbody background", "broad, temperature-scaling, non-resonant")],
              "no material-assigned resonance in any band -> nothing to hybridize", False,
              note="Hudson described RF tuning while calling the state 'light'; sweep RF->UV"),
        _test("polariton anticrossing", "tunable cavity / dispersion mapping",
              "avoided crossing with minimum gap 2g > linewidth as the mode is tuned "
              "through resonance (a genuine hybrid)",
              [("two unrelated peaks", "peaks cross; no anticrossing"),
               ("single dressed resonance", "no second branch")],
              "peaks cross (no avoided crossing) -> not a hybrid light-matter mode", True),
        _test("optical coherence (g1/g2)", "interferometry + Hanbury-Brown-Twiss",
              "first/second-order coherence, linewidth narrowing, threshold (condensate-like)",
              [("fluorescence", "g2(0)~1, no threshold, broad"),
               ("Raman/thermal emission", "incoherent; no phase stability")],
              "g2/linewidth consistent with incoherent emission -> not macroscopic coherence", True),
        _test("resonant injection ring-down", "pump-probe: drive at resonance, cut drive, watch decay",
              "post-drive ring-down far exceeding the mode lifetime (self-sustaining / persistent)",
              [("driven-dissipative polariton condensate", "decays on the mode timescale; needs pumping"),
               ("cavity leakage", "decays at the bare cavity rate")],
              "decays on the mode timescale -> ordinary driven-dissipative, not persistent", True,
              note="THE decisive Branch-B test: most room-temperature polariton condensates are "
                   "driven-dissipative; Hudson's stronger claim implies a persistent internal mode"),
        _test("energy-transfer geometry", "separated input/output couplers, sample between",
              "low-loss coherent transport through the phase (eta(omega), phase delay, size scaling)",
              [("local luminescence", "no transport; emission co-located with drive"),
               ("EM leakage around sample", "transport survives interrupting the material path")],
              "'transport' survives cutting the material path -> leakage, not through-phase transport", True),
        _test("magnetism vs resonance (dM/dP)", "SQUID while sweeping the optical/RF resonance",
              "magnetic response appears/strengthens ON resonance (C(omega)=dM/dP_drive), same "
              "threshold and decay as the coherent mode",
              [("magnetism uncorrelated with resonance", "flat dM/dP through resonance"),
               ("microwave/optical heating", "thermal magnetization shift, not resonant")],
              "no magnetic response tracking the resonance -> optical anomaly without the Hudson "
              "magnetic link (fails full Hudson)", True),
    )
```

Update `_branch_b_tests`'s reference in `design_validation` and its docstring note that Branch B is emitted unconditionally alongside the generic table (it is the mechanism-agnostic optical baseline). Ensure `_test`'s `decisive`→`ev_conf` default already gives the ring-down (decisive) test `ev_conf=4` and the survey (non-decisive) `ev_conf=3` — no override needed.

- [ ] **Step 4: Run to verify it passes + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_validator.py -q && python3 -m pytest -q`
Expected: PASS (validator tests green; full suite green).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/validator.py tests/test_validator.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(hudson): promote optical route to first-class Branch-B decisive experiments"
```

---

## Self-Review

**Spec coverage (against the operator's message):**
- Two independent branches (A conventional SC, B Hudson optical) — Tasks 6, 9 (`HudsonOpticalResult`, `BranchVerdict`), Task 8 (independence pinned in closure).
- `O_H = {ω₀, Q, g, τ_coh, L_coh, f_ph, f_el}` — Task 2 (`OpticalOrderParameter`).
- "electrons become light" NOT literal — module docstring (Task 1) encodes the hybrid `|P⟩` with measurable fractions, not literal photons.
- Broad resonance survey, not visible-only — Task 4 (`SURVEY_BANDS` RF→near-UV), validator survey test (Task 10).
- Strong-coupling anticrossing `E_±` — Tasks 1 (`polariton_branches`, `is_anticrossing`), 10 (anticrossing experiment).
- Coherence not emission (g⁽¹⁾/g⁽²⁾) — Task 10 experiment; the coherence score is Branch B's `regime`/`coherence_score`.
- Resonant injection + ring-down — Task 3 (`classify_persistence`), Task 10 (decisive experiment).
- Energy-transfer geometry — Task 10 experiment.
- Correlate coherence with magnetism `C(ω)=∂M/∂P` — Task 5 (`magnetism_tracks_resonance`), Task 10 experiment.
- Revised claim hierarchy (levels 1–8, none implies the next) — Task 6 (`HudsonClaim`, independent `supported` set).
- Persistent vs driven-dissipative is decisive — Task 3 (default-blocked; only a measured persistent ring-down reaches Level 4).
- Levels 9–10 (reproduction, transduction) and the full `G_Hudson` ledger — explicitly deferred (Global Constraints "out of scope").

**Placeholder scan:** none — every code step contains the actual implementation and the actual test.

**Type consistency:** `HudsonOpticalResult.supported` is `frozenset[HudsonClaim]` in Tasks 6, 9, 10; `evaluate_hudson_optical` signature matches its call in Task 7 (kwargs `number_density_m3`, `anisotropy_score`, `matter_ev`, `coupling_fraction`, optional `measured_ringdown_fs`/`measured_dM_dP`/`dM_dP_on_resonance`); `classify_persistence`/`magnetism_tracks_resonance` return the `PersistenceResult`/`CausalLink` used in Task 6. `CandidateRecord` Branch-B field names (`hudson_regime`, `hudson_photon_fraction`, `hudson_persistence`, `hudson_highest_claim`, `hudson_supported_levels`) are identical in Tasks 7, 8, 10.

**Integration points verified at plan time (against `pipeline.py`/`config.py`):** the carrier-density local is `n = free_electron_density(element)` (Task 7 hoists it to a single computation); `anisotropy` and `th = config.thresholds` are in scope; `compute_em_coherence` is a `LabConfig` flag defaulting to `False`. Branch B gets its own opt-in `compute_hudson_optical` flag (also `False` by default), so the base SC screen and every existing screen test are unaffected — Task 7 includes an explicit `test_branch_b_off_by_default` guard. This removes the "does the flag change break the suite" risk that would otherwise surface only at execution.
