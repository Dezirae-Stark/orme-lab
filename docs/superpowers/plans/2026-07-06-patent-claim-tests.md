# Patent-Claim Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate three Hudson-patent (DE3920144A1) signature claims — the IR doublet, thermal stability, and Meissner Hc1 — into deterministic, evidence-clamped triage screens, and surface all patent claim-methods on the lab site.

**Architecture:** Three focused Python screen modules in `src/orme_lab/`, each mirroring the existing frozen-dataclass + hedged-`explain()` pattern (`superconductivity.py`), returning a computed quantity, a cited reference band, a verdict enum, and an evidence level clamped to `LAB_CEILING` (2). The web layer adds five registry cards (three computable + two documented) and three live-input widgets that are one-line-formula JS mirrors of the Python screens, pinned by a Python parity test.

**Tech Stack:** Python 3 (stdlib `math`, `dataclasses`), pytest; vanilla ES-module JS (no framework), existing `web/` app.

## Global Constraints

- Evidence: every screen verdict carries `evidence_level` and MUST satisfy `evidence_level <= LAB_CEILING` (`EvidenceLevel.SIMULATION_CANDIDATE`, value 2). These screens are mathematical-consistency (Level 1) triage.
- Determinism: no `time`, no RNG, no unseeded/order-dependent iteration anywhere in these paths.
- Reference data: force constants, melting points, Tammann/Hüttig fractions, and SC constants are **representative literature values with a source comment**, never presented as novel measurements. Sources: Herzberg *Spectra of Diatomic Molecules*; Atkins *Physical Chemistry*; Tinkham *Introduction to Superconductivity*; CRC melting points; Tammann/Hüttig sintering rule.
- Neutral outcomes: the findings doc (`docs/patent-claim-tests.md`) is authored only AFTER the screens are run, recording actual verdicts — not before.
- No network egress, no telemetry, loopback-only — unchanged lab invariants.
- Commits: author identity is `Dezirae Stark <deziraestark69@gmail.com>` via `git -c user.name=... -c user.email=...`; NEVER emit AI-identity trailers (`Co-Authored-By`, `Signed-off-by`, `Claude-Session`).
- Branch: work continues on `patent-claim-tests` (already created; spec committed there).
- Tests import modules directly (`from orme_lab.ir_signature import ...`); no `__init__.py` re-export churn.

---

### Task 1: IR-doublet screen (`ir_signature.py`)

**Files:**
- Create: `src/orme_lab/ir_signature.py`
- Test: `tests/test_ir_signature.py`

