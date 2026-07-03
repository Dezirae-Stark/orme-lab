# EPW Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `src/orme_lab/epw/` subpackage and wire `Capability.SC_GAP` into the pipeline so a configured `EPWBackend` computes an Allen–Dynes electron–phonon Tc for a periodic approximant of each candidate, reported alongside the unchanged five-gate triage.

**Architecture:** A subpackage of small, pure, unit-tested units (spectral moments, Allen–Dynes Tc, result, approximant, config, QE deck writers, `.a2f` parser) plus one quarantined subprocess `runner.py`. `EPWBackend` (SC_GAP only) composes them behind an injectable runner so the backend→pipeline wiring is testable without QE binaries. The deterministic core is written first, TDD.

**Tech Stack:** Python 3 standard library only (no numpy in the core — trapezoid integration is hand-rolled). `pytest` for tests. Quantum ESPRESSO (`pw.x`, `ph.x`) + EPW (`epw.x`) are external binaries required only for the live runner (skipped in CI).

## Global Constraints

- **Stdlib only** in the core; no third-party imports in `src/orme_lab/epw/*` except within `runner.py` (`subprocess`, `os`, `shutil`, `tempfile` — all stdlib). No numpy.
- **Determinism** guarantee (`pipeline.py` docstring) applies to `backend=None` ONLY. `sc_*` columns are explicitly non-deterministic on the live path. No `time.time()`, no unseeded RNG anywhere.
- **Framing (verbatim, in every module docstring that surfaces the number and the `SC_GAP` docstring):** "Phonon-channel spin-singlet Tc of an imposed periodic reference lattice — NOT a superconductivity estimate for the ORME claim, NOT the finite cluster, NOT any observed phase. A returned Tc is not evidence the material superconducts. Level 2."
- **Evidence cap:** every record's `evidence_level = min(candidate_evidence_level(...), LAB_CEILING)`; no record ever exceeds `LAB_CEILING` (= `SIMULATION_CANDIDATE`, 2), EPW present or absent.
- **Verified physics constants** (Allen–Dynes 1975, secondary-source-confirmed): prefactor `1.20`, exp `1.04`, μ coef `0.62`, `Λ1 = 2.46(1+3.8μ*)`, `Λ2 = 1.82(1+6.3μ*)(ω̄₂/ω_log)`, BCS `1.764`. `μ*` default `0.10`. `k_B = BOLTZMANN/EV_IN_JOULES` eV/K.
- **No silent fallback:** if EPW is asked for and fails, record `sc_source="epw:failed"` with `sc_tc_kelvin=None` — never a toy number in the `sc_*` columns.
- **Commits:** as `Dezirae Stark <deziraestark69@gmail.com>`, no AI-identity trailers.

Spec: `docs/superpowers/specs/2026-07-03-epw-backend-design.md`.

## File Structure

| File | Responsibility |
|---|---|
| `src/orme_lab/epw/__init__.py` | subpackage exports |
| `src/orme_lab/epw/spectral.py` | `EliashbergFunction`: λ, ω_log, ω̄₂ with G-SPEC guards |
| `src/orme_lab/epw/allen_dynes.py` | `allen_dynes_tc`, `bcs_gap_mev` with G-DENOM guard |
| `src/orme_lab/epw/result.py` | `EPWResult` dataclass + constructors |
| `src/orme_lab/epw/approximant.py` | `PeriodicApproximant`, `build_approximant`, `ApproximantUndefined` |
| `src/orme_lab/epw/config.py` | `EPWConfig` dataclass |
| `src/orme_lab/epw/qe_input.py` | scf/nscf/ph/epw deck writers |
| `src/orme_lab/epw/parse.py` | 11-column `.a2f` parser → `EliashbergFunction` |
| `src/orme_lab/epw/runner.py` | `EPWRunner` protocol, `LiveEPWRunner`, `EPWError` |
| `src/orme_lab/backends.py` | widen SC_GAP seam; flesh out `EPWBackend`; `get_backend(**kwargs)` |
| `src/orme_lab/pipeline.py` | consume SC_GAP; new record fields; cap; CSV sentinel |

Tests are flat `tests/test_epw_*.py` (following the existing `tests/test_*.py` convention).

---

### Task 1: Spectral moments (`spectral.py`)

**Files:**
- Create: `src/orme_lab/epw/__init__.py`
- Create: `src/orme_lab/epw/spectral.py`
- Test: `tests/test_epw_spectral.py`

**Interfaces:**
- Consumes: nothing (leaf).
- Produces: `EliashbergFunction(omega: tuple[float,...], a2f: tuple[float,...], omega_min: float = 1e-6, unstable_tol: float = 0.05)` — frozen dataclass with properties `.lam -> float`, `.omega_log -> float`, `.omega_2 -> float`, `.unstable -> bool`, and `.moments() -> tuple[float, float, float]` returning `(lam, omega_log, omega_2)`. Moments are in the same unit as `omega`. A null/empty positive spectrum gives `lam=0.0, omega_log=0.0, omega_2=0.0` (sentinels, never NaN).

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_spectral.py`)

```python
import math
from orme_lab.epw.spectral import EliashbergFunction


def _ef(omega, a2f):
    return EliashbergFunction(omega=tuple(omega), a2f=tuple(a2f))


def test_single_interior_spike_S1():
    ef = _ef([0, 1, 2, 3, 4], [0, 0, 1, 0, 0])   # spike area 1 at w0=2
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 1.0, abs_tol=1e-12)
    assert math.isclose(wlog, 2.0, abs_tol=1e-12)
    assert math.isclose(w2, 2.0, abs_tol=1e-12)


def test_single_interior_spike_S2():
    ef = _ef(list(range(11)), [0, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0])  # spike 2 at w0=5
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 0.8, abs_tol=1e-12)   # 2*P*dw/w0 = 2*2/5
    assert math.isclose(wlog, 5.0, abs_tol=1e-12)
    assert math.isclose(w2, 5.0, abs_tol=1e-12)


def test_two_spike_distinguishes_wlog_from_w2_S3():
    ef = _ef([0, 1, 2, 3, 4, 5], [0, 1, 0, 0, 2, 0])
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 3.0, abs_tol=1e-10)
    assert math.isclose(wlog, 4 ** (1 / 3), abs_tol=1e-10)
    assert math.isclose(w2, math.sqrt(6), abs_tol=1e-10)


def test_omega_zero_and_ln_guards_finite():
    ef = _ef([0, 0.5, 1.0], [0.0, 0.3, 0.0])
    for v in ef.moments():
        assert math.isfinite(v)
    ef2 = _ef([0, 0.5, 1.0], [9.9, 0.3, 0.0])   # nonzero a2f at omega=0 must not poison
    for v in ef2.moments():
        assert math.isfinite(v)


def test_null_spectrum_returns_zero_not_nan():
    ef = _ef([0, 1, 2, 3], [0, 0, 0, 0])
    lam, wlog, w2 = ef.moments()
    assert lam == 0.0 and wlog == 0.0 and w2 == 0.0


