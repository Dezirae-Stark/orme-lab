# IR-doublet Contaminant Control Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the positive leg to the patent IR-doublet screen — a cited contaminant reference library that scores the observed doublet against known IR-active species and ranks the matches, plus a coupled-oscillator physics model for the top match.

**Architecture:** New module `src/orme_lab/ir_contaminant.py` sibling to the existing `ir_signature.py` (which stays the negative/exclusion leg). Layer 1 is a match-and-rank screen over a `_CONTAMINANTS` reference table whose band values are sourced and citation-audited *before* they are coded (Task 1). Layer 2 is a closed-form coupled-oscillator model applied to whichever candidate ranks top at runtime. Web widget and parity test extend to mirror the new table.

**Tech Stack:** Python 3 (stdlib only: `math`, `dataclasses`), pytest, vanilla ES-module JS (`web/patent_tests.js`).

## Global Constraints

- Evidence Level ≤ 2 (`LAB_CEILING`) on every verdict — `EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))`.
- Deterministic: no `time`, no RNG, no order-dependent iteration. Ranking sorts by a total key `(score, category_rank, name)` with a stable name tiebreak.
- No fabricated citations: every band value in `_CONTAMINANTS` carries an inline `source` comment and is verified against a primary reference by Task 1 before it is committed. A candidate whose bands cannot be sourced is dropped and the omission recorded.
- Neutral outcomes: no winning assignment asserted in any test; the patent-doublet test asserts only structural properties; the actual ranking is recorded in the findings doc after the screen runs. The screen must be provably able to return `unmatched`.
- No network egress, no telemetry, loopback-only — unchanged lab invariants.
- Commit identity: `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`, `--no-verify` not required but never emit AI-identity trailers (Co-Authored-By / Signed-off-by / Claude-Session) in author, committer, or message body.
- Harmonic constant is `WAVENUMBER_CONST = 1302.8`, imported from `ir_signature.py` — never re-declared.
- Branch: all implementation lands on a feature branch `ir-contaminant-control` off `master`; open a PR at the end, do not merge without operator approval.

---

### Task 1: Source-verification gate (research, no code)

**Files:**
- Create: `~/.claude/research-wiki/prior-art/ir-contaminant-bands.md` (user-level prior-art wiki, matching `hudson-orme-patents-de3920144a1.md`)

**Interfaces:**
- Produces: a verified table — for each candidate species — of `lo_band (lo_min,lo_max)`, `hi_band (hi_min,hi_max)`, `split_band (d_min,d_max)` in cm⁻¹, the stretch reduced mass `oscillator_mu` (amu) where a coupled-stretch model applies, `coupled_applicable` (bool), and a `source` string (author, title, table/page). Consumed verbatim by Task 4 and Task 5.

**Candidate roster to source** (route-derived tier first, then standard):
nitrate NO₃⁻, carbonate CO₃²⁻, carboxylate/acetate COO⁻, water bend δ(H₂O), alkyl C–H scissor/bend pair, ammonium NH₄⁺, sulfate SO₄²⁻, silicone/PDMS.

- [ ] **Step 1: Dispatch prior-art sourcing**

Dispatch the `prior-art-cartographer` subagent. Task it to find, for each candidate species above, the characteristic IR band positions in the 1200–1700 cm⁻¹ region and the characteristic asymmetric/symmetric splitting, from primary references: Nakamoto, *Infrared and Raman Spectra of Inorganic and Coordination Compounds* (nitrate/carbonate/carboxylate metal-complex bands and coordination-dependent splittings); Socrates, *Infrared and Raman Characteristic Group Frequencies* (C–H, silicone, ammonium, sulfate); NIST Chemistry WebBook. Require a page/table reference for every number. Record all searches and results to `~/.claude/research-wiki/prior-art/ir-contaminant-bands.md`.

- [ ] **Step 2: Citation audit**

Dispatch the `citation-auditor` subagent against `ir-contaminant-bands.md`. It verifies every band number is attributable to its cited source and flags any value that cannot be confirmed. Drop any candidate whose bands the auditor cannot confirm; record the drop in the wiki file with the reason (honest absence over confident filler).

- [ ] **Step 3: Freeze the sourced table**

