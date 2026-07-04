# Ir Per-Element EPW λ — Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement the CODE tasks (Task C1–C4) task-by-task. The COMPUTE tiers (Tier 0/1/2) are gated live-run procedures, not TDD tasks — execute them by their checklists and honour every go/no-go gate. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Produce a converged phonon-channel electron–phonon coupling λ (and Allen-Dynes Tc) for the Ir approximant using real QE 7.3.1 / EPW 5.8.1, with the Wannier recipe locked and every claim honestly bounded — reaching the physically-relevant high-spin ORME state only if the toolchain supports magnetic elph, and reporting an honest negative if it does not.

**Architecture:** The lab already owns a validated deterministic deck pipeline (`src/orme_lab/epw/`, proven end-to-end on fcc-Pb, λ=1.19). This plan adds (a) a committed, reproducible Ir run driver + config, (b) a convergence-gate checker, and (c) a three-tier live-compute procedure: Tier 0 non-magnetic calibration → Tier 1 EPW-magnetism capability gate → Tier 2 high-spin ORME run. Each tier is a go/no-go gate with a standalone deliverable.

**Tech Stack:** Python 3 (existing `orme_lab.epw`), Quantum ESPRESSO 7.3.1 + EPW 5.8.1 built from source (Debian package is broken — FORTIFY SIGABRT), OpenMPI, SSSP pseudopotentials, Wannier90 (bundled in EPW), pytest.

## Global Constraints