def test_unstable_flag_on_negative_frequency_mass():
    stable = _ef([0, 1, 2, 3], [0, 0, 1, 0])
    unstable = _ef([-2, -1, 0, 1, 2], [1.0, 1.0, 0, 0, 0.2])
    assert stable.unstable is False
    assert unstable.unstable is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_spectral.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'orme_lab.epw'`.

- [ ] **Step 3: Create the package init**

`src/orme_lab/epw/__init__.py`:

```python
"""EPW (Quantum ESPRESSO + EPW) electron-phonon Tc backend.

PHONON-CHANNEL, SPIN-SINGLET Tc of an IMPOSED periodic reference lattice --
NOT a superconductivity estimate for the ORME claim, NOT the finite cluster,
NOT any observed phase. A returned Tc is not evidence the material
superconducts. Everything here stays Level 2. See
docs/superpowers/specs/2026-07-03-epw-backend-design.md.
"""
```

- [ ] **Step 4: Implement `spectral.py`**

```python
"""Eliashberg spectral function alpha^2 F(omega) and its moments.

lambda   = 2 * int alpha2F/omega d omega
omega_log = exp[(2/lambda) int (alpha2F/omega) ln omega d omega]
omega_2   = [(2/lambda) int alpha2F * omega d omega]^(1/2)

Moments are returned in the SAME unit as the omega grid. Guards (G-SPEC): the
1/omega factor and 0*ln0 term at omega<=omega_min are skipped; alpha2F is
clipped to >= 0; a null positive spectrum returns (0,0,0), never NaN; negative
(unstable) phonon frequencies set .unstable.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


def _trapz(y: list[float], x: list[float]) -> float:
    total = 0.0
    for i in range(1, len(x)):
        total += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1])
    return total


@dataclass(frozen=True)
class EliashbergFunction:
    omega: tuple[float, ...]
    a2f: tuple[float, ...]
    omega_min: float = 1e-6
    unstable_tol: float = 0.05

    def _positive(self) -> tuple[list[float], list[float]]:
        xs, ys = [], []
        for w, a in zip(self.omega, self.a2f):
            if w > self.omega_min:
                xs.append(w)
                ys.append(max(0.0, a))
        return xs, ys

    @property
    def unstable(self) -> bool:
        neg = _trapz([abs(a) for w, a in zip(self.omega, self.a2f) if w < -self.omega_min],
                     [w for w in self.omega if w < -self.omega_min])
        pos = _trapz([max(0.0, a) for w, a in zip(self.omega, self.a2f) if w > self.omega_min],
                     [w for w in self.omega if w > self.omega_min])
        total = neg + pos
        return total > 0.0 and neg > self.unstable_tol * total

    @property
    def lam(self) -> float:
        xs, ys = self._positive()
        if len(xs) < 2:
            return 0.0
        integrand = [a / w for w, a in zip(xs, ys)]
        return 2.0 * _trapz(integrand, xs)

    @property
    def omega_log(self) -> float:
        lam = self.lam
        if lam <= 0.0:
            return 0.0
        xs, ys = self._positive()
        integrand = [(a / w) * math.log(w) for w, a in zip(xs, ys)]
        return math.exp((2.0 / lam) * _trapz(integrand, xs))

    @property
    def omega_2(self) -> float:
        lam = self.lam
        if lam <= 0.0:
            return 0.0
        xs, ys = self._positive()
        integrand = [a * w for w, a in zip(xs, ys)]
        return math.sqrt((2.0 / lam) * _trapz(integrand, xs))

    def moments(self) -> tuple[float, float, float]:
        return (self.lam, self.omega_log, self.omega_2)
```

- [ ] **Step 5: Run to verify they pass**

Run: `pytest tests/test_epw_spectral.py -q`
Expected: PASS (6 passed).

- [ ] **Step 6: Commit**

```bash
git add src/orme_lab/epw/__init__.py src/orme_lab/epw/spectral.py tests/test_epw_spectral.py
git commit -m "epw: Eliashberg spectral moments (lambda, omega_log, omega_2) with G-SPEC guards"
```

---

### Task 2: Allen–Dynes Tc + BCS gap (`allen_dynes.py`)

**Files:**
- Create: `src/orme_lab/epw/allen_dynes.py`
- Test: `tests/test_epw_allen_dynes.py`

**Interfaces:**
- Consumes: `EliashbergFunction` (for the end-to-end test).
- Produces: `allen_dynes_tc(lam: float, omega_log_k: float, omega_2_k: float, mu_star: float = 0.10) -> float` (Kelvin; 0.0 when `D<=0`, `lam<=0`, or `omega_log<=0`); `bcs_gap_mev(tc_k: float) -> float` (0.0 when `tc<=0`); module constant `MU_STAR_DEFAULT = 0.10`.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_allen_dynes.py`)

```python
import math
import pytest
from orme_lab.epw.allen_dynes import allen_dynes_tc, bcs_gap_mev
from orme_lab.epw.spectral import EliashbergFunction


def test_einstein_golden_A1():
    tc = allen_dynes_tc(1.0, 300.0, 300.0, 0.10)
    assert math.isclose(tc, 21.95067514, rel_tol=1e-6)


def test_mu_star_monotone_A2_A3():
    tcs = [allen_dynes_tc(1.0, 300.0, 300.0, mu) for mu in (0.10, 0.13, 0.16)]
    assert math.isclose(tcs[0], 21.95067514, rel_tol=1e-6)
    assert math.isclose(tcs[1], 18.74239370, rel_tol=1e-6)
    assert math.isclose(tcs[2], 15.69857840, rel_tol=1e-6)
    assert tcs[0] > tcs[1] > tcs[2]


def test_weak_coupling_A4():
    assert math.isclose(allen_dynes_tc(0.5, 400.0, 400.0, 0.10), 4.95218473, rel_tol=1e-6)


def test_strong_coupling_f2_gt_1_A5():
    assert math.isclose(allen_dynes_tc(2.0, 250.0, 300.0, 0.10), 42.67473048, rel_tol=1e-6)


def test_mu_zero_A8():
    assert math.isclose(allen_dynes_tc(1.0, 300.0, 300.0, 0.0), 33.72638610, rel_tol=1e-6)


def test_subcritical_returns_zero_A6_A7():
    assert allen_dynes_tc(0.10, 300.0, 300.0, 0.10) == 0.0
    assert allen_dynes_tc(0.05, 300.0, 300.0, 0.10) == 0.0


def test_just_above_critical_underflow_safe():
    for lam in (0.107, 0.11):
        tc = allen_dynes_tc(lam, 300.0, 300.0, 0.10)
        assert math.isfinite(tc) and 0.0 <= tc < 1e-30


def test_null_inputs_return_zero():
    assert allen_dynes_tc(0.0, 300.0, 300.0, 0.10) == 0.0
    assert allen_dynes_tc(1.0, 0.0, 0.0, 0.10) == 0.0


def test_bcs_gap_linear():
    assert math.isclose(bcs_gap_mev(21.95067514), 3.33672, rel_tol=1e-5)
    assert bcs_gap_mev(0.0) == 0.0


def test_end_to_end_spike_to_tc():
    ef = EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))
    lam, wlog, w2 = ef.moments()
    assert math.isclose(lam, 1.0, abs_tol=1e-9)
    assert math.isclose(wlog, 300.0, abs_tol=1e-9)
    tc = allen_dynes_tc(lam, wlog, w2, 0.10)
    assert math.isclose(tc, 21.95067514, rel_tol=1e-6)
    assert math.isclose(bcs_gap_mev(tc), 3.33672, rel_tol=1e-5)
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_allen_dynes.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'orme_lab.epw.allen_dynes'`.

- [ ] **Step 3: Implement `allen_dynes.py`**

```python
"""McMillan-Allen-Dynes Tc and the BCS weak-coupling gap.

PHONON-CHANNEL, SPIN-SINGLET Tc of an imposed reference lattice -- not a
superconductivity estimate for the ORME claim; a returned Tc is not evidence
the material superconducts. Level 2.

Tc = f1 f2 (omega_log/1.20) exp[-1.04(1+lam)/(lam - mu*(1+0.62 lam))]
  f1 = [1 + (lam/L1)^1.5]^(1/3),        L1 = 2.46(1 + 3.8 mu*)
  f2 = 1 + (w2/wlog - 1) lam^2/(lam^2+L2^2), L2 = 1.82(1 + 6.3 mu*)(w2/wlog)

Constants verified against Allen & Dynes 1975 (Phys. Rev. B 12, 905) via
SECONDARY sources only (primary PRB paywalled) -- see
research-wiki/prior-art/epw-allen-dynes-tc-citation-verification.md.