Confirm the wiki file contains, for each surviving candidate, the six band edges + `oscillator_mu` + `coupled_applicable` + `source`. This frozen table is the single source of truth transcribed into code in Tasks 4–5. No commit (file is outside the repo); the numbers enter the repo as code + source comments in later tasks.

---

### Task 2: `ContaminantBand` + match-score primitive

**Files:**
- Create: `src/orme_lab/ir_contaminant.py`
- Test: `tests/test_ir_contaminant.py`

**Interfaces:**
- Consumes: `WAVENUMBER_CONST`, `wavenumber` from `ir_signature.py`; `EvidenceLevel`, `LAB_CEILING` from `evidence.py`.
- Produces: `ContaminantBand(name, category, lo_band, hi_band, split_band, oscillator_mu, coupled_applicable, source)`; `match_score(lines_cm, band) -> float`; module-level `_CAT_RANK`, `_TOL_PLAUSIBLE`, `_band_residual`.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_ir_contaminant.py
import math
import pytest
from orme_lab.ir_contaminant import ContaminantBand, match_score, _band_residual


def _synthetic(name="x", category="route_derived", lo=(1420, 1440), hi=(1480, 1500),
               split=(50, 70), mu=6.856, coupled=True, source="test"):
    return ContaminantBand(name, category, lo, hi, split, mu, coupled, source)


def test_band_residual_inside_is_zero():
    assert _band_residual(1430, (1420, 1440)) == 0.0


def test_band_residual_outside_is_bandwidths():
    # 10 cm^-1 below a 20-wide band -> 0.5 band-widths
    assert _band_residual(1410, (1420, 1440)) == pytest.approx(0.5)
    assert _band_residual(1460, (1420, 1440)) == pytest.approx(1.0)


def test_match_score_dead_centre_is_zero():
    band = _synthetic()
    # lines 1430 / 1490 -> both centred, split 60 centred
    assert match_score((1430.0, 1490.0), band) == pytest.approx(0.0)


def test_match_score_orders_lines():
    band = _synthetic()
    # unordered input must be normalised (min=lo, max=hi)
    assert match_score((1490.0, 1430.0), band) == pytest.approx(0.0)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: FAIL — `ModuleNotFoundError` / cannot import `ContaminantBand`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/ir_contaminant.py