- **Reference lattice is counterfactual and code-derived.** `approximant.build_approximant` sets `a = d·√2` (fcc) from the cluster nearest-neighbour distance `d = 2·covalent_radius = 2.82 Å` → **a = 3.988 Å**. Do NOT substitute experimental Ir (3.839 Å) in the model runs; an experimental-lattice run is permitted only as a labelled external-validation *control* (Tier 0 optional step), never as the reported ORME number.
- **Evidence ceiling Level 2.** Every λ/Tc emitted is a phonon-channel spin-state counterfactual on an imposed lattice, NOT a superconductivity estimate for the ORME claim. `min(level, LAB_CEILING=2)` stays in force. No "validated" claim for any Ir λ — Pb validated the *pipeline*, not this number.
- **woSOC.** Spin–orbit omitted (same convention as the validated Pb run; the SOC shortfall is the characterized systematic). Do not enable SOC without a separate decision.
- **Determinism.** All grids/cutoffs pinned in an `EPWConfig`; runs reproducible up to the solver's MPI/BLAS nondeterminism (sc_* columns are not byte-reproducible — documented).
- **Compute envelope (operator's box, hard constraint).** 16 cores, `nice -15`. Baseline load ≈ 21 from operator daemons (Cytherea, QuantumTrader/MT5, ollama) — those PIDs are NEVER touched. Back off (drop to 8 cores / pause `ph.x`) if free RAM < 15 GB, free disk < 30 GB, or nice'd jobs stop yielding. All long stages backgrounded + polled; never foregrounded (5-min tool-timeout kills them).
- **Commit identity.** Commit as `Dezirae Stark <deziraestark69@gmail.com>`. NEVER emit AI-identity trailers (Co-Authored-By / Signed-off-by / Claude-Session).
- **No fabricated capability claims.** The EPW-magnetism support question (Tier 1) is resolved by READING EPW 5.8.1 source/docs, not by assuming. If unresolved, that is itself the finding.

---

## Critical findings that shaped this plan (read first)

1. **All ORME-relevant Ir states are magnetic.** `high_spin_state(Ir)` → unpaired=3, `nspin=2`, `starting_magnetization=0.3`; `low_spin_state(Ir)` → unpaired=1, still `nspin=2`, mag=0.1. Non-magnetic Ir exists only as an artificial `SpinState(Ir, 0)` calibration reference.
2. **The `nspin=2` deck path is real-QE-untested.** `qe_input._system` writes `nspin=2` + `starting_magnetization` for `spin_polarized` approximants, but only spin-degenerate Pb ever ran against real QE. The magnetic SCF/ph/nscf/EPW path is code-present, run-unproven.
3. **EPW collinear-spin elph support is uncertain in 5.8.1** and must be verified before committing to the expensive magnetic run. This is Tier 1's entire purpose.
4. **No external λ check exists** for the expanded counterfactual lattice — confidence rests entirely on the four internal convergence gates (Task C4).

---

## File Structure

- **Create** `src/orme_lab/epw/runs/__init__.py` — package marker for committed run configs.
- **Create** `src/orme_lab/epw/runs/ir.py` — Ir `EPWConfig` factory + the three approximant specs (non-magnetic ref, low-spin, high-spin) as pure builders. One responsibility: pin every Ir run parameter in one reviewable place.
- **Create** `src/orme_lab/epw/convergence.py` — `ConvergenceReport` + gate checks (Wannier-band match, λ vs fine-grid, dynamical stability, Tc). One responsibility: turn raw run outputs into a pass/fail gate verdict. No solver calls.
- **Create** `scripts/run_ir_epw.py` — thin, committed, reproducible driver: build approximant → write decks (existing writers) → drive stages (existing `runner`) → parse → emit `ConvergenceReport`. Replaces the ad-hoc host script used for Pb (which was never committed).
- **Create** `tests/test_epw_ir_run.py` — unit tests for `runs/ir.py` and `convergence.py` (deck contents, spin flags, gate logic). No live QE.
- **Create** `docs/epw-ir-lambda-run.md` — the live-run log + Tier 1 capability finding + final convergence report + honest-caveat block. Written during compute tiers.
- **Modify** `docs/epw-live-validation.md` — add an "Ir per-element run" section pointing at the new run log (single line; the detail lives in the new doc).

---

## Task C1: Ir run config + approximant specs

**Files:**
- Create: `src/orme_lab/epw/runs/__init__.py`
- Create: `src/orme_lab/epw/runs/ir.py`
- Test: `tests/test_epw_ir_run.py`

**Interfaces:**
- Consumes: `EPWConfig` (`epw.config`), `build_approximant`, `get_element`, `make_compact_cluster`, `SpinState`, `high_spin_state`, `low_spin_state`.
- Produces:
  - `ir_config(pseudo_dir: str, upf: str) -> EPWConfig`
  - `ir_approximant(spin: str) -> PeriodicApproximant` where `spin ∈ {"none","low","high"}` ("none" builds `SpinState(get_element("Ir"), 0, is_high_spin=False)`).
  - Module constant `IR_CLUSTER_N = 13`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_epw_ir_run.py
from orme_lab.epw.runs import ir

def test_ir_high_spin_is_spin_polarized():
    ap = ir.ir_approximant("high")
    assert ap.spin_polarized is True
    assert ap.starting_magnetization == 0.3
    assert round(ap.a_angstrom, 3) == 3.988
    assert ap.bravais == "fcc"

def test_ir_none_spin_is_nonmagnetic_reference():
    ap = ir.ir_approximant("none")
    assert ap.spin_polarized is False       # artificial unpaired=0 calibration

def test_ir_config_pins_grids_and_windows():
    cfg = ir.ir_config(pseudo_dir="/pseudo", upf="Ir.upf")
    assert cfg.pseudo_for("Ir") == "Ir.upf"
    assert cfg.q_coarse == (4, 4, 4)
    assert cfg.nbndsub == 6                  # 5 d + 1 s explicit
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_epw_ir_run.py -v`
Expected: FAIL — `ModuleNotFoundError: orme_lab.epw.runs`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/epw/runs/__init__.py
```
```python
# src/orme_lab/epw/runs/ir.py
"""Pinned Ir run parameters. a=3.988 A counterfactual lattice (cluster NN, NOT
experimental Ir). Every ORME-relevant Ir spin state is magnetic (d7); 'none' is
an artificial non-magnetic calibration reference only."""
from __future__ import annotations

from ...elements import get_element
from ...geometry import make_compact_cluster
from ...spin_states import SpinState, high_spin_state, low_spin_state
from ..approximant import PeriodicApproximant, build_approximant
from ..config import EPWConfig

IR_CLUSTER_N = 13

def ir_approximant(spin: str) -> PeriodicApproximant:
    ir = get_element("Ir")
    geom = make_compact_cluster(ir, IR_CLUSTER_N)
    state = {
        "high": high_spin_state(ir),
        "low": low_spin_state(ir),
        "none": SpinState(ir, 0, is_high_spin=False),
    }[spin]
    return build_approximant(ir, geom, state)

def ir_config(pseudo_dir: str, upf: str) -> EPWConfig:
    # ecutwfc/ecutrho: SSSP-recommended for Ir (CONFIRM from the SSSP table at
    # provision time; 60/480 is the Pb-tuned placeholder until then).
    return EPWConfig(
        pseudo_dir=pseudo_dir,
        pseudopotentials=(("Ir", upf),),
        ecutwfc_ry=60.0,
        ecutrho_ry=480.0,
        k_coarse=(8, 8, 8),
        q_coarse=(4, 4, 4),
        k_fine=(20, 20, 20),
        q_fine=(20, 20, 20),
        nbndsub=6,
        mu_star=0.10,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_epw_ir_run.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/runs/ tests/test_epw_ir_run.py
git commit -m "epw: pin Ir run config + spin-state approximants (a=3.988A counterfactual, all ORME states magnetic)"
```

---

## Task C2: Convergence-gate checker

**Files:**
- Create: `src/orme_lab/epw/convergence.py`
- Test: `tests/test_epw_ir_run.py` (append)

**Interfaces:**
- Consumes: nothing external (pure logic over floats/bools the driver extracts).
- Produces:
  - `@dataclass(frozen=True) ConvergenceReport` with fields `wannier_band_max_dev_mev: float`, `lambda_grid_delta_frac: float`, `min_phonon_freq_cm: float`, `lambda_value: float`, `tc_kelvin: float`.
  - `ConvergenceReport.gates() -> dict[str, bool]` returning the four named gates.
  - `ConvergenceReport.trustworthy() -> bool` = all gates pass.

- [ ] **Step 1: Write the failing test**

```python
from orme_lab.epw.convergence import ConvergenceReport

def test_all_gates_pass_for_good_run():
    r = ConvergenceReport(wannier_band_max_dev_mev=3.0, lambda_grid_delta_frac=0.03,
                          min_phonon_freq_cm=12.0, lambda_value=0.41, tc_kelvin=0.2)
    assert r.gates() == {"wannier_match": True, "lambda_converged": True,
                         "dynamically_stable": True, "tc_computed": True}
    assert r.trustworthy() is True

def test_imaginary_phonon_fails_stability_gate():
    r = ConvergenceReport(wannier_band_max_dev_mev=3.0, lambda_grid_delta_frac=0.03,
                          min_phonon_freq_cm=-40.0, lambda_value=0.41, tc_kelvin=0.2)
    assert r.gates()["dynamically_stable"] is False
    assert r.trustworthy() is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_epw_ir_run.py -k convergence -v`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/epw/convergence.py
"""Turn raw Ir-run outputs into a pass/fail trust verdict. Thresholds are the
four gates from the plan; a run failing ANY gate is not trustworthy (Level 2)."""
from __future__ import annotations
from dataclasses import dataclass

_WANNIER_MAX_DEV_MEV = 10.0     # interpolated bands vs DFT near E_F
_LAMBDA_DELTA_FRAC = 0.05       # |Δλ|/λ on fine-grid refinement
_MIN_FREQ_CM = 0.0              # no imaginary modes (soft tol at Gamma handled upstream)

@dataclass(frozen=True)
class ConvergenceReport:
    wannier_band_max_dev_mev: float
    lambda_grid_delta_frac: float
    min_phonon_freq_cm: float
    lambda_value: float
    tc_kelvin: float

    def gates(self) -> dict[str, bool]:
        return {
            "wannier_match": self.wannier_band_max_dev_mev <= _WANNIER_MAX_DEV_MEV,
            "lambda_converged": abs(self.lambda_grid_delta_frac) <= _LAMBDA_DELTA_FRAC,
            "dynamically_stable": self.min_phonon_freq_cm >= _MIN_FREQ_CM,
            "tc_computed": self.tc_kelvin >= 0.0 and self.lambda_value > 0.0,
        }

    def trustworthy(self) -> bool:
        return all(self.gates().values())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_epw_ir_run.py -k convergence -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/convergence.py tests/test_epw_ir_run.py
git commit -m "epw: add ConvergenceReport with the four per-element trust gates"
```

---

## Task C3: Reproducible Ir run driver

**Files:**
- Create: `scripts/run_ir_epw.py`
- Test: `tests/test_epw_ir_run.py` (append — dry-run/deck-only path, no QE)

**Interfaces:**
- Consumes: `runs.ir`, existing `qe_input` writers, existing `runner` stage functions, `convergence.ConvergenceReport`.
- Produces: CLI `python3 scripts/run_ir_epw.py --spin {none,low,high} --workdir DIR [--deck-only] [--pseudo-dir P --upf U]`. `--deck-only` writes the four decks and exits 0 without invoking any binary (this is what the test exercises).

- [ ] **Step 1: Write the failing test**

```python
def test_driver_deck_only_writes_four_decks(tmp_path):
    from scripts.run_ir_epw import write_decks
    paths = write_decks(spin="high", workdir=str(tmp_path),
                        pseudo_dir="/pseudo", upf="Ir.upf")
    assert set(paths) == {"scf", "nscf", "ph", "epw"}
    scf = (tmp_path / "scf.in").read_text()
    assert "nspin = 2" in scf                     # high-spin -> magnetic deck
    assert "starting_magnetization(1) = 0.3" in scf
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_epw_ir_run.py -k deck_only -v`
Expected: FAIL — `scripts.run_ir_epw` missing.

- [ ] **Step 3: Write minimal implementation**

Implement `write_decks(spin, workdir, pseudo_dir, upf) -> dict[str,str]` that calls `ir_approximant(spin)` + `ir_config(...)` and the existing `scf_input/nscf_input/ph_input/epw_input` writers, writing `scf.in/nscf.in/ph.in/epw.in` with prefix `ir`. Add an `argparse` `main()` that, without `--deck-only`, drives the existing `runner` stages (scf → ph → `collect_dvscf` → nscf → epw), parses λ/Tc, prints a `ConvergenceReport`. Guard the live path so `--deck-only` never imports/invokes a binary.

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_epw_ir_run.py -k deck_only -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add scripts/run_ir_epw.py tests/test_epw_ir_run.py
git commit -m "epw: committed reproducible Ir run driver (deck-only path tested, live path gated)"
```

---

## Task C4: Full suite green + self-review

- [ ] **Step 1:** Run `python3 -m pytest -q` — expect all prior tests + the new Ir tests pass (≥ 187).
- [ ] **Step 2:** `ruff check src/orme_lab/epw/runs src/orme_lab/epw/convergence.py scripts/run_ir_epw.py` — no F-errors.
- [ ] **Step 3:** Commit any fixups. This closes the CODE half; the tree is ready for compute.

---

## Tier 0 (COMPUTE, gated): non-magnetic Ir calibration

**Purpose:** first *d-electron* validation of the pipeline (Pb was s–p), lock the Ir:d+s Wannier recipe, produce a converged non-magnetic λ. Cheap, clean, high-confidence. Deliverable stands regardless of Tiers 1–2.

- [ ] **Provision:** rebuild QE 7.3.1 + EPW 5.8.1 from source (~30–45 min); place SSSP Ir UPF; CONFIRM ecutwfc/ecutrho from the SSSP table and update `ir_config` if they differ from 60/480. Start the monitoring harness (below) BEFORE any heavy stage.
- [ ] **Run:** `python3 scripts/run_ir_epw.py --spin none --workdir <scratch>/ir_none --pseudo-dir <p> --upf Ir.upf` (background; poll).
- [ ] **Tune Wannier windows:** inspect interpolated vs DFT bands near E_F; adjust `dis_win`/`dis_froz` until `wannier_band_max_dev_mev` gate passes (1–3 iterations; re-runs only the cheap EPW stage).
- [ ] **Converge λ:** bump fine grid once; confirm `lambda_grid_delta_frac` gate passes.
- [ ] **GATE 0:** `ConvergenceReport.trustworthy()` is True → record λ_none, Tc_none, and the locked window values in `docs/epw-ir-lambda-run.md`. If not reachable, STOP and report why (this is a real negative — the pipeline does not converge for a d-electron metal at these settings).
- [ ] **Optional external control:** re-run `--spin none` at experimental a=3.839 Å (a labelled one-off, NOT via `ir_config`) to compare λ against literature Ir and quantify the lattice-expansion sensitivity. Clearly marked non-model.

---

## Tier 1 (READING gate, no compute): EPW magnetic-elph capability

**Purpose:** decide whether Tier 2 is even possible. NO fabrication — read the source.

- [ ] Read EPW 5.8.1 source/docs (`EPW/src`, the user guide) for collinear-spin (`nspin=2`) electron–phonon + Wannierization support. Check `epw_readin`/`elphon_shuffle` handling of `nspin==2`, and any explicit "not implemented for spin-polarized" guards.
- [ ] Record the finding verbatim (file:line or doc quote) in `docs/epw-ir-lambda-run.md`.
- [ ] **GATE 1:**
  - **Supported** → proceed to Tier 2.
  - **Not supported / unclear after honest search** → STOP. Report: the high-spin ORME-Ir λ is not obtainable with this toolchain; λ_none (Tier 0) is the ceiling this method reaches; the magnetic ORME claim cannot be evaluated by phonon EPW here. File as the honest negative. This is a legitimate terminal outcome.

---

## Tier 2 (COMPUTE, gated on GATE 1): high-spin ORME Ir

**Purpose:** the decision-relevant number for `H1-open-shell`. Fragile magnetic path; ~2× Tier 0 cost.

- [ ] **Run:** `python3 scripts/run_ir_epw.py --spin high --workdir <scratch>/ir_high ...` with the Tier-0-locked windows (background; poll; monitor especially — magnetic SCF/DFPT is the fragility risk).
- [ ] Watch for: magnetic SCF non-convergence, moment collapsing to ~0 (→ effectively non-magnetic, note it), imaginary phonons (magnetic lattice instability — a real finding, not a failure).
- [ ] **GATE 2:** `trustworthy()` True → record λ_high, Tc_high + full convergence report + honest-caveat block (expanded lattice, no external check, Level 2, woSOC). If a physical instability appears (imaginary modes / moment collapse), that IS the result — report it, don't force a number.

---

## Monitoring harness (runs across all compute tiers)

- [ ] Background a poller: every ~3 min log `uptime` 1-min load, `free -g` available, `df -h` scratch free, and the RSS/state of my `pw.x`/`ph.x`/`epw.x` PIDs. Write to `<scratch>/monitor.log`.
- [ ] Back-off rule (automatic): if free RAM < 15 GB OR free disk < 30 GB OR 1-min load implies operator services are starved (my nice'd jobs not yielding), `kill -STOP` my QE PIDs, drop the next stage to 8 cores, and surface the event. Resume only when headroom returns.
- [ ] NEVER signal a non-QE PID. Operator daemons are identified and excluded by PID before any kill.

---

## Teardown

- [ ] On completion (or terminal gate stop): remove the QE build (`/opt/qe`, ~1.5 GB), purge the apt toolchain packages, delete scratch. Free cores. Confirm only operator services remain (`ps`, load returns to ~baseline).
- [ ] EXCEPTION: if the operator has queued more elements (Pt/Os share the 5d recipe), offer to keep the build warm instead of tearing down.
- [ ] Commit the run log + the one-line pointer in `docs/epw-live-validation.md`.

---

## Self-Review

**Spec coverage:** C1 pins config+spin (finding 1); C1/C3 exercise the magnetic deck (finding 2); Tier 1 resolves the capability question (finding 3); C2/C4 gate on internal convergence since no external check exists (finding 4). Provision/monitor/teardown honour the compute-envelope constraint. Covered.

**Placeholder scan:** ecutwfc/ecutrho carry an explicit CONFIRM-at-provision note (not a silent TODO — the value is usable and the confirmation step is a checklist item). No other placeholders.

**Type consistency:** `ir_approximant(spin: str)` / `ir_config(pseudo_dir, upf)` / `write_decks(spin, workdir, pseudo_dir, upf)` / `ConvergenceReport(...).trustworthy()` are used identically across tasks and tiers.

**Estimated wall-clock:** C1–C4 ≈ 1–2 h. Tier 0 ≈ 0.5–1 day (incl. Wannier tuning). Tier 1 ≈ 1–2 h reading. Tier 2 ≈ 0.5–1 day if GATE 1 passes. Total to a high-spin number: ~1.5–2.5 days; to the honest-negative stop (if GATE 1 fails): ~1 day, having still delivered the Tier 0 non-magnetic λ + locked recipe.