G-DENOM: D = lam - mu*(1+0.62 lam) changes sign at lam_crit = mu*/(1-0.62 mu*);
below it the raw formula returns a spurious huge Tc, so D<=0 (or lam<=0 or
wlog<=0) returns Tc=0.
"""

from __future__ import annotations

import math

from ..config import BOLTZMANN, EV_IN_JOULES

MU_STAR_DEFAULT = 0.10
_KB_MEV_PER_K = (BOLTZMANN / EV_IN_JOULES) * 1000.0   # 8.617333262e-2 meV/K


def allen_dynes_tc(lam: float, omega_log_k: float, omega_2_k: float,
                   mu_star: float = MU_STAR_DEFAULT) -> float:
    if lam <= 0.0 or omega_log_k <= 0.0:
        return 0.0
    denom = lam - mu_star * (1.0 + 0.62 * lam)
    if denom <= 0.0:                       # G-DENOM: invalid / non-superconducting
        return 0.0
    ratio = (omega_2_k / omega_log_k) if omega_log_k > 0.0 else 1.0
    lam1 = 2.46 * (1.0 + 3.8 * mu_star)
    lam2 = 1.82 * (1.0 + 6.3 * mu_star) * ratio
    f1 = (1.0 + (lam / lam1) ** 1.5) ** (1.0 / 3.0)
    f2 = 1.0 + (ratio - 1.0) * lam * lam / (lam * lam + lam2 * lam2)
    exponent = -1.04 * (1.0 + lam) / denom
    try:
        tc = f1 * f2 * (omega_log_k / 1.20) * math.exp(exponent)
    except OverflowError:                  # extreme exponent -> unphysical, clamp
        return 0.0
    return tc if math.isfinite(tc) else 0.0


def bcs_gap_mev(tc_k: float) -> float:
    if tc_k <= 0.0:
        return 0.0
    return 1.764 * _KB_MEV_PER_K * tc_k
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_allen_dynes.py -q`
Expected: PASS (10 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/allen_dynes.py tests/test_epw_allen_dynes.py
git commit -m "epw: Allen-Dynes Tc + BCS gap with G-DENOM denominator guard"
```

---

### Task 3: Result object (`result.py`)

**Files:**
- Create: `src/orme_lab/epw/result.py`
- Test: `tests/test_epw_result.py`

**Interfaces:**
- Consumes: `EliashbergFunction`, `allen_dynes_tc`, `bcs_gap_mev`.
- Produces: frozen dataclass `EPWResult(tc_kelvin, lam, omega_log_k, omega_2_k, gap_mev, mu_star, source, unstable, provenance)` (all numeric fields `float | None`) with classmethods `toy_absent()`, `not_applicable(reason)`, `failed(reason)`, `from_eliashberg(ef, mu_star, provenance)`. `from_eliashberg` sets `source="epw:unstable"` and `tc_kelvin=None` when `ef.unstable`, else `source="epw"` and fills Tc/gap.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_result.py`)

```python
import math
from orme_lab.epw.result import EPWResult
from orme_lab.epw.spectral import EliashbergFunction


def test_toy_absent_all_none():
    r = EPWResult.toy_absent()
    assert r.source == "toy" and r.tc_kelvin is None and r.gap_mev is None


def test_not_applicable_and_failed():
    assert EPWResult.not_applicable("monomer").source == "n/a"
    assert EPWResult.failed("scf did not converge").source == "epw:failed"


def test_from_eliashberg_stable():
    ef = EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))
    r = EPWResult.from_eliashberg(ef, mu_star=0.10, provenance="fcc-Pb approximant")
    assert r.source == "epw"
    assert math.isclose(r.tc_kelvin, 21.95067514, rel_tol=1e-6)
    assert math.isclose(r.lam, 1.0, abs_tol=1e-9)
    assert r.mu_star == 0.10 and r.unstable is False


def test_from_eliashberg_unstable_gives_none_tc():
    ef = EliashbergFunction(omega=(-2, -1, 0, 1, 2), a2f=(1.0, 1.0, 0, 0, 0.2))
    r = EPWResult.from_eliashberg(ef, mu_star=0.10, provenance="unstable")
    assert r.source == "epw:unstable" and r.tc_kelvin is None and r.unstable is True
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_result.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `result.py`**

```python
"""EPWResult -- the value the SC_GAP seam returns.

Numeric fields are None when EPW did not produce a Tc (toy/absent, not
applicable, failed, or dynamically unstable). `source` is always present.
"""

from __future__ import annotations

from dataclasses import dataclass

from .allen_dynes import allen_dynes_tc, bcs_gap_mev
from .spectral import EliashbergFunction


@dataclass(frozen=True)
class EPWResult:
    tc_kelvin: float | None
    lam: float | None
    omega_log_k: float | None
    omega_2_k: float | None
    gap_mev: float | None
    mu_star: float | None
    source: str
    unstable: bool = False
    provenance: str = ""

    @classmethod
    def toy_absent(cls) -> "EPWResult":
        return cls(None, None, None, None, None, None, "toy", False, "")

    @classmethod
    def not_applicable(cls, reason: str) -> "EPWResult":
        return cls(None, None, None, None, None, None, "n/a", False, reason)

    @classmethod
    def failed(cls, reason: str) -> "EPWResult":
        return cls(None, None, None, None, None, None, "epw:failed", False, reason)

    @classmethod
    def from_eliashberg(cls, ef: EliashbergFunction, mu_star: float,
                        provenance: str) -> "EPWResult":
        lam, wlog, w2 = ef.moments()
        if ef.unstable:
            return cls(None, lam, wlog, w2, None, mu_star, "epw:unstable", True, provenance)
        tc = allen_dynes_tc(lam, wlog, w2, mu_star)
        gap = bcs_gap_mev(tc)
        return cls(tc, lam, wlog, w2, gap, mu_star, "epw", False, provenance)
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_result.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/result.py tests/test_epw_result.py
git commit -m "epw: EPWResult with toy/n-a/failed/unstable/from_eliashberg constructors"
```

---

### Task 4: Periodic approximant (`approximant.py`)

**Files:**
- Create: `src/orme_lab/epw/approximant.py`
- Test: `tests/test_epw_approximant.py`

**Interfaces:**
- Consumes: `Element`, `ClusterGeometry`, `SpinState` (from the package).
- Produces: `ApproximantUndefined(Exception)`; frozen dataclass `PeriodicApproximant(element_symbol, bravais, a_angstrom, c_over_a, spin_polarized, starting_magnetization, label)` with properties `.ibrav -> int` (2 fcc, 4 hcp) and `.a_bohr -> float`; `build_approximant(element, geometry, spin_state) -> PeriodicApproximant` raising `ApproximantUndefined` when `geometry.nearest_neighbor_distance` is not finite (monomer). fcc for all screen elements except `{Os, Ru}` (hcp). fcc `a = d*sqrt(2)`, hcp `a = d`, `c/a = 1.6329931619`. `starting_magnetization = min(1.0, unpaired/10)`; `spin_polarized = unpaired > 0`.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_approximant.py`)

```python
import math
import pytest
from orme_lab.elements import get_element
from orme_lab.geometry import make_monomer, make_compact_cluster
from orme_lab.spin_states import high_spin_state, low_spin_state
from orme_lab.epw.approximant import build_approximant, ApproximantUndefined


def test_monomer_raises_approximant_undefined():
    au = get_element("Au")
    with pytest.raises(ApproximantUndefined):
        build_approximant(au, make_monomer(au), high_spin_state(au))


def test_fcc_element_lattice_constant_from_nn():
    au = get_element("Au")
    geom = make_compact_cluster(au, 13)
    d = geom.nearest_neighbor_distance
    ap = build_approximant(au, geom, high_spin_state(au))
    assert ap.bravais == "fcc" and ap.ibrav == 2
    assert math.isclose(ap.a_angstrom, d * math.sqrt(2), rel_tol=1e-9)
    assert ap.c_over_a is None


def test_hcp_element_uses_ideal_c_over_a():
    os_el = get_element("Os")
    geom = make_compact_cluster(os_el, 13)
    ap = build_approximant(os_el, geom, high_spin_state(os_el))
    assert ap.bravais == "hcp" and ap.ibrav == 4
    assert math.isclose(ap.c_over_a, 1.6329931619, rel_tol=1e-9)


def test_high_spin_is_polarized_low_spin_is_not():
    os_el = get_element("Os")
    geom = make_compact_cluster(os_el, 13)
    hi = build_approximant(os_el, geom, high_spin_state(os_el))
    lo = build_approximant(os_el, geom, low_spin_state(os_el))
    assert hi.spin_polarized is True and hi.starting_magnetization > 0.0
    assert lo.spin_polarized is (low_spin_state(os_el).unpaired_electrons > 0)
    assert 0.0 <= hi.starting_magnetization <= 1.0
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_approximant.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `approximant.py`**

```python
"""Build the periodic reference lattice EPW runs on.