**Interfaces:**
- Consumes: `orme_lab.evidence.EvidenceLevel`, `orme_lab.evidence.LAB_CEILING`.
- Produces:
  - `WAVENUMBER_CONST: float = 1302.8`
  - `wavenumber(k_mdyne: float, mu_amu: float) -> float`
  - `required_force_constant(nu_cm: float, mu_amu: float) -> float`
  - `metal_family(symbol: str) -> BondFamily`
  - `screen_ir_doublet(symbol: str, lines_cm: tuple[float, ...]) -> IrSignatureResult`
  - `IrSignatureResult` with fields `symbol, observed_lines_cm, k_required_mdyne, metal_band_cm, reachable_by_family, verdict, evidence_level` and method `explain()`. `verdict ∈ {"metal_bond_consistent","light_atom_consistent","metal_bond_excluded","indeterminate"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ir_signature.py
import math

import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.ir_signature import (
    WAVENUMBER_CONST,
    screen_ir_doublet,
    wavenumber,
    required_force_constant,
)


def test_wavenumber_calibration_co():
    # C=O harmonic: k~18.6 mdyne/A, mu(C,O)=6.86 amu -> ~2145 cm^-1 (obs ~2143).
    mu_co = (12.011 * 15.999) / (12.011 + 15.999)
    assert wavenumber(18.6, mu_co) == pytest.approx(2145, rel=0.03)


def test_required_force_constant_rh_line():
    # Rh homodimer mu = 102.905/2; upper patent line 1490.99 cm^-1 -> ~67.4 mdyne/A.
    k = required_force_constant(1490.99, 102.905 / 2)
    assert k == pytest.approx(67.4, rel=0.02)


def test_patent_doublet_excludes_metal_metal():
    r = screen_ir_doublet("Rh", (1429.53, 1490.99))
    assert r.metal_band_cm[1] < 500.0        # Rh-Rh cannot exceed ~406 cm^-1
    assert r.verdict == "light_atom_consistent"
    assert r.reachable_by_family["C–O / C=O"] == (True, True)


def test_low_doublet_stays_metal_consistent():
    # A genuinely metal-range doublet must flip the verdict — the ruler can fail.
    r = screen_ir_doublet("Rh", (200.0, 300.0))
    assert r.verdict == "metal_bond_consistent"


def test_evidence_clamped():
    r = screen_ir_doublet("Rh", (1429.53, 1490.99))
    assert r.evidence_level <= LAB_CEILING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_ir_signature.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.ir_signature'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/ir_signature.py
"""IR-doublet signature screen — Hudson patent DE3920144A1 (claim: 1400-1600 cm^-1 doublet).

Triage, not proof. The patent's own OUME identity marker is an IR doublet in
1400-1600 cm^-1 (quoted: Rh 1429.53/1490.99, Ir 1432.09/1495.17). This screen asks,
deterministically, which bond family could produce a line at that wavenumber within
its representative literature force-constant range, and what force constant a
metal-metal bond would need to reach it.

Physics: harmonic diatomic  nu_tilde (cm^-1) = 1302.8 * sqrt(k/mu),  k in mdyne/A, mu in amu.

Reference values are representative literature ranges (Herzberg, Spectra of Diatomic
Molecules; Atkins, Physical Chemistry), not novel measurements. The metal-metal upper
bound is the envelope including multiply-bonded dimers (e.g. Re2Cl8^2-, nu(M-M) ~275 cm^-1).
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

WAVENUMBER_CONST = 1302.8  # cm^-1 * sqrt(amu / (mdyne/A))

# Atomic masses (amu), CRC standard.
_MASS = {"Rh": 102.905, "Ir": 192.217, "C": 12.011, "N": 14.007, "O": 15.999, "H": 1.008}

_METAL_K_MIN, _METAL_K_MAX = 1.0, 5.0  # metal-metal force-constant envelope (mdyne/A)


def _reduced_mass(m_a: float, m_b: float) -> float:
    return (m_a * m_b) / (m_a + m_b)


def wavenumber(k_mdyne: float, mu_amu: float) -> float:
    """Harmonic diatomic wavenumber (cm^-1) for force constant k (mdyne/A), reduced mass mu (amu)."""
    return WAVENUMBER_CONST * math.sqrt(k_mdyne / mu_amu)


def required_force_constant(nu_cm: float, mu_amu: float) -> float:
    """Force constant (mdyne/A) a bond of reduced mass mu would need to vibrate at nu_cm."""
    return mu_amu * (nu_cm / WAVENUMBER_CONST) ** 2


@dataclass(frozen=True)
class BondFamily:
    name: str
    mu_amu: float
    k_min_mdyne: float
    k_max_mdyne: float
    is_metal_metal: bool = False

    def reachable_band_cm(self) -> tuple[float, float]:
        return (wavenumber(self.k_min_mdyne, self.mu_amu), wavenumber(self.k_max_mdyne, self.mu_amu))

    def contains(self, nu_cm: float) -> bool:
        lo, hi = self.reachable_band_cm()
        return lo <= nu_cm <= hi


# Fixed light-atom reference families (representative literature k ranges).
_LIGHT_FAMILIES = (
    BondFamily("C–O / C=O", _reduced_mass(_MASS["C"], _MASS["O"]), 5.0, 13.0),
    BondFamily("C=C", _reduced_mass(_MASS["C"], _MASS["C"]), 8.0, 10.0),
    BondFamily("N–O", _reduced_mass(_MASS["N"], _MASS["O"]), 10.0, 16.0),
)


def metal_family(symbol: str) -> BondFamily:
    """Homodimer metal-metal family for `symbol` (mu = m/2)."""
    return BondFamily(f"{symbol}–{symbol}", _MASS[symbol] / 2.0, _METAL_K_MIN, _METAL_K_MAX, True)


@dataclass(frozen=True)
class IrSignatureResult:
    symbol: str
    observed_lines_cm: tuple[float, ...]
    k_required_mdyne: tuple[float, ...]
    metal_band_cm: tuple[float, float]
    reachable_by_family: dict[str, tuple[bool, ...]]
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        band = f"{self.metal_band_cm[0]:.0f}–{self.metal_band_cm[1]:.0f} cm^-1"
        kmax = max(self.k_required_mdyne)
        if self.verdict == "metal_bond_consistent":
            return (f"A {self.symbol}-{self.symbol} vibration ({band}) can reach the observed "
                    f"doublet. Metal-metal assignment not excluded (triage only).")
        if self.verdict == "light_atom_consistent":
            return (f"The doublet lies far above the {self.symbol}-{self.symbol} reachable band "
                    f"({band}); reaching it needs k~{kmax:.0f} mdyne/A (vs a metal-metal envelope "
                    f"<=5). A light-atom (C/N/O) bond reaches it within physical force constants. "
                    f"Triage: metal-metal excluded, light-atom assignment consistent.")
        if self.verdict == "metal_bond_excluded":
            return (f"Metal-metal excluded (needs k~{kmax:.0f} mdyne/A >> 5); no reference "
                    f"light-atom family cleanly reaches the doublet either.")
        return "Indeterminate."


def screen_ir_doublet(symbol: str, lines_cm: tuple[float, ...]) -> IrSignatureResult:
    metal = metal_family(symbol)
    k_req = tuple(required_force_constant(nu, metal.mu_amu) for nu in lines_cm)
    reachable = {fam.name: tuple(fam.contains(nu) for nu in lines_cm)
                 for fam in (metal, *_LIGHT_FAMILIES)}

    decisive = max(lines_cm)  # highest line -> largest required k
    if metal.contains(decisive):
        verdict = "metal_bond_consistent"
    elif any(f.contains(decisive) for f in _LIGHT_FAMILIES):
        verdict = "light_atom_consistent"
    else:
        verdict = "metal_bond_excluded"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return IrSignatureResult(symbol, tuple(lines_cm), k_req, metal.reachable_band_cm(),
                             reachable, verdict, level)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_ir_signature.py -q`
