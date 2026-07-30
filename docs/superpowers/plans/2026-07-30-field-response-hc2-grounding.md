# Heavy-fermion Hc2/Pauli-limit grounding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ground the existing field-response discriminator in heavy-fermion Hc2/Pauli-limit methodology — R_Pauli = Hc2(0)/Bp, Maki parameter, clean-limit admissibility gate; a cited benchmark table (CeSiI template, all six verified); enrich the triplet decisive-measurement (Level-3 handoff). No new hypothesis; sharpens the proxy without raising evidence level (Level 2).

**Architecture:** Enriches `magnetic_field.py` (adds R_Pauli/Maki/clean-limit alongside the existing `field_response_ratio`, which stays for the pairing-branch wiring), threads optional Borb/clean-limit inputs through `pipeline.py`/`config.py`, adds a cited `field_response_refs.py` data module (calibration + CeSiI anchor, NEVER a PGM score), and enriches the existing `validator._mech_test(Mechanism.TRIPLET)` `AdversarialTest` + the `H7-triplet` web card. Reconciliations from the map: there is no "SAC-stack Method 5" (attach to `validator.py`), "the Ledger" for CeSiI is the new refs module (not `lab_loop/ledger.py`), and the "Baskaran anchor" is recorded as explicitly-conceptual framing with NO fabricated citation.

**Tech Stack:** Python 3 (stdlib: `math`, `dataclasses`), pytest, vanilla JS (`web/hypotheses.js`), node parity test.

## Global Constraints

- No `VALIDATED` verdict member. **A grounded threshold stays Level 2** — it does not raise the evidence level anywhere.
- Anti-tautology gate preserved: `field_response_ratio` stays off-gate; no `GATE_INPUT_CLOSURE` change.
- Default path byte-identical: new inputs (`b_orb_tesla`, `is_clean_limit`) default `None`; with them absent every existing `CandidateRecord` field + metric is unchanged.
- **Reference table NEVER adds a score to a PGM candidate** — calibration/anchor only (golden test).
- **R_Pauli > 1 is *consistent-with* triplet, not *proof*** — one signature inside the AND-gate; and it is registrable as an unconventional signature ONLY in the clean limit (`clean_limit_admits_unconventional`). A dirty/unknown candidate cannot register it regardless of R_Pauli.
- Heavy-fermion refs are methodology/template ONLY, never PGM-SAC evidence. CeSiI anchor carries verbatim not-PGM/cryogenic/not-evidence scoping.
- **No fabricated citations.** The six benchmarks are audit-verified (`~/.claude/research-wiki/prior-art/heavy-fermion-hc2-pauli-limit.md`); CeSiI pressure = 6/7 GPa; the 1.86 coefficient = Clogston/Chandrasekhar 1962. NO Baskaran citation is encoded (conceptual framing only).
- Determinism; commit as `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`; no AI trailers. Branch `field-response-hc2-grounding`. Tests: `cd /orme-lab && python3 -m pytest`.

---

### Task 1: R_Pauli, Maki parameter, clean-limit gate (`magnetic_field.py`)

**Files:** Modify `src/orme_lab/magnetic_field.py`; Test `tests/test_pairing_symmetry.py`.