COUNTERFACTUAL: an imposed close-packed crystal inferred from the cluster's
single nearest-neighbour distance and forced into the high-spin state. NOT the
ORME motif, NOT the finite cluster, NOT any observed phase. The NN->crystal map
is under-determined (fcc/hcp, c/a are conventions); see the spec's O2. Level 2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from ..elements import Element
from ..geometry import ClusterGeometry
from ..spin_states import SpinState

ANGSTROM_TO_BOHR = 1.8897259886
IDEAL_C_OVER_A = 1.6329931619          # sqrt(8/3)
_HCP = frozenset({"Os", "Ru"})         # ambient hcp; everything else in the screen is fcc


class ApproximantUndefined(Exception):
    """Raised when a geometry has no well-defined nearest-neighbour distance
    (e.g. a monomer), so no periodic approximant can be built."""


@dataclass(frozen=True)
class PeriodicApproximant:
    element_symbol: str
    bravais: str            # "fcc" | "hcp"
    a_angstrom: float
    c_over_a: float | None  # None for fcc
    spin_polarized: bool
    starting_magnetization: float
    label: str

    @property
    def ibrav(self) -> int:
        return 2 if self.bravais == "fcc" else 4

    @property
    def a_bohr(self) -> float:
        return self.a_angstrom * ANGSTROM_TO_BOHR


def build_approximant(element: Element, geometry: ClusterGeometry,
                      spin_state: SpinState) -> PeriodicApproximant:
    d = geometry.nearest_neighbor_distance
    if not math.isfinite(d):
        raise ApproximantUndefined(
            f"{element.symbol}/{geometry.label or 'geometry'} has no finite "
            f"nearest-neighbour distance (n_atoms={geometry.n_atoms}); "
            f"no periodic approximant is defined."
        )
    hcp = element.symbol in _HCP
    bravais = "hcp" if hcp else "fcc"
    a = d if hcp else d * math.sqrt(2.0)          # fcc nn = a/sqrt(2)
    c_over_a = IDEAL_C_OVER_A if hcp else None
    unpaired = spin_state.unpaired_electrons
    return PeriodicApproximant(
        element_symbol=element.symbol,
        bravais=bravais,
        a_angstrom=a,
        c_over_a=c_over_a,
        spin_polarized=unpaired > 0,
        starting_magnetization=min(1.0, unpaired / 10.0),
        label=f"{element.symbol}-{bravais}-{geometry.label or 'cluster'}",
    )
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_approximant.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/approximant.py tests/test_epw_approximant.py
git commit -m "epw: periodic approximant builder (fcc/hcp from nn-distance; ApproximantUndefined for monomer)"
```

---

### Task 5: EPW config (`config.py`)

**Files:**
- Create: `src/orme_lab/epw/config.py`
- Test: `tests/test_epw_config.py`

**Interfaces:**
- Consumes: nothing.
- Produces: frozen dataclass `EPWConfig` with fields `mu_star=0.10`, `ecutwfc_ry=60.0`, `ecutrho_ry=480.0`, `k_coarse=(8,8,8)`, `q_coarse=(4,4,4)`, `k_fine=(20,20,20)`, `q_fine=(20,20,20)`, `smearing_column=5`, `omega_min_k=1.0`, `unstable_tol=0.05`, `pseudo_dir=""`, `pseudopotentials: tuple[tuple[str,str],...]=()`, `pw_x="pw.x"`, `ph_x="ph.x"`, `epw_x="epw.x"`, `scratch_root="/tmp/orme-epw"`, `timeout_s=86400`; methods `resolved_pseudo_dir() -> str` (falls back to `$ESPRESSO_PSEUDO`), `pseudo_for(symbol) -> str | None`.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_config.py`)

```python
import os
from orme_lab.epw.config import EPWConfig


def test_defaults():
    c = EPWConfig()
    assert c.mu_star == 0.10 and c.smearing_column == 5 and c.epw_x == "epw.x"


def test_pseudo_for_lookup():
    c = EPWConfig(pseudopotentials=(("Os", "Os.upf"), ("Au", "Au.upf")))
    assert c.pseudo_for("Au") == "Au.upf"
    assert c.pseudo_for("Pt") is None


def test_resolved_pseudo_dir_env_fallback(monkeypatch):
    monkeypatch.setenv("ESPRESSO_PSEUDO", "/opt/pseudo")
    assert EPWConfig().resolved_pseudo_dir() == "/opt/pseudo"
    assert EPWConfig(pseudo_dir="/explicit").resolved_pseudo_dir() == "/explicit"
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_config.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `config.py`**

```python
"""EPWConfig -- deterministic parameters for the EPW backend.

Owned by EPWBackend at construction (kept out of LabConfig). All meshes/cutoffs
are pinned so a run is reproducible up to the external solver's own
MPI/BLAS-level nondeterminism (see the spec's O5 -- sc_* columns are not
byte-reproducible).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass(frozen=True)
class EPWConfig:
    mu_star: float = 0.10
    ecutwfc_ry: float = 60.0
    ecutrho_ry: float = 480.0
    k_coarse: tuple[int, int, int] = (8, 8, 8)
    q_coarse: tuple[int, int, int] = (4, 4, 4)
    k_fine: tuple[int, int, int] = (20, 20, 20)
    q_fine: tuple[int, int, int] = (20, 20, 20)
    smearing_column: int = 5          # 1..10 -> which degaussq column of the .a2f
    omega_min_k: float = 1.0
    unstable_tol: float = 0.05
    pseudo_dir: str = ""
    pseudopotentials: tuple[tuple[str, str], ...] = ()
    pw_x: str = "pw.x"
    ph_x: str = "ph.x"
    epw_x: str = "epw.x"
    scratch_root: str = "/tmp/orme-epw"
    timeout_s: int = 86400

    def resolved_pseudo_dir(self) -> str:
        return self.pseudo_dir or os.environ.get("ESPRESSO_PSEUDO", "")

    def pseudo_for(self, symbol: str) -> str | None:
        for sym, upf in self.pseudopotentials:
            if sym == symbol:
                return upf
        return None
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_config.py -q`
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/config.py tests/test_epw_config.py
git commit -m "epw: EPWConfig (pinned meshes/cutoffs, pseudo lookup, binary paths)"
```

---

### Task 6: `.a2f` parser (`parse.py`)

**Files:**
- Create: `src/orme_lab/epw/parse.py`
- Create: `tests/fixtures/sample.a2f`
- Test: `tests/test_epw_parse.py`

**Interfaces:**
- Consumes: `EliashbergFunction`.
- Produces: `parse_a2f(text: str, column: int = 5) -> EliashbergFunction`. Reads the 11-column raw EPW `.a2f` (col 1 = ω in meV, cols 2-11 = α²F at 10 degaussq smearings); selects the given 1-based smearing column; **converts ω from meV to Kelvin** (`* 11.604518`) so the returned grid is in Kelvin. Skips blank/comment (`#`, `lambda`) lines and any row without ≥ `column+1` numeric fields. `MEV_TO_KELVIN = 11.604518`.

- [ ] **Step 1: Create the fixture** (`tests/fixtures/sample.a2f`)

A minimal 11-column file with a single spike at ω=25.85 meV (= 300.0 K) of height 1.0 in every smearing column, so column 5 yields λ=2·(1·dw)/ω... use a lone interior spike so the moment identities hold. Grid step chosen so the spike integrates to λ where `allen_dynes` gives the golden Tc is not required here; this test only checks parsing shape and unit conversion.

```
# Eliashberg spectral function a2F, 11 columns: omega(meV) then 10 degaussq smearings
    0.000000   0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
   12.925000   0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
   25.850000   1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0 1.0
   38.775000   0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
   51.700000   0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0 0.0
lambda : 0.7736
```

- [ ] **Step 2: Write the failing tests** (`tests/test_epw_parse.py`)

```python
import math
from pathlib import Path
from orme_lab.epw.parse import parse_a2f, MEV_TO_KELVIN
from orme_lab.epw.spectral import EliashbergFunction

FIX = Path(__file__).parent / "fixtures" / "sample.a2f"


def test_parses_11_columns_and_converts_to_kelvin():
    ef = parse_a2f(FIX.read_text(), column=5)
    assert isinstance(ef, EliashbergFunction)
    assert len(ef.omega) == 5
    # 25.850 meV -> ~300 K; spike position is the third grid point
    assert math.isclose(ef.omega[2], 25.850 * MEV_TO_KELVIN, rel_tol=1e-6)
    assert ef.a2f[2] == 1.0 and ef.a2f[0] == 0.0


def test_skips_comment_and_lambda_lines():
    ef = parse_a2f(FIX.read_text(), column=5)
    # 'lambda : 0.7736' and the '#' header must not become data rows
    assert all(math.isfinite(w) for w in ef.omega)


def test_column_selection_out_of_range_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_a2f(FIX.read_text(), column=11)   # only 10 smearing columns (2..11 -> 1..10)
```

- [ ] **Step 3: Run to verify they fail**

Run: `pytest tests/test_epw_parse.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 4: Implement `parse.py`**

```python
"""Parse the raw EPW PREFIX.a2f file into an EliashbergFunction.