Expected: PASS (5 passed)

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/ir_signature.py tests/test_ir_signature.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: IR-doublet triage screen (harmonic reachable-band vs metal-metal)"
```

---

### Task 2: Thermal-stability screen (`thermal_stability.py`)

**Files:**
- Create: `src/orme_lab/thermal_stability.py`
- Test: `tests/test_thermal_stability.py`

**Interfaces:**
- Consumes: `orme_lab.evidence.EvidenceLevel`, `orme_lab.evidence.LAB_CEILING`.
- Produces:
  - `HUTTIG_FRACTION: float = 0.3`, `TAMMANN_FRACTION: float = 0.5`
  - `screen_thermal(symbol: str, t_claim_c: float) -> ThermalStabilityResult`
  - `ThermalStabilityResult` with fields `symbol, t_melt_c, t_huttig_c, t_tammann_c, t_claim_c, verdict, evidence_level` and `explain()`. `verdict ∈ {"within_refractory_envelope","marginal","exceeds_envelope"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_thermal_stability.py
import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.thermal_stability import screen_thermal


def test_tammann_temperature_ir():
    # Ir T_m 2446 C -> Tammann 0.5*(2446+273.15)-273.15 = 1086.4 C.
    assert screen_thermal("Ir", 1200.0).t_tammann_c == pytest.approx(1086.4, abs=1.0)


def test_ir_1200_exceeds_envelope():
    assert screen_thermal("Ir", 1200.0).verdict == "exceeds_envelope"


def test_ir_800_marginal():
    assert screen_thermal("Ir", 800.0).verdict == "marginal"


def test_au_800_exceeds_for_low_melting_metal():
    # Au T_m 1064 C -> Tammann ~395 C; 800 C is above it -> anomalous for Au.
    assert screen_thermal("Au", 800.0).verdict == "exceeds_envelope"


def test_os_500_within_envelope():
    assert screen_thermal("Os", 500.0).verdict == "within_refractory_envelope"


def test_evidence_clamped():
    assert screen_thermal("Ir", 1200.0).evidence_level <= LAB_CEILING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_thermal_stability.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.thermal_stability'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/thermal_stability.py
"""Thermal-stability screen — Hudson patent DE3920144A1 (claims: no sinter at 800 C,
amorphous powder to 1200 C).

Triage, not proof. Compares a claimed stability temperature against the Huttig
(~0.3*T_m) and Tammann (~0.5*T_m) sintering-onset heuristics computed from the bulk
melting point. A claim below the refractory envelope is unremarkable for that metal;
a claim above its Tammann onset would be anomalous for it.

Reference: Tammann/Huttig rule (established in sintering / heterogeneous-catalysis
literature); melting points are CRC-standard values. Heuristic, flagged as such.
"""
from __future__ import annotations

from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

HUTTIG_FRACTION = 0.3
TAMMANN_FRACTION = 0.5
_ABS_ZERO_C = -273.15

# Bulk melting points (C), CRC standard.
_MELT_C = {
    "Rh": 1964, "Ir": 2446, "Pt": 1768, "Pd": 1555, "Os": 3033,
    "Ru": 2334, "Au": 1064, "Ag": 962, "Cu": 1085,
}


def _c_to_k(t_c: float) -> float:
    return t_c - _ABS_ZERO_C


def _k_to_c(t_k: float) -> float:
    return t_k + _ABS_ZERO_C


@dataclass(frozen=True)
class ThermalStabilityResult:
    symbol: str
    t_melt_c: float
    t_huttig_c: float
    t_tammann_c: float
    t_claim_c: float
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        if self.verdict == "within_refractory_envelope":
            return (f"{self.symbol}: claimed stability at {self.t_claim_c:.0f} C is below the "
                    f"Huttig onset ({self.t_huttig_c:.0f} C); ordinary bulk powder already "
                    f"survives this. Not diagnostic of an exotic state.")
        if self.verdict == "marginal":
            return (f"{self.symbol}: {self.t_claim_c:.0f} C sits between Huttig "
                    f"({self.t_huttig_c:.0f}) and Tammann ({self.t_tammann_c:.0f} C) — the "
                    f"ordinary sintering-onset window. Not clearly anomalous.")
        return (f"{self.symbol}: {self.t_claim_c:.0f} C exceeds the Tammann bulk-mobility onset "
                f"({self.t_tammann_c:.0f} C); persistent non-sintering here would be anomalous "
                f"for this metal.")


def screen_thermal(symbol: str, t_claim_c: float) -> ThermalStabilityResult:
    t_melt_c = _MELT_C[symbol]
    t_m_k = _c_to_k(t_melt_c)
    t_huttig_c = _k_to_c(HUTTIG_FRACTION * t_m_k)
    t_tammann_c = _k_to_c(TAMMANN_FRACTION * t_m_k)

    if t_claim_c < t_huttig_c:
        verdict = "within_refractory_envelope"
    elif t_claim_c < t_tammann_c:
        verdict = "marginal"
    else:
        verdict = "exceeds_envelope"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return ThermalStabilityResult(symbol, t_melt_c, t_huttig_c, t_tammann_c, t_claim_c, verdict, level)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_thermal_stability.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/thermal_stability.py tests/test_thermal_stability.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: thermal-stability triage screen (Huttig/Tammann sintering onset)"
```

---

### Task 3: Meissner Hc1 screen (`meissner_field.py`)

**Files:**
- Create: `src/orme_lab/meissner_field.py`
- Test: `tests/test_meissner_field.py`

**Interfaces:**
- Consumes: `orme_lab.evidence.EvidenceLevel`, `orme_lab.evidence.LAB_CEILING`.
- Produces:
  - `PHI0, MU0, M_E, E_CHARGE, EARTH_FIELD_T` (floats)
  - `penetration_depth(b_c1_t: float, ln_kappa: float = 1.0) -> float`
  - `superfluid_density(lambda_m: float) -> float`
  - `screen_meissner(b_c1_t: float = EARTH_FIELD_T, *, isolated_premise: bool = True, ln_kappa: float = 1.0) -> MeissnerFieldResult`
  - `MeissnerFieldResult` with fields `b_c1_tesla, lambda_london_m, implied_superfluid_density_m3, normal_metal_ratio, isolated_premise, verdict, evidence_level` and `explain()`. `verdict ∈ {"in_tension_with_isolation","implied_density_physical","implied_density_unphysical"}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_meissner_field.py
import pytest

from orme_lab.evidence import LAB_CEILING
from orme_lab.meissner_field import (
    EARTH_FIELD_T,
    penetration_depth,
    screen_meissner,
    superfluid_density,
)


def test_penetration_depth_at_earth_field():
    # Hc1 = 50 uT, ln kappa = 1 -> lambda ~ 1.81 um.
    assert penetration_depth(EARTH_FIELD_T) == pytest.approx(1.814e-6, rel=0.01)


def test_superfluid_density_at_earth_field():
    n = superfluid_density(penetration_depth(EARTH_FIELD_T))
    assert n == pytest.approx(8.58e24, rel=0.02)


def test_patent_claim_is_in_tension_with_isolation():
    assert screen_meissner(EARTH_FIELD_T, isolated_premise=True).verdict == "in_tension_with_isolation"


def test_coupled_density_is_physical():
    assert screen_meissner(EARTH_FIELD_T, isolated_premise=False).verdict == "implied_density_physical"


def test_tiny_field_gives_unphysical_density():
    # Absurdly small Hc1 -> huge lambda -> vanishing n_s -> outside physical bounds.
    assert screen_meissner(1e-12, isolated_premise=False).verdict == "implied_density_unphysical"


def test_evidence_clamped():
    assert screen_meissner(EARTH_FIELD_T).evidence_level <= LAB_CEILING
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_meissner_field.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.meissner_field'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/meissner_field.py
"""Meissner Hc1 screen — Hudson patent DE3920144A1 (claim: lower critical field Hc1
below Earth's field ~50 uT for Ir/Au S-OUME).

Triage, not proof. From Hc1 back out the London penetration depth and the implied
superfluid density, and test the claim against (a) physical density bounds and
(b) the lab's own isolation premise (H-04/H-05): any Meissner screening needs
inter-unit phase coherence that an isolated monomer lacks.

  B_c1 ~ (Phi0 / 4 pi lambda^2) * ln kappa      (kappa ~ 2.7 -> ln kappa ~ 1, documented default)
  n_s  = m_e / (mu0 lambda^2 e^2)

Reference constants and conventional-SC Hc scales (Al ~0.01 T, Sn ~0.03 T, Pb ~0.08 T):
Tinkham, Introduction to Superconductivity.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING

PHI0 = 2.067833831e-15        # magnetic flux quantum (Wb)
MU0 = 1.25663706212e-6        # vacuum permeability (H/m)
M_E = 9.1093837015e-31        # electron mass (kg)
E_CHARGE = 1.602176634e-19    # elementary charge (C)

EARTH_FIELD_T = 50e-6         # nominal Earth field (T)
_NORMAL_METAL_N = 1e29        # reference normal-metal carrier density (m^-3)
_N_PHYSICAL_MIN, _N_PHYSICAL_MAX = 1e22, 1e29


def penetration_depth(b_c1_t: float, ln_kappa: float = 1.0) -> float:
    """London penetration depth lambda (m) implied by a lower critical field B_c1 (T)."""
    return math.sqrt(PHI0 * ln_kappa / (4.0 * math.pi * b_c1_t))


def superfluid_density(lambda_m: float) -> float:
    """Superfluid carrier density n_s (m^-3) for penetration depth lambda (m)."""
    return M_E / (MU0 * lambda_m ** 2 * E_CHARGE ** 2)


@dataclass(frozen=True)
class MeissnerFieldResult:
    b_c1_tesla: float
    lambda_london_m: float
    implied_superfluid_density_m3: float
    normal_metal_ratio: float
    isolated_premise: bool
    verdict: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        if self.verdict == "in_tension_with_isolation":
            return (f"Hc1~{self.b_c1_tesla * 1e6:.0f} uT implies lambda~{self.lambda_london_m * 1e6:.2f} um "
                    f"and n_s~{self.implied_superfluid_density_m3:.1e} m^-3 "
                    f"({self.normal_metal_ratio:.1e}x a normal metal). But Meissner screening needs "
                    f"inter-unit phase coherence, which the isolated-monomer premise (H-04/H-05) "
                    f"lacks — the claim is internally in tension with its own premise.")
        if self.verdict == "implied_density_physical":
            return (f"Implied n_s~{self.implied_superfluid_density_m3:.1e} m^-3 is low "
                    f"({self.normal_metal_ratio:.1e}x a normal metal) but within physical bounds "
                    f"for a coupled dilute superconductor.")
        return (f"Implied n_s~{self.implied_superfluid_density_m3:.1e} m^-3 falls outside physical "
                f"bounds [{_N_PHYSICAL_MIN:.0e}, {_N_PHYSICAL_MAX:.0e}] m^-3.")


def screen_meissner(b_c1_t: float = EARTH_FIELD_T, *, isolated_premise: bool = True,
                    ln_kappa: float = 1.0) -> MeissnerFieldResult:
    lam = penetration_depth(b_c1_t, ln_kappa)
    n_s = superfluid_density(lam)
    ratio = n_s / _NORMAL_METAL_N

    if isolated_premise:
        verdict = "in_tension_with_isolation"
    elif _N_PHYSICAL_MIN <= n_s <= _N_PHYSICAL_MAX:
        verdict = "implied_density_physical"
    else:
        verdict = "implied_density_unphysical"

    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return MeissnerFieldResult(b_c1_t, lam, n_s, ratio, isolated_premise, verdict, level)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_meissner_field.py -q`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/meissner_field.py tests/test_meissner_field.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: Meissner Hc1 triage screen (penetration depth / superfluid density / isolation tension)"
```

---

### Task 4: Registry cards — patent group (`hypotheses.js`)

**Files:**
- Modify: `web/hypotheses.js` (add 5 cards to `HYPOTHESES`; extend `renderRegistry`)
- Test: manual — `renderRegistry` is exercised by the parity/整 app; verified visually in Task 7 handoff.

**Interfaces:**
- Consumes: existing `card(h)`, `evidenceBadge`, `PROVENANCE`, `renderRegistry(el)`.
- Produces: five `HYPOTHESES` entries with `group: "patent"`; a `<div id="patentWidgets"></div>` placeholder emitted by `renderRegistry` (Task 5 mounts into it).

- [ ] **Step 1: Add the five patent cards**

In `web/hypotheses.js`, inside the `HYPOTHESES` array (after the last extended entry, before the closing `];`), add:

```javascript
  // ---- Patent-claim tests (Hudson DE3920144A1, tested on its own terms) ----
  {
    id: "P-IR", group: "patent", level: 1, status: "modeled",
    statement: "Patent: OUMEs show an IR doublet at 1400–1600 cm⁻¹ (Rh 1429.53/1490.99; Ir 1432.09/1495.17) as the OUME identity marker.",
    modeled: "ir_signature.py",
    test: "Harmonic ν̃=1302.8√(k/μ): which bond family reaches 1400–1600 cm⁻¹ within physical force constants? Raman/IR on a real sample, controlled for adsorbate/organic bands.",
  },
  {
    id: "P-THERM", group: "patent", level: 1, status: "modeled",
    statement: "Patent: OUMEs do not sinter at 800 °C and stay amorphous to 1200 °C.",
    modeled: "thermal_stability.py",
    test: "Compare claimed stability to Hüttig/Tammann sintering onsets from the bulk melting point; TGA/DSC + XRD on a real sample.",
  },
  {
    id: "P-MEISS", group: "patent", level: 1, status: "modeled",
    statement: "Patent: a lower critical field Hc1 below Earth's field (~50 µT) for Ir/Au S-OUME.",
    modeled: "meissner_field.py",
    test: "Back out λ and nₛ from Hc1; check physical bounds and the isolation premise. SQUID magnetometry (zero-field-cooled Meissner fraction).",
  },
  {
    id: "P-JJ", group: "patent", level: 0, status: "roadmap",
    statement: "Patent: an ac-Josephson-type response above Hc2.",
    modeled: "documented — see coupling-channel prior-art",
    test: "Not independently falsifiable in this framework; would need a real junction I–V with Shapiro steps under microwave drive.",
  },
  {
    id: "P-ASSAY", group: "patent", level: 0, status: "premise",
    statement: "Patent: OUMEs evade conventional instrumental analysis (ore 'assays to <100%').",
    modeled: "documented — flagged unfalsifiable-by-construction",
    test: "A claim that fails all detection methods is not testable as stated; requires an independent quantitative recovery (ICP-MS mass balance) to even define.",
  },
```

- [ ] **Step 2: Extend `renderRegistry` to render the patent section**

In `web/hypotheses.js`, in `renderRegistry(el)`, add `const patent = HYPOTHESES.filter((h) => h.group === "patent");` alongside the existing `core`/`ext` filters, and insert the patent section into the `el.innerHTML` string immediately BEFORE the `Provenance` section label:

```javascript
    `<div class="reg-section-label">Patent-claim tests · P-* <span>Hudson DE3920144A1, tested on its own terms</span></div>` +
    `<div class="hyp-grid">${patent.map(card).join("")}</div>` +
    `<div id="patentWidgets"></div>` +
```

- [ ] **Step 3: Verify the module still parses**

Run: `node --check web/hypotheses.js`
Expected: no output, exit 0.

- [ ] **Step 4: Commit**

```bash
git add web/hypotheses.js
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(web): patent-claim cards + registry section (P-IR/THERM/MEISS/JJ/ASSAY)"
```

---

### Task 5: Live-input widgets (`patent_tests.js`) + app wiring

**Files:**
- Create: `web/patent_tests.js`
- Modify: `web/app.js` (import + one call after `renderRegistry`)
- Modify: `web/styles.css` (small `.patent-widget` block)

**Interfaces:**
- Consumes: `#patentWidgets` container (emitted by `renderRegistry`, Task 4).
- Produces: `renderPatentTests(el: HTMLElement) -> void`; exported constants `WAVENUMBER_CONST, HUTTIG_FRACTION, TAMMANN_FRACTION, PHI0, MU0, M_E, E_CHARGE` (Task 6 pins these).

- [ ] **Step 1: Create the widget module**

```javascript
// web/patent_tests.js
/*
 * patent_tests.js -- live-input widgets for the three computable Hudson-patent
 * claim screens (IR doublet, thermal stability, Meissner Hc1). Each widget is a
 * one-line-formula JS mirror of the authoritative Python screen in src/orme_lab/;
 * the shared constants below are pinned to the Python modules by
 * tests/test_patent_web_parity.py. Triage only -- evidence Level <= 2.
 */

// ---- shared physical constants (pinned to Python by parity test) ----------
export const WAVENUMBER_CONST = 1302.8;       // ir_signature.py
export const HUTTIG_FRACTION = 0.3;           // thermal_stability.py
export const TAMMANN_FRACTION = 0.5;          // thermal_stability.py
export const PHI0 = 2.067833831e-15;          // meissner_field.py
export const MU0 = 1.25663706212e-6;
export const M_E = 9.1093837015e-31;
export const E_CHARGE = 1.602176634e-19;

const MASS = { Rh: 102.905, Ir: 192.217, C: 12.011, N: 14.007, O: 15.999 };
const MELT_C = { Rh: 1964, Ir: 2446, Pt: 1768, Pd: 1555, Os: 3033, Ru: 2334, Au: 1064, Ag: 962, Cu: 1085 };
const reduced = (a, b) => (a * b) / (a + b);
const wavenumber = (k, mu) => WAVENUMBER_CONST * Math.sqrt(k / mu);
const requiredK = (nu, mu) => mu * (nu / WAVENUMBER_CONST) ** 2;

function irVerdict(sym, hi) {
  const mu = MASS[sym] / 2;
  const metalHi = wavenumber(5, mu);
  const co = [wavenumber(5, reduced(MASS.C, MASS.O)), wavenumber(13, reduced(MASS.C, MASS.O))];
  const kReq = requiredK(hi, mu);
  let v;
  if (hi <= metalHi) v = `${sym}–${sym} reachable — metal–metal not excluded`;
  else if (hi >= co[0] && hi <= co[1]) v = `metal–metal excluded (needs k~${kReq.toFixed(0)} mdyne/Å >> 5); light-atom (C/N/O) consistent`;
  else v = `metal–metal excluded (k~${kReq.toFixed(0)}); no clean light-atom fit`;
  return `ν̃=${hi.toFixed(0)} cm⁻¹ → ${sym}–${sym} band tops out at ${metalHi.toFixed(0)} cm⁻¹. ${v}.`;
}

function thermalVerdict(sym, tClaim) {
  const tmK = MELT_C[sym] + 273.15;
  const huttig = HUTTIG_FRACTION * tmK - 273.15;
  const tammann = TAMMANN_FRACTION * tmK - 273.15;
  let v;
  if (tClaim < huttig) v = "within refractory envelope (not diagnostic)";
  else if (tClaim < tammann) v = "marginal (ordinary sintering window)";
  else v = "exceeds Tammann onset (anomalous for this metal)";
  return `${sym}: Hüttig ${huttig.toFixed(0)} °C, Tammann ${tammann.toFixed(0)} °C → claim at ${tClaim.toFixed(0)} °C is ${v}.`;
}

function meissnerVerdict(bc1uT) {
  const bc1 = bc1uT * 1e-6;
  const lam = Math.sqrt(PHI0 / (4 * Math.PI * bc1));
  const ns = M_E / (MU0 * lam * lam * E_CHARGE * E_CHARGE);
  return `Hc1=${bc1uT.toFixed(0)} µT → λ≈${(lam * 1e6).toFixed(2)} µm, nₛ≈${ns.toExponential(1)} m⁻³ (${(ns / 1e29).toExponential(1)}× a normal metal). Meissner screening needs coherence the isolated-monomer premise lacks — in tension with its own premise.`;
}

const _elements = Object.keys(MELT_C);

export function renderPatentTests(el) {
  if (!el) return;
  el.innerHTML = `
    <div class="patent-widget">
      <div class="pw-title">IR doublet — bond assignment</div>
      <label>upper line (cm⁻¹) <input id="pwIrLine" class="field" type="number" value="1490.99" step="0.01"></label>
      <label>metal <select id="pwIrSym" class="field">${["Rh", "Ir"].map((s) => `<option>${s}</option>`).join("")}</select></label>
      <p class="pw-out" id="pwIrOut"></p>
    </div>
    <div class="patent-widget">
      <div class="pw-title">Thermal stability — sintering onset</div>
      <label>metal <select id="pwThSym" class="field">${_elements.map((s) => `<option${s === "Ir" ? " selected" : ""}>${s}</option>`).join("")}</select></label>
      <label>claimed stable to (°C) <input id="pwThT" class="field" type="number" value="1200" step="10"></label>
      <p class="pw-out" id="pwThOut"></p>
    </div>
    <div class="patent-widget">
      <div class="pw-title">Meissner Hc1 — implied λ / nₛ</div>
      <label>Hc1 (µT) <input id="pwMeB" class="field" type="number" value="50" step="1"></label>
      <p class="pw-out" id="pwMeOut"></p>
    </div>`;

  const $ = (id) => el.querySelector("#" + id);
  const updIr = () => { $("pwIrOut").textContent = irVerdict($("pwIrSym").value, parseFloat($("pwIrLine").value) || 0); };
  const updTh = () => { $("pwThOut").textContent = thermalVerdict($("pwThSym").value, parseFloat($("pwThT").value) || 0); };
  const updMe = () => { $("pwMeOut").textContent = meissnerVerdict(parseFloat($("pwMeB").value) || 0); };
  $("pwIrLine").addEventListener("input", updIr); $("pwIrSym").addEventListener("change", updIr);
  $("pwThSym").addEventListener("change", updTh); $("pwThT").addEventListener("input", updTh);
  $("pwMeB").addEventListener("input", updMe);
  updIr(); updTh(); updMe();
}
```

- [ ] **Step 2: Wire into `app.js`**

Add the import next to the existing hypotheses import (near `web/app.js:6`):

```javascript
import { renderPatentTests } from "./patent_tests.js?v=__BUILD__";
```

Immediately after the existing `renderRegistry($("regBody"));` call (near `web/app.js:512`), add:

```javascript
  renderPatentTests($("patentWidgets"));
```

- [ ] **Step 3: Add widget styles**

Append to `web/styles.css`:

```css
/* Patent-claim live-input widgets */
.patent-widget { border: 1px solid var(--line, #2a2a2a); border-radius: 8px; padding: 12px; margin: 10px 0; }
.patent-widget .pw-title { font-weight: 600; margin-bottom: 8px; }
.patent-widget label { display: inline-flex; gap: 6px; align-items: center; margin-right: 14px; }
.patent-widget .pw-out { margin-top: 10px; font-size: 0.9em; opacity: 0.9; }
```

- [ ] **Step 4: Verify modules parse**

Run: `node --check web/patent_tests.js && node --check web/app.js`
Expected: no output, exit 0.

- [ ] **Step 5: Commit**

```bash
git add web/patent_tests.js web/app.js web/styles.css
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(web): live-input widgets for IR/thermal/Meissner patent screens"
```

---

### Task 6: Python↔JS parity test (`test_patent_web_parity.py`)

**Files:**
- Create: `tests/test_patent_web_parity.py`

**Interfaces:**
- Consumes: `orme_lab.ir_signature.WAVENUMBER_CONST`; `orme_lab.thermal_stability.HUTTIG_FRACTION/TAMMANN_FRACTION`; `orme_lab.meissner_field.PHI0/MU0/M_E/E_CHARGE`; the text of `web/patent_tests.js`.
- Produces: nothing (guard test).

- [ ] **Step 1: Write the parity test**

```python
# tests/test_patent_web_parity.py
"""Pins the web widgets' physical constants to the authoritative Python screens,
so web/patent_tests.js cannot silently drift from src/orme_lab/."""
import pathlib
import re

from orme_lab import ir_signature, meissner_field, thermal_stability

_JS = pathlib.Path(__file__).resolve().parents[1] / "web" / "patent_tests.js"


def _js_const(name: str) -> float:
    m = re.search(rf"export const {name}\s*=\s*([0-9eE.+\-]+)\s*;", _JS.read_text())
    assert m, f"{name} not found in patent_tests.js"
    return float(m.group(1))


def test_ir_constant_parity():
    assert _js_const("WAVENUMBER_CONST") == ir_signature.WAVENUMBER_CONST


def test_thermal_fraction_parity():
    assert _js_const("HUTTIG_FRACTION") == thermal_stability.HUTTIG_FRACTION
    assert _js_const("TAMMANN_FRACTION") == thermal_stability.TAMMANN_FRACTION


def test_meissner_constant_parity():
    assert _js_const("PHI0") == meissner_field.PHI0
    assert _js_const("MU0") == meissner_field.MU0
    assert _js_const("M_E") == meissner_field.M_E
    assert _js_const("E_CHARGE") == meissner_field.E_CHARGE
```

- [ ] **Step 2: Run the parity test**

Run: `python -m pytest tests/test_patent_web_parity.py -q`
Expected: PASS (3 passed)

- [ ] **Step 3: Run the full suite**

Run: `python -m pytest -q`
Expected: PASS (previous 207 + 20 new = 227 passed; count exact totals from output, no failures)

- [ ] **Step 4: Commit**

```bash
git add tests/test_patent_web_parity.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "test: pin web patent-widget constants to Python screens (parity)"
```

---

### Task 7: Run the screens & write findings (`docs/patent-claim-tests.md`)

**Files:**
- Create: `docs/patent-claim-tests.md`

**Interfaces:**
- Consumes: `screen_ir_doublet`, `screen_thermal`, `screen_meissner`.
- Produces: findings doc (human-facing).

- [ ] **Step 1: Run the three screens for the patent's actual quoted values**

Run:

```bash
python - <<'PY'
from orme_lab.ir_signature import screen_ir_doublet
from orme_lab.thermal_stability import screen_thermal
from orme_lab.meissner_field import screen_meissner

for sym, lines in (("Rh", (1429.53, 1490.99)), ("Ir", (1432.09, 1495.17))):
    r = screen_ir_doublet(sym, lines)
    print("IR", sym, r.verdict, "kreq=%.1f" % max(r.k_required_mdyne), "band=%.0f-%.0f" % r.metal_band_cm)
    print("   ", r.explain())

for sym, t in (("Ir", 1200.0), ("Rh", 1200.0), ("Au", 800.0), ("Os", 500.0)):
    r = screen_thermal(sym, t)
    print("THERM", sym, t, r.verdict, "huttig=%.0f tammann=%.0f" % (r.t_huttig_c, r.t_tammann_c))

r = screen_meissner()
print("MEISS", r.verdict, "lambda=%.2e n_s=%.2e ratio=%.1e" % (r.lambda_london_m, r.implied_superfluid_density_m3, r.normal_metal_ratio))
print("   ", r.explain())
PY
```

Expected: deterministic output. Record the ACTUAL printed verdicts and numbers — do not pre-fill.

- [ ] **Step 2: Write `docs/patent-claim-tests.md`**

Author the findings doc from the captured output. Required sections:
- **Provenance** — one line linking `~/.claude/research-wiki/prior-art/hudson-orme-patents-de3920144a1.md` and the P-* cards.
- **Method** — the three screens, their formulas, and the cited reference bands (verbatim from module docstrings).
- **Results** — one subsection per screen with the ACTUAL verdicts/numbers from Step 1, each labelled `Evidence Level 1/6 (mathematical consistency; triage, not proof)`.
- **Caveats** — IR reference bands are representative literature ranges, not per-species measurements; Tammann/Hüttig is a heuristic; the Meissner isolation-tension verdict is contingent on the isolated-monomer premise (toggle `isolated_premise=False` to see the density-only branch); the two documented cards (ac-Josephson, assay<100%) are not computably falsified here.

- [ ] **Step 3: Verify the doc references match reality**

Run: `python -m pytest -q && node --check web/hypotheses.js && node --check web/patent_tests.js`
Expected: all PASS / exit 0.

- [ ] **Step 4: Commit**

```bash
git add docs/patent-claim-tests.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "docs: patent-claim triage findings (IR-doublet, thermal, Meissner)"
```

---

## Self-Review

**1. Spec coverage.** Spec Test 1 → Task 1; Test 2 → Task 2; Test 3 → Task 3; documented cards (ac-Josephson, assay<100%) → Task 4 (P-JJ, P-ASSAY); web integration (`patent` group + 3 widgets) → Tasks 4–5; parity test → Task 6; findings doc → Task 7. All spec sections mapped. Evidence-ceiling assertion present in every module's test. Neutral-outcomes honored: Task 7 authors the doc only after running.

**2. Placeholder scan.** No "TBD"/"handle edge cases"/"similar to Task N". Task 7 Step 2 intentionally leaves the *findings text* to be written from live output (this is the neutral-outcomes requirement, not a code placeholder); its required sections and inputs are fully specified.

**3. Type consistency.** `screen_ir_doublet(symbol, lines_cm)`, `screen_thermal(symbol, t_claim_c)`, `screen_meissner(b_c1_t, *, isolated_premise, ln_kappa)` — names and signatures identical across interfaces, implementations, tests, and Task 7. Verdict enum strings match between each module and its tests. Exported constant names (`WAVENUMBER_CONST`, `HUTTIG_FRACTION`, `TAMMANN_FRACTION`, `PHI0`, `MU0`, `M_E`, `E_CHARGE`) are identical in the Python modules, `patent_tests.js`, and the parity test regex. `#patentWidgets` is emitted by `renderRegistry` (Task 4 Step 2) and consumed by `renderPatentTests` (Task 5 Step 2).