- [ ] **Step 1: Failing tests** (mirror the existing `test_pauli_limit_is_1_86_tc` style):
```python
def test_pauli_violation_ratio():
    from orme_lab.magnetic_field import pauli_violation_ratio
    assert pauli_violation_ratio(18.6, 10.0) == pytest.approx(1.0)   # Hc2 == Bp -> R=1
    assert pauli_violation_ratio(37.2, 10.0) == pytest.approx(2.0)   # 2x Pauli -> unconventional
    assert pauli_violation_ratio(5.0, None) is None                  # no Tc -> prediction, not a number


def test_maki_alpha():
    from orme_lab.magnetic_field import maki_alpha
    import math
    assert maki_alpha(20.0, 10.0) == pytest.approx(math.sqrt(2) * 2.0)
    assert maki_alpha(None, 10.0) is None


def test_clean_limit_gates_unconventional():
    from orme_lab.magnetic_field import clean_limit_admits_unconventional
    assert clean_limit_admits_unconventional(5.0, True) is True     # alpha>=1.8 AND clean
    assert clean_limit_admits_unconventional(5.0, False) is False   # dirty -> not admissible
    assert clean_limit_admits_unconventional(1.0, True) is False    # alpha<1.8 -> not admissible
    assert clean_limit_admits_unconventional(None, True) is False   # unknown -> conservative
```
- [ ] **Step 2: Run → FAIL** (`python3 -m pytest tests/test_pairing_symmetry.py -k "pauli_violation or maki or clean_limit" -v`).
- [ ] **Step 3: Implement** in `magnetic_field.py` (after `pauli_limit_tesla`):
```python
MAKI_FFLO_MIN = 1.8   # Maki parameter above which paramagnetically-limited FFLO / unconventional
                      # signatures become admissible (standard threshold; clean limit required).


def pauli_violation_ratio(hc2_0_tesla: float, tc_kelvin: float | None) -> float | None:
    """R_Pauli = Hc2(0) / Bp, Bp = 1.86*Tc (Clogston PRL 9,266 1962 / Chandrasekhar APL 1,7 1962).
    Core field-response quantity. R_Pauli <= 1: consistent with singlet / Pauli-limited.
    R_Pauli > 1: unconventional / equal-spin-triplet SIGNATURE (admissible only in the clean limit,
    see clean_limit_admits_unconventional). None when Tc unknown (toy path) -> a decisive-measurement
    PREDICTION, not a computed score. Model proxy, Level 2."""
    if tc_kelvin is None or tc_kelvin <= 0.0:
        return None
    return hc2_0_tesla / pauli_limit_tesla(tc_kelvin)


def maki_alpha(b_orb_tesla: float | None, bp_tesla: float | None) -> float | None:
    """Maki parameter alpha = sqrt(2) * Borb / Bp (orbital vs paramagnetic pair-breaking).
    None if either field is unknown. Model proxy, Level 2."""
    if b_orb_tesla is None or bp_tesla is None or bp_tesla <= 0.0:
        return None
    return math.sqrt(2.0) * b_orb_tesla / bp_tesla


def clean_limit_admits_unconventional(alpha: float | None, is_clean: bool | None) -> bool:
    """An FFLO / paramagnetically-limited unconventional signature is admissible ONLY in the clean
    limit (mean free path >~ coherence length) with a large Maki parameter (alpha >= MAKI_FFLO_MIN).
    Unknown inputs -> NOT admissible (conservative): absence of evidence cannot register an
    unconventional signature (Maki 1966; usage per CeCoIn5/LiFeAs literature)."""
    return alpha is not None and is_clean is True and alpha >= MAKI_FFLO_MIN
```
Also update the `pauli_limit_tesla` docstring/`PAULI_SLOPE_T_PER_K` comment to credit **Clogston 1962 / Chandrasekhar 1962** for the 1.86 coefficient (Schossmann-Carbotte PRB 39,4210 1989 for the general Hc2 theory).
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: R_Pauli + Maki parameter + clean-limit admissibility gate (magnetic_field)`.

---

### Task 2: thread Borb / clean-limit inputs + admissibility through the pipeline

**Files:** Modify `src/orme_lab/config.py`, `src/orme_lab/pipeline.py`; Test `tests/test_pairing_symmetry.py`.

**Interfaces:** `LabConfig.b_orb_tesla: float | None = None`, `LabConfig.is_clean_limit: bool | None = None`; `CandidateRecord.b_orb_tesla: float | None = None`, `is_clean_limit: bool | None = None`, `unconventional_admissible: bool = False`.

- [ ] **Step 1: Failing tests:**
```python
def test_unconventional_admissible_gated_by_clean_limit():
    from dataclasses import replace
    from orme_lab.config import DEFAULT_CONFIG
    from orme_lab.pipeline import evaluate_candidate
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    el = get_element("Ir"); geo = make_compact_cluster(el, 13); st = high_spin_state(el)
    # default: no Borb/clean-limit -> not admissible, byte-identical extras None
    d = evaluate_candidate(el, geo, "high_spin", st, DEFAULT_CONFIG)
    assert d.b_orb_tesla is None and d.is_clean_limit is None and d.unconventional_admissible is False
    # dirty limit -> cannot register unconventional even with a huge Borb
    dirty = evaluate_candidate(el, geo, "high_spin", st,
              replace(DEFAULT_CONFIG, b_orb_tesla=200.0, is_clean_limit=False))
    assert dirty.unconventional_admissible is False
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** `config.py`: add the two `LabConfig` fields (default None). `pipeline.py`: add the three `CandidateRecord` fields (defaults keep toy path byte-identical). In `evaluate_candidate`, after `fr_ratio` is computed (`pipeline.py:286`), compute:
```python
    from .magnetic_field import maki_alpha, clean_limit_admits_unconventional, pauli_limit_tesla
    _bp = pauli_limit_tesla(epw.tc_kelvin) if epw.tc_kelvin else None
    _alpha = maki_alpha(config.b_orb_tesla, _bp)
    unconventional_admissible = (
        fr_ratio is not None and fr_ratio > 1.0
        and clean_limit_admits_unconventional(_alpha, config.is_clean_limit))
```
Pass `b_orb_tesla=config.b_orb_tesla, is_clean_limit=config.is_clean_limit, unconventional_admissible=unconventional_admissible` into the `CandidateRecord(...)` constructor. (This is the clean-limit gate: R_Pauli>1 alone never registers unconventional — only R_Pauli>1 AND clean-admissible does. Absent inputs → False, conservative, byte-identical.)
- [ ] **Step 4: Run → PASS**, full suite (default byte-identical).
- [ ] **Step 5: Commit** `feat: thread Borb/clean-limit inputs + unconventional-admissibility gate through the screen`.