The raw file is 11 columns: column 1 is omega in meV, columns 2-11 are
alpha^2F(omega) at 10 phonon-smearing (degaussq) values. We select one smearing
column and convert omega from meV to Kelvin so the moments come out in Kelvin.

Column semantics come from EPW docs/forum and MUST be re-verified against the
installed EPW version's a2f.f90 (format can change across releases) -- G-A2F.
"""

from __future__ import annotations

from .spectral import EliashbergFunction

MEV_TO_KELVIN = 11.604518          # 1 meV in Kelvin (1/k_B)
_N_SMEARING = 10                   # columns 2..11


def parse_a2f(text: str, column: int = 5) -> EliashbergFunction:
    if not (1 <= column <= _N_SMEARING):
        raise ValueError(f"smearing column {column} out of range 1..{_N_SMEARING}")
    omega: list[float] = []
    a2f: list[float] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.lower().startswith("lambda"):
            continue
        parts = s.split()
        if len(parts) < 1 + _N_SMEARING:
            continue
        try:
            w_mev = float(parts[0])
            val = float(parts[column])          # parts[1] is smearing col 1
        except ValueError:
            continue
        omega.append(w_mev * MEV_TO_KELVIN)
        a2f.append(val)
    return EliashbergFunction(omega=tuple(omega), a2f=tuple(a2f))
```

- [ ] **Step 5: Run to verify they pass**

Run: `pytest tests/test_epw_parse.py -q`
Expected: PASS (3 passed).

- [ ] **Step 6: Commit**

```bash
git add src/orme_lab/epw/parse.py tests/test_epw_parse.py tests/fixtures/sample.a2f
git commit -m "epw: 11-column .a2f parser with meV->K conversion (G-A2F)"
```

---

### Task 7: Runner (`runner.py`)

**Files:**
- Create: `src/orme_lab/epw/runner.py`
- Test: `tests/test_epw_runner.py`

**Interfaces:**
- Consumes: `PeriodicApproximant`, `EPWConfig`, `qe_input` writers (Task 8 provides them; this task references them by name — see note).
- Produces: `EPWError(Exception)`; `EPWRunner` (typing Protocol) with `run(approx, cfg) -> str` (returns raw `.a2f` text or raises `EPWError`); `scratch_name(approx) -> str` (deterministic, from element+label); `assert_stage_complete(stdout: str, *, require_convergence: bool) -> None` (raises `EPWError` unless `JOB DONE` present, and — when required — `convergence has been achieved`); `LiveEPWRunner` implementing the protocol via subprocess (skipped in CI).

> **Note on ordering:** `LiveEPWRunner.run` calls the Task 8 deck writers. Implement the pure helpers (`scratch_name`, `assert_stage_complete`, `EPWError`, the `EPWRunner` protocol) and their tests in this task; the `LiveEPWRunner.run` body may import `qe_input` lazily inside the method so Task 7's tests pass before Task 8 exists.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_runner.py`)

```python
import pytest
from orme_lab.epw.runner import scratch_name, assert_stage_complete, EPWError
from orme_lab.epw.approximant import PeriodicApproximant


def _approx(label):
    return PeriodicApproximant("Os", "hcp", 2.7, 1.6329931619, True, 0.4, label)


def test_scratch_name_is_deterministic_and_distinct():
    a = scratch_name(_approx("Os-hcp-compact13"))
    b = scratch_name(_approx("Os-hcp-compact13"))
    c = scratch_name(_approx("Os-hcp-compact6"))
    assert a == b and a != c
    assert " " not in a and "/" not in a


def test_assert_stage_complete_accepts_job_done():
    assert_stage_complete("... JOB DONE ...", require_convergence=False)


def test_assert_stage_complete_rejects_missing_job_done():
    with pytest.raises(EPWError):
        assert_stage_complete("stopped early", require_convergence=False)


def test_assert_stage_complete_requires_convergence_when_asked():
    with pytest.raises(EPWError):
        assert_stage_complete("JOB DONE", require_convergence=True)  # no convergence line
    assert_stage_complete("convergence has been achieved\nJOB DONE", require_convergence=True)


def test_assert_stage_complete_rejects_crash_marker():
    with pytest.raises(EPWError):
        assert_stage_complete("JOB DONE\n %%%% CRASH %%%%", require_convergence=False)
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_runner.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `runner.py`**

```python
"""Subprocess orchestration for a live EPW run (pw -> ph -> nscf -> epw).

The pure helpers (deterministic scratch naming, positive completion
validation) are unit-tested. LiveEPWRunner.run needs the QE+EPW binaries and is
exercised only when they are present. Failures raise EPWError; the backend maps
them to EPWResult.failed so one candidate's failure never aborts a screen.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from typing import Protocol

from .approximant import PeriodicApproximant
from .config import EPWConfig


class EPWError(Exception):
    """A live EPW run failed (missing binary/pseudo, non-convergence, crash,
    timeout, or truncated output)."""