"""IR-doublet contaminant control — Hudson patent DE3920144A1 (positive leg).

Triage, not proof. The negative leg (src/orme_lab/ir_signature.py) excludes a
metal-metal assignment for the patent's quoted doublet. This module supplies the
positive leg: a cited reference library of IR-active species the patent's own
wet-chemistry route would deposit, scored against the observed doublet by line
position AND splitting, and ranked. Verdict may be `unmatched` — with metal-metal
already excluded, that is the anomalous branch that would support the patent.

Band values are sourced and citation-audited before entry (see
~/.claude/research-wiki/prior-art/ir-contaminant-bands.md); every row carries a
source comment. Reuses the harmonic constant 1302.8 from ir_signature.py.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .evidence import EvidenceLevel, LAB_CEILING
from .ir_signature import WAVENUMBER_CONST, wavenumber  # noqa: F401  (wavenumber used in Task 5)

_CAT_RANK = {"route_derived": 0, "standard": 1}
_TOL_PLAUSIBLE = 1.0  # total normalised band-width residual admitted as a plausible match


@dataclass(frozen=True)
class ContaminantBand:
    name: str
    category: str                       # "route_derived" | "standard"
    lo_band: tuple[float, float]        # lower-line cm^-1 range
    hi_band: tuple[float, float]        # upper-line cm^-1 range
    split_band: tuple[float, float]     # asym-sym splitting cm^-1 range
    oscillator_mu: float | None         # stretch reduced mass (amu) for layer-2; None if N/A
    coupled_applicable: bool
    source: str


def _band_residual(x: float, band: tuple[float, float]) -> float:
    """0 if x is inside [lo, hi]; else the distance outside expressed in band-widths."""
    lo, hi = band
    if lo <= x <= hi:
        return 0.0
    width = hi - lo if hi > lo else 1.0
    return (lo - x) / width if x < lo else (x - hi) / width


def match_score(lines_cm: tuple[float, ...], band: ContaminantBand) -> float:
    """Total normalised residual of a doublet against a candidate band (0 = perfect)."""
    lo_line, hi_line = min(lines_cm), max(lines_cm)
    split = hi_line - lo_line
    return (_band_residual(lo_line, band.lo_band)
            + _band_residual(hi_line, band.hi_band)
            + _band_residual(split, band.split_band))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: PASS (4 tests).

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/ir_contaminant.py tests/test_ir_contaminant.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: ContaminantBand + normalized match-score primitive"
```

---

### Task 3: `screen_contaminants` + verdict + `ContaminantMatchResult`

**Files:**
- Modify: `src/orme_lab/ir_contaminant.py`
- Test: `tests/test_ir_contaminant.py`

**Interfaces:**
- Consumes: `ContaminantBand`, `match_score`, `_band_residual`, `_CAT_RANK`, `_TOL_PLAUSIBLE`.
- Produces: `ContaminantMatchResult(observed_lines_cm, splitting_cm, ranked, verdict, top_source, evidence_level)` with `.explain()`; `screen_contaminants(lines_cm, bands) -> ContaminantMatchResult`. Note `screen_contaminants` takes the band list as a parameter (defaulting to `_CONTAMINANTS`, populated in Task 4) so it is testable with synthetic bands now.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_ir_contaminant.py
from orme_lab.ir_contaminant import screen_contaminants, ContaminantMatchResult
from orme_lab.evidence import LAB_CEILING


def test_tight_match_when_all_bands_contain():
    bands = [_synthetic(name="fits", lo=(1420, 1440), hi=(1480, 1500), split=(50, 70))]
    r = screen_contaminants((1430.0, 1490.0), bands)
    assert r.verdict == "tight_match"
    assert r.ranked[0][0] == "fits"
    assert r.evidence_level <= 2


def test_unmatched_when_far_from_every_band():
    bands = [_synthetic(name="a", lo=(1000, 1010), hi=(1020, 1030), split=(10, 20))]
    r = screen_contaminants((1430.0, 1490.0), bands)
    assert r.verdict == "unmatched"


def test_splitting_discriminates_at_equal_position_error():
    # both candidates miss the lines equally, but only `rightsplit` has the right splitting
    rightsplit = _synthetic(name="rightsplit", lo=(1400, 1405), hi=(1515, 1520), split=(55, 65))
    wrongsplit = _synthetic(name="wrongsplit", lo=(1400, 1405), hi=(1515, 1520), split=(100, 110))
    r = screen_contaminants((1430.0, 1490.0), [wrongsplit, rightsplit])
    assert r.ranked[0][0] == "rightsplit"


def test_ranking_is_deterministic_stable_tiebreak():
    # equal score -> route_derived before standard, then name-alphabetical
    b1 = _synthetic(name="zeta", category="route_derived")
    b2 = _synthetic(name="alpha", category="standard")
    r = screen_contaminants((1430.0, 1490.0), [b2, b1])
    assert [n for n, _ in r.ranked] == ["zeta", "alpha"]


def test_result_is_frozen():
    r = screen_contaminants((1430.0, 1490.0), [_synthetic()])
    with pytest.raises(Exception):
        r.verdict = "x"  # frozen dataclass
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: FAIL — cannot import `screen_contaminants`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/orme_lab/ir_contaminant.py`:

```python
@dataclass(frozen=True)
class ContaminantMatchResult:
    observed_lines_cm: tuple[float, ...]
    splitting_cm: float
    ranked: tuple[tuple[str, float], ...]   # (name, score), ascending
    verdict: str                            # tight_match | plausible_match | unmatched
    top_source: str
    evidence_level: EvidenceLevel

    def explain(self) -> str:
        top_name, top_score = self.ranked[0]
        if self.verdict == "tight_match":
            return (f"Doublet {self.observed_lines_cm} (splitting {self.splitting_cm:.1f} cm^-1) "
                    f"falls inside the cited band of {top_name}. A mundane contaminant "
                    f"explains it (triage only; source: {self.top_source}).")
        if self.verdict == "plausible_match":
            return (f"Closest cited species is {top_name} (residual {top_score:.2f} band-widths; "
                    f"source: {self.top_source}); a contaminant assignment is plausible but not tight.")
        return (f"No cited contaminant matches the doublet within tolerance "
                f"(closest {top_name}, residual {top_score:.2f} band-widths). With metal-metal "
                f"already excluded, the doublet is unmatched — an anomalous result.")


def screen_contaminants(lines_cm: tuple[float, ...],
                        bands: "list[ContaminantBand] | None" = None) -> ContaminantMatchResult:
    table = list(_CONTAMINANTS if bands is None else bands)
    lo, hi = min(lines_cm), max(lines_cm)
    scored = [(b, match_score(lines_cm, b)) for b in table]
    scored.sort(key=lambda bs: (bs[1], _CAT_RANK[bs[0].category], bs[0].name))

    top_band, top_score = scored[0]
    lo_r = _band_residual(lo, top_band.lo_band)
    hi_r = _band_residual(hi, top_band.hi_band)
    sp_r = _band_residual(hi - lo, top_band.split_band)
    if lo_r == 0.0 and hi_r == 0.0 and sp_r == 0.0:
        verdict = "tight_match"
    elif top_score <= _TOL_PLAUSIBLE:
        verdict = "plausible_match"
    else:
        verdict = "unmatched"

    ranked = tuple((b.name, s) for b, s in scored)
    level = EvidenceLevel(min(EvidenceLevel.MATHEMATICAL_CONSISTENCY, LAB_CEILING))
    return ContaminantMatchResult(tuple(lines_cm), hi - lo, ranked, verdict, top_band.source, level)
```

Add a module-level placeholder so the default path imports cleanly until Task 4 fills it:

```python
_CONTAMINANTS: "tuple[ContaminantBand, ...]" = ()  # populated in Task 4 from the sourced table
```

Place this `_CONTAMINANTS = ()` line directly after `_TOL_PLAUSIBLE` (Task 4 replaces it).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: PASS (9 tests total).

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/ir_contaminant.py tests/test_ir_contaminant.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: screen_contaminants ranking + verdict (synthetic-band tested)"
```

---

### Task 4: Populate `_CONTAMINANTS` from the sourced table + neutral patent test

**Files:**
- Modify: `src/orme_lab/ir_contaminant.py` (replace `_CONTAMINANTS = ()`)
- Test: `tests/test_ir_contaminant.py`

**Interfaces:**
- Consumes: the frozen sourced table from Task 1 (`ir-contaminant-bands.md`).
- Produces: populated `_CONTAMINANTS` tuple.

- [ ] **Step 1: Transcribe the sourced table**

Replace the `_CONTAMINANTS = ()` line with one `ContaminantBand(...)` row per **surviving** candidate from Task 1, values copied verbatim from `ir-contaminant-bands.md`, each with an inline `# source:` comment naming author + table/page. Shape (fill numbers from the wiki — **do not invent**):

```python
_CONTAMINANTS: "tuple[ContaminantBand, ...]" = (
    ContaminantBand("nitrate NO3-", "route_derived",
                    lo_band=(..., ...), hi_band=(..., ...), split_band=(..., ...),
                    oscillator_mu=7.464, coupled_applicable=True,
                    source="Nakamoto Part A, Table ... (NO3- nu3 splitting)"),
    # ... one row per surviving candidate, route_derived first ...
)
```

`oscillator_mu` values are reduced masses of the relevant stretch (N–O ≈ 7.464, C–O ≈ 6.856), computable from atomic masses; `coupled_applicable=False` with `oscillator_mu=None` for single-band species (e.g. water bend). Every number traces to the wiki.

- [ ] **Step 2: Write the neutral structural test**

```python
# add to tests/test_ir_contaminant.py
from orme_lab.ir_contaminant import _CONTAMINANTS


def test_library_is_populated_and_well_formed():
    assert len(_CONTAMINANTS) >= 4  # at least the route-derived tier survived sourcing
    for b in _CONTAMINANTS:
        assert b.category in ("route_derived", "standard")
        assert b.lo_band[0] <= b.lo_band[1]
        assert b.hi_band[0] <= b.hi_band[1]
        assert b.split_band[0] <= b.split_band[1]
        assert b.source  # every row cites a source


def test_patent_doublets_run_neutrally():
    # NEUTRAL: assert structure only, never a specific winner.
    for lines in ((1429.53, 1490.99), (1432.09, 1495.17)):
        r = screen_contaminants(lines)
        assert r.verdict in ("tight_match", "plausible_match", "unmatched")
        assert r.evidence_level <= 2
        assert len(r.ranked) == len(_CONTAMINANTS)
        scores = [s for _, s in r.ranked]
        assert scores == sorted(scores)  # ascending / deterministic
```

- [ ] **Step 3: Run tests to verify they pass**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: PASS. If `test_library_is_populated_and_well_formed` fails on `>= 4`, fewer than four candidates survived sourcing — revisit Task 1, do not lower the bar silently.

- [ ] **Step 4: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/ir_contaminant.py tests/test_ir_contaminant.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: populate cited contaminant library + neutral patent-doublet test"
```

---

### Task 5: Coupled-oscillator physics model (layer 2)

**Files:**
- Modify: `src/orme_lab/ir_contaminant.py`
- Test: `tests/test_ir_contaminant.py`

**Interfaces:**
- Consumes: `WAVENUMBER_CONST`; `ContaminantBand`.
- Produces: `coupled_stretch(k, k_int, mu) -> (nu_sym, nu_asym)`; `back_out_coupling(nu_lo, nu_hi, mu) -> (k, k_int)`; `coupled_model_for(band, lines_cm) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# add to tests/test_ir_contaminant.py
from orme_lab.ir_contaminant import coupled_stretch, back_out_coupling, coupled_model_for


def test_coupled_roundtrip():
    k, k_int, mu = 10.0, 0.5, 6.856
    nu_sym, nu_asym = coupled_stretch(k, k_int, mu)
    assert nu_asym > nu_sym  # antisymmetric (out-of-phase) is the higher line
    k_back, k_int_back = back_out_coupling(nu_sym, nu_asym, mu)
    assert k_back == pytest.approx(k, rel=1e-6)
    assert k_int_back == pytest.approx(k_int, rel=1e-6)


def test_coupled_model_reports_force_constants():
    band = _synthetic(name="nitrate NO3-", mu=7.464, coupled=True)
    msg = coupled_model_for(band, (1429.53, 1490.99))
    assert "nitrate NO3-" in msg
    assert "mdyne" in msg


def test_coupled_model_not_applicable_for_single_band():
    band = _synthetic(name="water bend", mu=None, coupled=False)
    msg = coupled_model_for(band, (1429.53, 1490.99))
    assert "N/A" in msg or "not a" in msg.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: FAIL — cannot import `coupled_stretch`.

- [ ] **Step 3: Write minimal implementation**

Append to `src/orme_lab/ir_contaminant.py`:

```python
# ---- Layer 2: coupled-oscillator model for the top match --------------------
# Two equivalent coupled bond stretches split into symmetric/antisymmetric modes:
#   nu_sym  = 1302.8 * sqrt((k - k')/mu)   (in-phase, lower)
#   nu_asym = 1302.8 * sqrt((k + k')/mu)   (out-of-phase, higher)
# k = bond force constant, k' = interaction constant, mu = one-oscillator reduced mass.
_PHYSICAL_LIGHT_K = (4.0, 18.0)  # representative light-atom stretch envelope (mdyne/A)


def coupled_stretch(k: float, k_int: float, mu: float) -> tuple[float, float]:
    nu_sym = WAVENUMBER_CONST * math.sqrt((k - k_int) / mu)
    nu_asym = WAVENUMBER_CONST * math.sqrt((k + k_int) / mu)
    return (nu_sym, nu_asym)


def back_out_coupling(nu_lo: float, nu_hi: float, mu: float) -> tuple[float, float]:
    a = (nu_hi / WAVENUMBER_CONST) ** 2   # (k + k')/mu
    b = (nu_lo / WAVENUMBER_CONST) ** 2   # (k - k')/mu
    k = mu * (a + b) / 2.0
    k_int = mu * (a - b) / 2.0
    return (k, k_int)


def coupled_model_for(band: ContaminantBand, lines_cm: tuple[float, ...]) -> str:
    if not band.coupled_applicable or band.oscillator_mu is None:
        return (f"Coupled-stretch model N/A for {band.name}: the doublet is not a "
                f"symmetric two-oscillator pair for this species.")
    lo, hi = min(lines_cm), max(lines_cm)
    k, k_int = back_out_coupling(lo, hi, band.oscillator_mu)
    lo_k, hi_k = _PHYSICAL_LIGHT_K
    verdict = "physical" if lo_k <= k <= hi_k else "outside the light-atom envelope"
    return (f"{band.name}: observed doublet implies bond k~{k:.1f} mdyne/A and interaction "
            f"k'~{k_int:.2f} mdyne/A (mu={band.oscillator_mu:.3f} amu) — {verdict} "
            f"[{lo_k:.0f}-{hi_k:.0f}].")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /orme-lab && python -m pytest tests/test_ir_contaminant.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/ir_contaminant.py tests/test_ir_contaminant.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat: coupled-oscillator model backs out k/k' for the top match"
```

---

### Task 6: Web widget + Python↔JS parity

**Files:**
- Modify: `web/patent_tests.js` (extend `irVerdict`, add `CONTAMINANTS` mirror)
- Modify: `tests/test_patent_web_parity.py` (add contaminant-table parity case)

**Interfaces:**
- Consumes: `_CONTAMINANTS` (Python), the JS `irVerdict` function.
- Produces: JS `CONTAMINANTS` array + `contaminantMatch(lo, hi)`; a parity test asserting the JS array equals the Python table row-for-row.

- [ ] **Step 1: Write the failing parity test**

```python
# add to tests/test_patent_web_parity.py
import re
from pathlib import Path
from orme_lab.ir_contaminant import _CONTAMINANTS

_JS = Path(__file__).resolve().parents[1] / "web" / "patent_tests.js"


def _parse_js_contaminants(text: str):
    block = re.search(r"const CONTAMINANTS\s*=\s*\[(.*?)\];", text, re.S).group(1)
    rows = re.findall(r"\{[^}]*\}", block)
    out = {}
    for row in rows:
        name = re.search(r'name:\s*"([^"]+)"', row).group(1)
        # extract ONLY the lo/hi/d array contents (in that document order) so a
        # digit inside a species name like "NO3-" cannot leak into the numbers
        arrs = re.findall(r"(?:lo|hi|d):\s*\[([^\]]*)\]", row)
        nums = [float(x) for arr in arrs for x in arr.split(",") if x.strip()]
        out[name] = nums
    return out


def test_js_contaminant_table_matches_python():
    js = _parse_js_contaminants(_JS.read_text())
    assert len(js) == len(_CONTAMINANTS)
    for b in _CONTAMINANTS:
        assert b.name in js, f"{b.name} missing from JS mirror"
        py_nums = [b.lo_band[0], b.lo_band[1], b.hi_band[0], b.hi_band[1],
                   b.split_band[0], b.split_band[1]]
        assert js[b.name] == pytest.approx(py_nums), f"{b.name} band mismatch"
```

(Ensure `import pytest` is present at the top of the test file.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /orme-lab && python -m pytest tests/test_patent_web_parity.py::test_js_contaminant_table_matches_python -v`
Expected: FAIL — no `CONTAMINANTS` block in `patent_tests.js`.

- [ ] **Step 3: Add the JS mirror + widget line**

In `web/patent_tests.js`, add after the existing constants a `CONTAMINANTS` array with one `{ name, cat, lo:[..], hi:[..], d:[..] }` per Python row (numbers copied verbatim from `_CONTAMINANTS` — six numbers per row in the order lo_min, lo_max, hi_min, hi_max, d_min, d_max), a `contaminantMatch(lines)` function mirroring `screen_contaminants` (same `_band_residual` + total-key sort + verdict tiers), and extend `irVerdict(sym, hi)` to append the top contaminant match beneath the exclusion line. Keep it a pure string-returning function; no new DOM inputs required (reuse the existing `pwIrLine` upper-line input and pair it with the patent's lower line for the same metal, or add a lower-line input — implementer's choice, but the parity test only pins the table).

Concretely, the JS scoring mirror:

```javascript
const CONTAMINANTS = [
  // numbers copied verbatim from _CONTAMINANTS (Python is authoritative; parity test pins this)
  { name: "nitrate NO3-", cat: "route_derived", lo: [/*..*/], hi: [/*..*/], d: [/*..*/] },
  // ... one row per surviving candidate ...
];
const CAT_RANK = { route_derived: 0, standard: 1 };
const bandResidual = (x, [lo, hi]) => (x >= lo && x <= hi) ? 0 : (x < lo ? (lo - x) / ((hi - lo) || 1) : (x - hi) / ((hi - lo) || 1));
function contaminantMatch(lo, hi) {
  const split = hi - lo;
  const scored = CONTAMINANTS
    .map((b) => [b, bandResidual(lo, b.lo) + bandResidual(hi, b.hi) + bandResidual(split, b.d)])
    .sort((a, z) => a[1] - z[1] || CAT_RANK[a[0].cat] - CAT_RANK[z[0].cat] || a[0].name.localeCompare(z[0].name));
  const [top, s] = scored[0];
  const tight = bandResidual(lo, top.lo) === 0 && bandResidual(hi, top.hi) === 0 && bandResidual(split, top.d) === 0;
  const v = tight ? "tight match" : (s <= 1.0 ? "plausible match" : "unmatched");
  return `closest contaminant: ${top.name} (${v}, residual ${s.toFixed(2)}).`;
}
```

- [ ] **Step 4: Run parity + existing web tests to verify pass**

Run: `cd /orme-lab && python -m pytest tests/test_patent_web_parity.py -v`
Expected: PASS (existing constant-parity cases + new table-parity case).

- [ ] **Step 5: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add web/patent_tests.js tests/test_patent_web_parity.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(web): IR widget shows top contaminant match; table pinned to Python"
```

---

### Task 7: Findings write-up (authored after running)

**Files:**
- Modify: `docs/patent-claim-tests.md` (append a contaminant-control section)

**Interfaces:**
- Consumes: the running screens (`screen_contaminants`, `coupled_model_for`).

- [ ] **Step 1: Run the screens and capture actual output**

Run:
```bash
cd /orme-lab && python -c "
from orme_lab.ir_contaminant import screen_contaminants, coupled_model_for, _CONTAMINANTS
for lines in ((1429.53, 1490.99), (1432.09, 1495.17)):
    r = screen_contaminants(lines)
    print(lines, '->', r.verdict)
    print(r.explain())
    top = next(b for b in _CONTAMINANTS if b.name == r.ranked[0][0])
    print(coupled_model_for(top, lines))
    print('ranked:', r.ranked)
    print()
"
```

- [ ] **Step 2: Write the findings section**

Append a "IR-doublet contaminant control" section to `docs/patent-claim-tests.md` recording the **actual** verdict, ranking, and coupled-oscillator k/k′ for each patent doublet as printed in Step 1 — no pre-judged outcome. State plainly what the screen found (tight/plausible/unmatched, which species, whether the implied force constants are physical) and reiterate the Level ≤ 2 triage framing and the `unmatched`-is-possible caveat.

- [ ] **Step 3: Full suite green**

Run: `cd /orme-lab && python -m pytest -q`
Expected: PASS (all prior 226 + the new `test_ir_contaminant.py` + the new parity case).

- [ ] **Step 4: Commit**

```bash
cd /orme-lab
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add docs/patent-claim-tests.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "docs: IR-doublet contaminant-control findings (actual ranked result)"
```

---

## Final: open PR (do not merge)

```bash
cd /orme-lab
git push -u origin ir-contaminant-control
BODY="Positive leg for the patent IR-doublet screen: cited contaminant reference library + ranked match, coupled-oscillator model for the top match, live web widget pinned to Python by parity test. Band values sourced (Nakamoto/Socrates/NIST) and citation-audited before entry. Triage only — evidence Level <= 2; screen provably able to return 'unmatched'. Findings in docs/patent-claim-tests.md."
gh pr create -R Dezirae-Stark/orme-lab --base master --head ir-contaminant-control \
  --title "IR-doublet contaminant control (positive leg)" --body "$BODY"
```

Report the PR URL to the operator; do not merge — repository/merge decisions are operator-reserved.