---

### Task 3: cited benchmark table + CeSiI anchor (`field_response_refs.py`)

**Files:** Create `src/orme_lab/field_response_refs.py`; Test `tests/test_field_response_refs.py`.

**Interfaces:** `FieldResponseBenchmark` frozen dataclass; `BENCHMARKS: tuple[...]`; `CESII_ANCHOR` record; `classifies_correctly(b) -> bool`.

- [ ] **Step 1: Failing tests:**
```python
# tests/test_field_response_refs.py
from orme_lab.field_response_refs import BENCHMARKS, CESII_ANCHOR, classifies_correctly


def test_all_benchmarks_classify_on_correct_side_of_pauli_boundary():
    # calibration: unconventional rows have R_Pauli>1, the Pauli-limited benchmark <=1
    assert len(BENCHMARKS) == 6
    for b in BENCHMARKS:
        assert classifies_correctly(b), f"{b.material} misclassified at R_Pauli=1"
    unconv = [b for b in BENCHMARKS if b.pairing_class == "unconventional"]
    pauli = [b for b in BENCHMARKS if b.pairing_class == "Pauli-limited"]
    assert unconv and pauli
    assert all(b.r_pauli > 1.0 for b in unconv)
    assert all(b.r_pauli <= 1.0 for b in pauli)


def test_every_benchmark_cites_a_source():
    for b in BENCHMARKS:
        assert b.citation and ("DOI" in b.citation or "PRL" in b.citation or "PRB" in b.citation
                               or "Science" in b.citation or "Nat" in b.citation)


def test_cesii_anchor_honest_scoping():
    t = CESII_ANCHOR.scoping.lower()
    assert "not" in t and "pgm" in t                # NOT a PGM system
    assert "not evidence" in t or "not a" in t       # not evidence for the ORME premise
    assert "240" in CESII_ANCHOR.conditions          # ~240 mK
    assert "gpa" in CESII_ANCHOR.conditions.lower()  # 6/7 GPa


def test_refs_never_score_a_pgm_candidate():
    # guardrail: the module exposes ONLY reference data + a classifier; no function takes or
    # returns a PGM CandidateRecord / score.
    import orme_lab.field_response_refs as m
    assert not hasattr(m, "score_candidate")
    for name in dir(m):
        obj = getattr(m, name)
        assert "CandidateRecord" not in getattr(obj, "__doc__", "" ) if callable(obj) else True
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** `field_response_refs.py` (cited-data-module pattern, like `ir_contaminant.py`):
```python
"""Heavy-fermion Hc2 / Pauli-limit benchmark references — calibration anchors for the field-response
discriminator's R_Pauli=1 singlet/unconventional boundary. GROUNDING ONLY: these are real external
superconductors used to document where the boundary sits; they NEVER contribute a score to any PGM
candidate. All citations audit-verified (research-wiki/prior-art/heavy-fermion-hc2-pauli-limit.md).
Level 2 — a grounded threshold is not a raised evidence level."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldResponseBenchmark:
    material: str
    r_pauli: float                 # published Hc2(0)/Bp (representative)
    clean: bool
    pairing_class: str             # "unconventional" | "Pauli-limited"
    citation: str


BENCHMARKS: "tuple[FieldResponseBenchmark, ...]" = (
    FieldResponseBenchmark("CeSiI", 5.5, True, "unconventional",
        "Shi, Cheng et al., Nat. Phys. (2026), DOI 10.1038/s41567-026-03392-3 — Hc2 4-7x Pauli, "
        "6 GPa dome / 7 GPa QCP, Tc~240 mK [TEMPLATE]"),
    FieldResponseBenchmark("CeSb2 (high-p)", 8.0, True, "unconventional",
        "Squire et al., PRL 131, 026001 (2023) — ~8x Pauli limit"),
    FieldResponseBenchmark("CeCoIn5", 5.0, True, "unconventional",
        "Miclea et al., PRL 96, 117001 (2006) — FFLO, clean, alpha~5"),
    FieldResponseBenchmark("CeRh2As2", 4.0, True, "unconventional",
        "Khim et al., Science 373, 1012 (2021), DOI 10.1126/science.abe7518 — field-induced SC transition"),
    FieldResponseBenchmark("LiFeAs", 0.9, True, "Pauli-limited",
        "Khim et al., PRB 84, 104502 (2011) — clean, Pauli-limited benchmark"),
    # theory anchor row (Pauli-limited reference behaviour; coefficient origin cited)
    FieldResponseBenchmark("BCS Pauli limit (theory)", 1.0, True, "Pauli-limited",
        "Clogston PRL 9,266 (1962) / Chandrasekhar APL 1,7 (1962); general Hc2 theory "
        "Schossmann & Carbotte PRB 39, 4210 (1989)"),
)


@dataclass(frozen=True)
class MethodologyAnchor:
    material: str
    conditions: str
    concept: str
    scoping: str
    citation: str


CESII_ANCHOR = MethodologyAnchor(
    material="CeSiI",
    conditions="Ce 4f heavy-fermion; pressure-tuned QCP; ~240 mK; 6 GPa (SC dome max) / 7 GPa (QCP)",
    concept=("superconductivity emerges when antiferromagnetic order is suppressed at a pressure-tuned "
             "quantum critical point — the peer-reviewed, cryogenic form of the 'latent SC deconfined "
             "by a perturbation' conceptual template (NO specific Baskaran citation is encoded here; "
             "recorded as a conceptual framing pending verification)"),
    scoping=("METHODOLOGY / CONCEPTUAL-TEMPLATE REFERENCE ONLY. NOT a PGM single-atom system, NOT room "
             "temperature, NOT evidence for the ORME premise — a different material class (Ce 4f) at "
             "millikelvin under GPa pressure. Used to calibrate the Hc2/Pauli-limit discriminator and "
             "seed its decisive-measurement spec, never to score a PGM candidate."),
    citation="Shi, Cheng et al., Nat. Phys. (2026), DOI 10.1038/s41567-026-03392-3",
)


def classifies_correctly(b: "FieldResponseBenchmark") -> bool:
    """The R_Pauli=1 boundary: unconventional rows sit above 1, Pauli-limited at/below 1."""
    return (b.r_pauli > 1.0) == (b.pairing_class == "unconventional")
```
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: cited heavy-fermion Hc2/Pauli benchmark table + CeSiI methodology anchor (grounding only)`.

---

### Task 4: enrich the triplet decisive-measurement (validator.py + web card)

**Files:** Modify `src/orme_lab/validator.py`, `web/hypotheses.js`; Test `tests/test_validator.py`, `tests/test_web_pairing_parity.py`.

- [ ] **Step 1: Failing tests:**
```python
# add to tests/test_validator.py
def test_triplet_test_names_r_pauli_and_companions():
    from orme_lab.validator import _mech_test
    from orme_lab.mechanisms import Mechanism
    t = _mech_test(Mechanism.TRIPLET.value)
    blob = (t.measurement + t.claimed_signature + t.rejection_threshold + t.note).lower()
    assert "pauli" in blob and "r_pauli" in blob            # R_Pauli = Hc2(0)/Bp named
    assert "non-fermi" in blob or "n < 2" in blob or "effective-mass" in blob  # QC companions
    assert "method 5" in blob                                # descriptive SAC label
    assert t.evidence_level == 3                             # LABORATORY_PREDICTION
```
```python
# add to tests/test_web_pairing_parity.py
def test_h7_triplet_card_names_r_pauli_and_clean_limit():
    js = (_WEB / "hypotheses.js").read_text()
    # the H7-triplet decisive measurement now names R_Pauli and the clean-limit admissibility
    assert "R_Pauli" in js and ("clean limit" in js or "clean-limit" in js)
```
(`_WEB` per the existing parity test's path constant.)
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement.** In `validator.py` `_mech_test`, enrich the `Mechanism.TRIPLET` branch (keep the `_test(...)` shape) so measurement/claimed/rejection/note explicitly name **R_Pauli = Hc2(0)/Bp**, add the quantum-critical companions (NFL resistivity exponent n<2, effective-mass enhancement near the magnetic instability) as corroborating off-gate evidence, note the clean-limit admissibility (α≳1.8, clean), the falsification (R_Pauli≤1 Pauli-limited ⇒ against triplet; R_Pauli>1 clean ⇒ consistent-with), and a "Method 5 (Hc2-vs-Pauli-limit)" descriptive label in `note` (NOT a new numbered enumeration). It already carries `evidence_level=_LAB_PRED (3)` via `_test`. In `web/hypotheses.js`, extend the `H7-triplet` card's `test:` string to name **R_Pauli = Hc2(0)/Bp**, the clean-limit admissibility, and the NFL/effective-mass companions (mirror the Python enrichment).
- [ ] **Step 4: Run → PASS**, full suite (incl. parity).
- [ ] **Step 5: Commit** `feat: enrich triplet decisive-measurement with R_Pauli + QC companions (SAC Method 5); mirror on H7-triplet card`.

---

### Task 5: acceptance contract + changelog

**Files:** Create `tests/test_field_response_grounding_acceptance.py`; Modify the design spec (Result note) / add a CHANGELOG note in `docs/`.

- [ ] **Step 1: Acceptance tests** (one per spec criterion): R_Pauli≤1 scores toward singlet / R_Pauli>1 clean toward unconventional matching the benchmark table; clean-limit gate actually gates (dirty ⇒ not admissible regardless of R_Pauli — reuse Task 2); discriminator can worsen standing (a Pauli-limited high-spin candidate scores against triplet on the field axis); field-response stays off-gate (`is_independent(("field_response_ratio",))`); decisive-measurement block emitted with falsification + companions (via `_mech_test(TRIPLET)`); no `VALIDATED`, Level-2 everywhere, CeSiI anchor scoping present; the refs module never scores a PGM candidate (reuse Task 3 guardrail).
- [ ] **Step 2: Run** `python3 -m pytest -q` (full suite green).
- [ ] **Step 3:** Append a CHANGELOG/Result note to the design spec: what was grounded (field-response thresholds anchored to heavy-fermion Hc2/Pauli literature, CeSiI template, all six verified; R_Pauli/Maki/clean-limit; Level-3 decisive-measurement handoff), why, and the invariant confirmation (no weakening, no level raise, no new hypothesis, no positive score term, Baskaran recorded as conceptual framing not a fabricated citation).
- [ ] **Step 4: Commit** `test: field-response grounding acceptance contract + changelog`.

---

## Final: open PR (do not merge)

```bash
cd /orme-lab
git push -u origin field-response-hc2-grounding
BODY="Grounds the field-response (singlet/triplet) discriminator in the heavy-fermion Hc2/Pauli-limit methodology. Adds R_Pauli = Hc2(0)/Bp, the Maki parameter alpha = sqrt(2)*Borb/Bp, and a clean-limit admissibility gate (unconventional/FFLO signature registrable ONLY when alpha>=1.8 AND clean; dirty/unknown -> conservative non-registration). A cited benchmark table (field_response_refs.py) with CeSiI (Nat. Phys. 2026, DOI 10.1038/s41567-026-03392-3) as the template calibrates the R_Pauli=1 boundary and NEVER scores a PGM candidate. The triplet decisive-measurement (validator.py + H7-triplet card) is enriched with R_Pauli + quantum-critical companions (NFL exponent n<2, effective-mass enhancement) as the Level-3 handoff ('Method 5, Hc2-vs-Pauli-limit'). CeSiI logged as a methodology anchor with explicit not-PGM / ~240 mK / 6-7 GPa / not-evidence scoping. All six citations audit-verified (CeSiI 6/7 GPa correction; 1.86 coefficient -> Clogston/Chandrasekhar 1962); NO Baskaran citation encoded (conceptual framing only). Invariants: no new hypothesis, no positive score term, Level 2 (grounded threshold != raised level), anti-tautology preserved, default path byte-identical. Do not merge without operator review."
gh pr create -R Dezirae-Stark/orme-lab --base master --head field-response-hc2-grounding \
  --title "Ground the field-response discriminator in heavy-fermion Hc2/Pauli-limit methodology" --body "$BODY"
```
Report the PR URL; do not merge — operator-reserved.