class EPWRunner(Protocol):
    def run(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        """Run the pipeline and return the raw PREFIX.a2f text, or raise EPWError."""
        ...


def scratch_name(approx: PeriodicApproximant) -> str:
    """Deterministic, filesystem-safe prefix keyed on the approximant identity
    (no wall-clock, no PID) so a screen's run directories are reproducible and
    never collide across candidates."""
    digest = hashlib.sha1(approx.label.encode("utf-8")).hexdigest()[:10]
    return f"orme_{approx.element_symbol}_{approx.bravais}_{digest}"


def assert_stage_complete(stdout: str, *, require_convergence: bool) -> None:
    """Fail closed unless the stage positively reports completion (QE exits 0 on
    soft failures, so returncode is not enough) -- G-COMPLETE."""
    if "CRASH" in stdout:
        raise EPWError("QE stage wrote a CRASH marker")
    if "JOB DONE" not in stdout:
        raise EPWError("QE stage did not reach 'JOB DONE' (truncated/killed run)")
    if require_convergence and "convergence has been achieved" not in stdout:
        raise EPWError("SCF did not report 'convergence has been achieved'")


class LiveEPWRunner:
    """Real subprocess runner. available() gates on the three binaries; run()
    drives scf/ph/nscf/epw in a fresh per-candidate scratch dir under a new
    process group (so a timeout kills the whole MPI tree) and validates each
    stage positively before parsing."""

    @staticmethod
    def available(cfg: EPWConfig) -> bool:
        return all(shutil.which(b) for b in (cfg.pw_x, cfg.ph_x, cfg.epw_x))

    def run(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        from . import qe_input   # lazy import: Task 8

        if not self.available(cfg):
            raise EPWError("pw.x/ph.x/epw.x not all on PATH")
        prefix = scratch_name(approx)
        workdir = os.path.join(cfg.scratch_root, prefix)
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        def _run(binary: str, deck: str, *, converge: bool) -> str:
            proc = subprocess.run(
                [binary], input=deck, cwd=workdir, text=True,
                capture_output=True, timeout=cfg.timeout_s, start_new_session=True,
            )
            assert_stage_complete(proc.stdout, require_convergence=converge)
            return proc.stdout

        _run(cfg.pw_x, qe_input.scf_input(approx, cfg), converge=True)
        _run(cfg.ph_x, qe_input.ph_input(approx, cfg, prefix), converge=False)
        _run(cfg.pw_x, qe_input.nscf_input(approx, cfg), converge=True)
        _run(cfg.epw_x, qe_input.epw_input(approx, cfg, prefix), converge=False)

        a2f_path = os.path.join(workdir, f"{prefix}.a2f")
        if not os.path.exists(a2f_path):
            raise EPWError(f"EPW produced no .a2f at {a2f_path}")
        return open(a2f_path, encoding="utf-8").read()
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_runner.py -q`
Expected: PASS (5 passed). (`LiveEPWRunner.run` is not exercised here.)

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/runner.py tests/test_epw_runner.py
git commit -m "epw: runner protocol + deterministic scratch + positive completion validation (G-COMPLETE/SCRATCH/KILL)"
```

---

### Task 8: QE deck writers (`qe_input.py`)

**Files:**
- Create: `src/orme_lab/epw/qe_input.py`
- Test: `tests/test_epw_qe_input.py`

**Interfaces:**
- Consumes: `PeriodicApproximant`, `EPWConfig`.
- Produces: `scf_input(approx, cfg) -> str`, `nscf_input(approx, cfg) -> str`, `ph_input(approx, cfg, prefix) -> str`, `epw_input(approx, cfg, prefix) -> str`. Each returns a valid QE/EPW input deck as text. `nspin=2` + `starting_magnetization` when `approx.spin_polarized`.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_qe_input.py`)

```python
from orme_lab.epw.qe_input import scf_input, ph_input, epw_input
from orme_lab.epw.config import EPWConfig
from orme_lab.epw.approximant import PeriodicApproximant


def _cfg():
    return EPWConfig(pseudopotentials=(("Os", "Os.upf"),))


def _fcc():
    return PeriodicApproximant("Au", "fcc", 4.0, None, False, 0.0, "Au-fcc-compact13")


def _hcp_polarized():
    return PeriodicApproximant("Os", "hcp", 2.7, 1.6329931619, True, 0.4, "Os-hcp-compact13")


def test_scf_has_required_namelists_and_ibrav():
    deck = scf_input(_fcc(), _cfg())
    assert "&control" in deck and "&system" in deck and "&electrons" in deck
    assert "ibrav = 2" in deck
    assert "calculation = 'scf'" in deck


def test_spin_polarized_sets_nspin_and_magnetization():
    deck = scf_input(_hcp_polarized(), _cfg())
    assert "nspin = 2" in deck
    assert "starting_magnetization(1) = 0.4" in deck
    assert "ibrav = 4" in deck and "celldm(3)" in deck


def test_non_polarized_omits_nspin():
    deck = scf_input(_fcc(), _cfg())
    assert "nspin" not in deck


def test_ph_and_epw_reference_prefix_and_meshes():
    ph = ph_input(_hcp_polarized(), _cfg(), "orme_Os")
    assert "orme_Os" in ph and "4 4 4" in ph          # q_coarse
    epw = epw_input(_hcp_polarized(), _cfg(), "orme_Os")
    assert "orme_Os" in epw and "nkf1" in epw and "a2f" in epw.lower()
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_qe_input.py -q`
Expected: FAIL with `ModuleNotFoundError`.

- [ ] **Step 3: Implement `qe_input.py`**

```python
"""Quantum ESPRESSO + EPW input-deck writers for the approximant.

Deterministic text generation only -- no binaries touched. Decks pin every
cutoff/mesh from EPWConfig. spin_polarized approximants get nspin=2 +
starting_magnetization.
"""

from __future__ import annotations

from .approximant import PeriodicApproximant
from .config import EPWConfig


def _cell(approx: PeriodicApproximant) -> str:
    lines = [f"    ibrav = {approx.ibrav}", f"    celldm(1) = {approx.a_bohr:.8f}"]
    if approx.c_over_a is not None:
        lines.append(f"    celldm(3) = {approx.c_over_a:.8f}")
    return "\n".join(lines)


def _system(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    lines = [
        "&system",
        _cell(approx),
        "    nat = 1",
        "    ntyp = 1",
        f"    ecutwfc = {cfg.ecutwfc_ry}",
        f"    ecutrho = {cfg.ecutrho_ry}",
        "    occupations = 'smearing'",
        "    smearing = 'mp'",
        "    degauss = 0.02",
    ]
    if approx.spin_polarized:
        lines.append("    nspin = 2")
        lines.append(f"    starting_magnetization(1) = {approx.starting_magnetization}")
    lines.append("/")
    return "\n".join(lines)


def _atomic_blocks(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    upf = cfg.pseudo_for(approx.element_symbol) or f"{approx.element_symbol}.upf"
    return (
        "ATOMIC_SPECIES\n"
        f" {approx.element_symbol} 1.0 {upf}\n"
        "ATOMIC_POSITIONS crystal\n"
        f" {approx.element_symbol} 0.0 0.0 0.0\n"
    )


def _pw(approx: PeriodicApproximant, cfg: EPWConfig, calc: str,
        kmesh: tuple[int, int, int]) -> str:
    pd = cfg.resolved_pseudo_dir()
    kx, ky, kz = kmesh
    return (
        "&control\n"
        f"    calculation = '{calc}'\n"
        f"    prefix = 'orme'\n"
        f"    pseudo_dir = '{pd}'\n"
        "    outdir = './'\n"
        "/\n"
        f"{_system(approx, cfg)}\n"
        "&electrons\n"
        "    conv_thr = 1.0d-10\n"
        "/\n"
        f"{_atomic_blocks(approx, cfg)}"
        f"K_POINTS automatic\n {kx} {ky} {kz} 0 0 0\n"
    )


def scf_input(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    return _pw(approx, cfg, "scf", cfg.k_coarse)


def nscf_input(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    return _pw(approx, cfg, "nscf", cfg.k_fine)


def ph_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    qx, qy, qz = cfg.q_coarse
    return (
        f"phonons for {prefix}\n"
        "&inputph\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        "    fildyn = 'dyn'\n"
        "    ldisp = .true.\n"
        f"    nq1 = {qx}\n    nq2 = {qy}\n    nq3 = {qz}\n"
        f"    ! q_coarse = {qx} {qy} {qz}\n"
        "/\n"
    )


def epw_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    kf = cfg.k_fine
    qf = cfg.q_fine
    kc = cfg.k_coarse
    qc = cfg.q_coarse
    return (
        "&inputepw\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        "    elph = .true.\n"
        "    epwwrite = .true.\n"
        "    a2f = .true.\n"
        f"    nkf1 = {kf[0]}\n    nkf2 = {kf[1]}\n    nkf3 = {kf[2]}\n"
        f"    nqf1 = {qf[0]}\n    nqf2 = {qf[1]}\n    nqf3 = {qf[2]}\n"
        f"    nk1 = {kc[0]}\n    nk2 = {kc[1]}\n    nk3 = {kc[2]}\n"
        f"    nq1 = {qc[0]}\n    nq2 = {qc[1]}\n    nq3 = {qc[2]}\n"
        "/\n"
    )
```

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_qe_input.py -q`
Expected: PASS (4 passed).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/epw/qe_input.py tests/test_epw_qe_input.py
git commit -m "epw: QE/EPW deck writers (scf/nscf/ph/epw; nspin+magnetization when polarized)"
```

---

### Task 9: `EPWBackend` + widen the SC_GAP seam (`backends.py`)

**Files:**
- Modify: `src/orme_lab/backends.py`
- Test: `tests/test_epw_backend.py`

**Interfaces:**
- Consumes: `build_approximant`/`ApproximantUndefined`, `EPWConfig`, `EPWRunner`/`LiveEPWRunner`/`EPWError`, `parse_a2f`, `EliashbergFunction`, `EPWResult`.
- Produces: `DFTBackend.superconducting_gap(self, element, geometry, spin_state) -> EPWResult` (base raises `_nyi`); `EPWBackend(config: EPWConfig | None = None, runner: EPWRunner | None = None)` implementing `@implemented(Capability.SC_GAP)` and providing **only** SC_GAP; `binary_requires = ("pw.x", "ph.x", "epw.x")`; `get_backend(name, **kwargs)` forwarding kwargs.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_backend.py`)

```python
import math
from orme_lab.backends import Capability, get_backend, EPWBackend
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster, make_monomer
from orme_lab.spin_states import high_spin_state
from orme_lab.epw.spectral import EliashbergFunction
from orme_lab.epw.config import EPWConfig


class FakeRunner:
    """Returns a canned .a2f-equivalent spectrum (bypasses binaries)."""
    def __init__(self, ef):
        self._ef = ef
    def run(self, approx, cfg):
        return self._ef


class FakeRunnerText:
    def run(self, approx, cfg):   # emulate a raw-text runner path
        raise AssertionError("not used")


def _spike_ef():
    return EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))


def test_epw_backend_provides_only_sc_gap():
    b = EPWBackend()
    assert b.provides(Capability.SC_GAP) is True
    assert b.provides(Capability.INTER_UNIT_COUPLING) is False
    assert b.capabilities() == frozenset({Capability.SC_GAP})


def test_superconducting_gap_computes_tc_via_injected_runner():
    b = EPWBackend(runner=FakeRunner(_spike_ef()))
    au = get_element("Au")
    r = b.superconducting_gap(au, make_compact_cluster(au, 13), high_spin_state(au))
    assert r.source == "epw"
    assert math.isclose(r.tc_kelvin, 21.95067514, rel_tol=1e-6)


def test_monomer_returns_not_applicable():
    b = EPWBackend(runner=FakeRunner(_spike_ef()))
    au = get_element("Au")
    r = b.superconducting_gap(au, make_monomer(au), high_spin_state(au))
    assert r.source == "n/a" and r.tc_kelvin is None


def test_runner_failure_returns_failed_not_raise():
    class Boom:
        def run(self, approx, cfg):
            from orme_lab.epw.runner import EPWError
            raise EPWError("scf blew up")
    b = EPWBackend(runner=Boom())
    au = get_element("Au")
    r = b.superconducting_gap(au, make_compact_cluster(au, 13), high_spin_state(au))
    assert r.source == "epw:failed" and r.tc_kelvin is None


def test_get_backend_forwards_runner_kwarg():
    b = get_backend("epw", runner=FakeRunner(_spike_ef()))
    assert isinstance(b, EPWBackend)
```

> The injected runner returns an `EliashbergFunction` directly; the backend must accept either a raw `.a2f` string (parsed via `parse_a2f`) or an already-parsed `EliashbergFunction`. See the implementation note in Step 3.

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_backend.py -q`
Expected: FAIL (base `superconducting_gap` signature is `(coupling, carrier_proxy)`; `EPWBackend` has no impl; `get_backend` takes no kwargs).

- [ ] **Step 3: Modify `backends.py`**

Widen the abstract seam (find the existing `superconducting_gap`):

```python
    def superconducting_gap(self, element: "Element", geometry: "ClusterGeometry",
                            spin_state: "SpinState") -> "EPWResult":
        """Electron-phonon Eliashberg Tc for a periodic approximant of the
        candidate (Capability.SC_GAP). PHONON-CHANNEL, SPIN-SINGLET Tc of an
        IMPOSED reference lattice -- NOT a superconductivity estimate for the
        ORME claim; a returned Tc is not evidence the material superconducts.
        Level 2."""
        self._nyi(Capability.SC_GAP)
```

Replace the `EPWBackend` stub with the implementation:

```python
class EPWBackend(DFTBackend):
    name = "epw"
    description = "EPW -- ab-initio electron-phonon / Eliashberg Tc (with Quantum ESPRESSO)"
    declared_capabilities = frozenset({Capability.SC_GAP})   # G-CAP: NOT INTER_UNIT_COUPLING
    binary_requires = ("pw.x", "ph.x", "epw.x")              # G-GATE: all three

    def __init__(self, config=None, runner=None):
        from .epw.config import EPWConfig
        from .epw.runner import LiveEPWRunner
        self.config = config or EPWConfig()
        self.runner = runner or LiveEPWRunner()

    @implemented(Capability.SC_GAP)
    def superconducting_gap(self, element, geometry, spin_state):
        from .epw.approximant import build_approximant, ApproximantUndefined
        from .epw.parse import parse_a2f
        from .epw.result import EPWResult
        from .epw.runner import EPWError
        from .epw.spectral import EliashbergFunction

        try:
            approx = build_approximant(element, geometry, spin_state)
        except ApproximantUndefined as exc:
            return EPWResult.not_applicable(str(exc))
        try:
            raw = self.runner.run(approx, self.config)
        except EPWError as exc:
            return EPWResult.failed(str(exc))
        ef = raw if isinstance(raw, EliashbergFunction) else parse_a2f(raw, self.config.smearing_column)
        return EPWResult.from_eliashberg(ef, self.config.mu_star, approx.label)
```

Update `get_backend` to forward kwargs:

```python
def get_backend(name: str, **kwargs) -> DFTBackend:
    try:
        return BACKENDS[name](**kwargs)
    except KeyError as exc:  # pragma: no cover - defensive
        known = ", ".join(sorted(BACKENDS))
        raise KeyError(f"Unknown backend {name!r}. Known: {known}") from exc
```

Add `SpinState` to the `TYPE_CHECKING` import block and `EPWResult` under `TYPE_CHECKING` for the annotation.

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_backend.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite (nothing else regressed)**

Run: `pytest -q`
Expected: PASS (all prior 43 + the new EPW tests).

- [ ] **Step 6: Commit**

```bash
git add src/orme_lab/backends.py tests/test_epw_backend.py
git commit -m "epw: EPWBackend (SC_GAP only, injectable runner) + widen the SC_GAP seam (G-CAP/GATE/LSP/DI)"
```

---

### Task 10: Pipeline + record wiring (`pipeline.py`)

**Files:**
- Modify: `src/orme_lab/pipeline.py`
- Test: `tests/test_epw_pipeline.py`

**Interfaces:**
- Consumes: `EPWBackend`, `Capability`, `EPWResult`, `LAB_CEILING`.
- Produces: `CandidateRecord` gains `sc_tc_kelvin/sc_lambda/sc_omega_log_k/sc_gap_mev/sc_mu_star: float | None = None` and `sc_source: str = "toy"`; `evaluate_candidate` consumes `SC_GAP` gated on `provides ∧ available` with a per-candidate try/except; `evidence_level = min(candidate_evidence_level(...), LAB_CEILING)`.

- [ ] **Step 1: Write the failing tests** (`tests/test_epw_pipeline.py`)

```python
from orme_lab.pipeline import run_screen, evaluate_candidate
from orme_lab.backends import EPWBackend
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import high_spin_state
from orme_lab.epw.spectral import EliashbergFunction
from orme_lab.evidence import LAB_CEILING


class FakeRunner:
    def __init__(self, ef): self._ef = ef
    def run(self, approx, cfg): return self._ef


def _spike(): return EliashbergFunction(omega=(0, 150, 300, 450, 600), a2f=(0, 0, 1.0, 0, 0))


def _epw_backend():
    b = EPWBackend(runner=FakeRunner(_spike()))
    b.available = lambda: True          # force the gate open for the fake
    return b


def test_no_backend_leaves_sc_columns_toy_and_none():
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=None)
    assert rec.sc_source == "toy" and rec.sc_tc_kelvin is None


def test_epw_backend_populates_tc_fields():
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=_epw_backend())
    assert rec.sc_source == "epw"
    assert rec.sc_tc_kelvin is not None and rec.sc_lambda is not None


def test_evidence_level_never_exceeds_lab_ceiling():
    au = get_element("Au")
    for backend in (None, _epw_backend()):
        rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                                 high_spin_state(au), DEFAULT_CONFIG, backend=backend)
        assert rec.evidence_level <= int(LAB_CEILING)


def test_backend_error_records_failed_and_continues():
    class Boom:
        def run(self, approx, cfg):
            from orme_lab.epw.runner import EPWError
            raise EPWError("boom")
    b = EPWBackend(runner=Boom()); b.available = lambda: True
    au = get_element("Au")
    rec = evaluate_candidate(au, make_compact_cluster(au, 13), "high_spin",
                             high_spin_state(au), DEFAULT_CONFIG, backend=b)
    assert rec.sc_source == "epw:failed" and rec.sc_tc_kelvin is None


def test_screen_toy_columns_identical_with_and_without_epw():
    au = [get_element("Au")]
    toy = run_screen(au, DEFAULT_CONFIG)
    epw = run_screen(au, DEFAULT_CONFIG, backend=_epw_backend())
    for a, b in zip(toy, epw):
        assert a.sc_plausibility == b.sc_plausibility and a.coupling == b.coupling
        assert a.evidence_level == b.evidence_level
```

- [ ] **Step 2: Run to verify they fail**

Run: `pytest tests/test_epw_pipeline.py -q`
Expected: FAIL (`CandidateRecord` has no `sc_source`; `evaluate_candidate` ignores SC_GAP).

- [ ] **Step 3: Modify `pipeline.py`**

Add the fields to `CandidateRecord` (after `sc_plausibility`):

```python
    sc_tc_kelvin: float | None = None
    sc_lambda: float | None = None
    sc_omega_log_k: float | None = None
    sc_gap_mev: float | None = None
    sc_mu_star: float | None = None
    sc_source: str = "toy"
```

In `evaluate_candidate`, add the import at top of file:

```python
from .evidence import badge as evidence_badge, candidate_evidence_level, LAB_CEILING
```

After the `plaus = ...` block and before `return CandidateRecord(`, compute the EPW result:

```python
    # SC_GAP seam (EPW). Gated on provides AND available; a per-candidate failure
    # is recorded, never allowed to abort the screen (G-GATE). No silent fallback.
    from .epw.result import EPWResult
    epw = EPWResult.toy_absent()
    if backend is not None and backend.provides(Capability.SC_GAP) and backend.available():
        try:
            epw = backend.superconducting_gap(element, geometry, state)
        except Exception as exc:  # backstop; the backend should already catch EPWError
            epw = EPWResult.failed(f"{type(exc).__name__}: {exc}")

    level = min(candidate_evidence_level(not plaus.all_passed), LAB_CEILING)
```

Update the `return CandidateRecord(...)` to use `level` and add the sc_* fields:

```python
        sc_plausibility=plaus.score,
        ruled_out=not plaus.all_passed,
        evidence_level=int(level),
        verdict=f"{plaus.explain()} [{evidence_badge(level)}]",
        sc_tc_kelvin=epw.tc_kelvin,
        sc_lambda=epw.lam,
        sc_omega_log_k=epw.omega_log_k,
        sc_gap_mev=epw.gap_mev,
        sc_mu_star=epw.mu_star,
        sc_source=epw.source,
```

Update the module docstring determinism note (G-DETERM): change "given the same `LabConfig`, a screen produces byte-identical output" to scope it — append: "This byte-identity guarantee applies to the toy path (`backend=None`); with a live EPW backend the `sc_*` columns are not byte-reproducible (external solver MPI/BLAS nondeterminism)."

- [ ] **Step 4: Run to verify they pass**

Run: `pytest tests/test_epw_pipeline.py -q`
Expected: PASS (5 passed).

- [ ] **Step 5: Run the full suite**

Run: `pytest -q`
Expected: PASS (all tests green).

- [ ] **Step 6: Update the epw `__init__` exports and commit**

Add to `src/orme_lab/epw/__init__.py`:

```python
from .config import EPWConfig
from .result import EPWResult
from .approximant import build_approximant, ApproximantUndefined, PeriodicApproximant
from .spectral import EliashbergFunction
from .allen_dynes import allen_dynes_tc, bcs_gap_mev
from .runner import EPWError, LiveEPWRunner, EPWRunner

__all__ = [
    "EPWConfig", "EPWResult", "build_approximant", "ApproximantUndefined",
    "PeriodicApproximant", "EliashbergFunction", "allen_dynes_tc", "bcs_gap_mev",
    "EPWError", "LiveEPWRunner", "EPWRunner",
]
```

```bash
git add src/orme_lab/pipeline.py src/orme_lab/epw/__init__.py tests/test_epw_pipeline.py
git commit -m "epw: wire SC_GAP into the pipeline (sc_* record fields, provides∧available gate, min(level, LAB_CEILING))"
```

---

## Self-Review

**Spec coverage:**
- §3 physics (moments, Tc, gap, constants) → Tasks 1, 2. ✓
- §4 subpackage decomposition → Tasks 1–8. ✓
- §5 five must-fix guards: G-DENOM (Task 2), G-SPEC (Task 1), G-CAP (Task 9), G-GATE (Tasks 9+10), G-LEVEL (Task 10). ✓
- §6 corrections: G-COMPLETE/SCRATCH/KILL (Task 7), G-DETERM (Task 10), G-UNIT (Task 2 gap + Task 6 parse meV→K), G-A2F (Task 6), G-LSP (Task 9), G-DI (Task 9), G-MONO (Task 4), G-CSV (Task 10 sc_source always present + None→"" default). ✓
- §7 wiring + EPWConfig → Tasks 5, 9, 10. ✓
- §8 test oracles → Tasks 1, 2 (all named oracles present). ✓
- §9 determinism scoping → Task 10 docstring. ✓
- §11 resolutions (O1 caveat in docstrings, O2 fcc/hcp ideal c/a in Task 4, O3 ship BCS gap Task 2, O4 clamp Task 10, O5 non-deterministic docstring Task 10). ✓

**Type consistency:** `EliashbergFunction`, `EPWResult`, `PeriodicApproximant`, `EPWConfig` signatures are consistent across Tasks 1–10; `superconducting_gap(element, geometry, spin_state)` matches base and backend and pipeline call site; `EPWResult` field names (`tc_kelvin`, `lam`, `omega_log_k`, `omega_2_k`, `gap_mev`, `mu_star`, `source`) match the `CandidateRecord` assignments in Task 10.

**Known follow-ups (out of scope, noted honestly):** the live `LiveEPWRunner.run` path and `qe_input` decks are structurally tested but not validated against a real QE+EPW install — the `.a2f` column semantics and deck correctness must be re-verified against the installed EPW version (§6 G-A2F) before any "validated" claim; the EPW/Migdal-in-magnetic-systems prior-art search (§10) remains a prerequisite to a "validated" label.
