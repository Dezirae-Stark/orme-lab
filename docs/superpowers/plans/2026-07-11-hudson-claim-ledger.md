# Hudson Claim Ledger Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Hudson Claim Ledger — a falsify-first, reporting-only layer above the pipeline that assesses Hudson's eight ORME claims, computes the six named gates, and reports two roll-ups (claim-level best-of, integrated weakest-link-within-lineage) without ever assembling a successful theory from unrelated specimens or emitting "VALIDATED".

**Architecture:** A new `hudson_ledger.py` consuming existing gates/screens (`identity`, `structure`, `hudson_optical`/`branch_verdict`, `mechanisms`, `meissner_field`, `ir_contaminant`/`control_experiment`, `validator`) plus a new `lineage.py` provenance type. Everything is pure/deterministic and read-only over `CandidateRecord`s. Extraordinary claims (transport/magnetism/replication) are default-blocked: absent measured evidence the ledger emits Level-3 decisive-experiment designs, never a computed pass. See `docs/superpowers/specs/2026-07-11-hudson-claim-ledger-design.md`.

**Tech Stack:** Python 3, stdlib only (`enum`, `dataclasses`, `math`), pytest. No new dependencies. `identity.py`, the SC gate, and Branch B are NOT modified — the ledger is strictly a consuming layer.

## Global Constraints

Every task's requirements implicitly include this section.

- **Falsify-first / no Frankenstein validation.** The integrated Hudson state may be credited only when ONE materially continuous lineage satisfies the core conjunction. The integrated roll-up is `max_lineage( min_claim S )` — NEVER `min_claim( max_candidate S )`. The ledger must not compute the latter.
- **Default-block extraordinary claims.** Transport, magnetism, and replication sub-gates are `False`/unestablished without measured evidence. The simulation never self-asserts `g_hudson_mechanism` or `g_conventional_superconductivity`.
- **`credited_sc_lead` → LEAD, never SUPPORTED.** A simulation lead is promising evidence, not support. HC-07 is `supported` only when measured evidence clears the preregistered gate.
- **Never "VALIDATED".** The ledger must never emit the string "HUDSON CLAIM VALIDATED" under any input. The strongest terminal verdict is `independent-replication-achieved`.
- **Identity split.** `identity.py` is left untouched (it gates Branch-A crediting with `phase == "metallic"`). The ledger computes `G_identity_established` (phase-agnostic) and `G_hudson_material_state` (HC-01 nonmetallic-elemental ∧ HC-02 dispersed) fresh from the same `IdentityWitness` + `StructuralDistribution`.
- **Evidence ceilings.** Simulation-produced `evidence_level` ≤ 2 (LAB_CEILING). Decisive designs = 3. L4 only as measured `evidence_level_if_confirmed`; L5 only from external replication metadata.
- **Determinism.** No `time.time()`, no unseeded RNG, no order-dependent iteration. Claims emit in fixed HC order; lineage grouping is sorted.
- **No web/network.** Python-only, loopback only. No fabricated citations.
- **Commits.** Author as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`. NEVER emit AI-identity trailers (`Co-Authored-By:`, `Signed-off-by:`, `Claude-Session:`) in the author, committer, message body, or any PR body.

---

## File Structure

- `src/orme_lab/lineage.py` **(create)** — `IntegrationLevel`, `MaterialLineage`, `singleton_lineage`, `lineage_key`, `group_by_lineage`, `after_treatment`.
- `src/orme_lab/hudson_ledger.py` **(create)** — enums, `ClaimRecord`, `ReplicationEvidence`, `MeasuredEvidence`, the six gates, the eight per-claim assessors, the two roll-ups, `evaluate_hudson_ledger`, `HudsonLedger`.
- `src/orme_lab/config.py` **(modify)** — HC-02 policy thresholds + replication minima.
- `docs/hudson_claim_ledger.md` **(create)** — the claim table, gate semantics, roll-up formulas, default-blocks.
- `tests/test_lineage.py`, `tests/test_hudson_ledger.py` **(create)**.

---

### Task 1: Lineage / provenance model

**Files:** Create `src/orme_lab/lineage.py`; Test `tests/test_lineage.py`.

**Interfaces:**
- Produces: `IntegrationLevel(IntEnum)` {SAME_SPECIMEN=3, SAME_BATCH=2, SAME_LINEAGE=1, NONE=0}; `MaterialLineage(frozen)` (material_family_id, preparation_batch_id, aliquot_id, processing_history: tuple[str,...], characterization_fingerprint: str, integration_level: IntegrationLevel); `singleton_lineage(candidate_id) -> MaterialLineage`; `lineage_key(lin) -> str` (batch-level: family/batch); `group_by_lineage(items: tuple[tuple[MaterialLineage, object],...]) -> dict[str, list]` (sorted keys); `after_treatment(lin, treatment, fingerprint) -> MaterialLineage`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_lineage.py`:

```python
"""Tests for the material-lineage / provenance model."""
from __future__ import annotations

from orme_lab.lineage import (
    IntegrationLevel,
    MaterialLineage,
    after_treatment,
    group_by_lineage,
    lineage_key,
    singleton_lineage,
)


def test_singleton_lineage_is_its_own_family_batch_aliquot():
    lin = singleton_lineage("Ir/compact13/high_spin")
    assert lin.material_family_id == lin.preparation_batch_id == lin.aliquot_id == "Ir/compact13/high_spin"
    assert lin.integration_level is IntegrationLevel.SAME_SPECIMEN
    assert lin.processing_history == ()


def test_group_by_lineage_groups_aliquots_of_one_batch():
    a = MaterialLineage("famA", "batch1", "aliquot1", (), "fpA", IntegrationLevel.SAME_BATCH)
    b = MaterialLineage("famA", "batch1", "aliquot2", (), "fpA", IntegrationLevel.SAME_BATCH)
    c = MaterialLineage("famA", "batch2", "aliquot3", (), "fpB", IntegrationLevel.SAME_BATCH)
    groups = group_by_lineage(((a, "x"), (b, "y"), (c, "z")))
    assert groups["famA/batch1"] == ["x", "y"]      # same batch grouped
    assert groups["famA/batch2"] == ["z"]           # different batch separate
    assert list(groups.keys()) == sorted(groups.keys())   # deterministic order


def test_after_treatment_appends_history_and_is_a_new_state():
    lin = singleton_lineage("Ir/mono/hs")
    treated = after_treatment(lin, "anneal-600C", "fp-annealed")
    assert treated.processing_history == ("anneal-600C",)
    assert treated.characterization_fingerprint == "fp-annealed"
    assert lin.processing_history == ()             # original unchanged (frozen)
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_lineage.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.lineage'`.

- [ ] **Step 3: Implement**

Create `src/orme_lab/lineage.py`:

```python
"""Material lineage / provenance for the Hudson Claim Ledger.

A claim observed on a specimen attaches to a MATERIAL STATE, not automatically to the
precursor: after annealing / hydration / irradiation / field treatment the resulting state
is a new lineage node (a new processing_history entry + fingerprint). Integrated Hudson
evidence must come from ONE lineage (same specimen > same batch > same lineage), never from
unrelated specimens. At pure-simulation level each computational candidate is its own
singleton lineage; real lab evidence carries explicit IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum


class IntegrationLevel(IntEnum):
    """Strength of the same-material claim, strongest first."""
    SAME_SPECIMEN = 3   # the exact physical aliquot received every test
    SAME_BATCH = 2      # aliquots of one homogeneous batch (minimum for integrated evidence)
    SAME_LINEAGE = 1    # independent batches, same recipe, matching fingerprints
    NONE = 0            # unrelated / unknown


@dataclass(frozen=True)
class MaterialLineage:
    material_family_id: str
    preparation_batch_id: str
    aliquot_id: str
    processing_history: tuple[str, ...] = ()
    characterization_fingerprint: str = ""
    integration_level: IntegrationLevel = IntegrationLevel.SAME_SPECIMEN


def singleton_lineage(candidate_id: str) -> MaterialLineage:
    """A computational candidate is its own singleton lineage (family = batch = aliquot)."""
    return MaterialLineage(candidate_id, candidate_id, candidate_id, (),
                           candidate_id, IntegrationLevel.SAME_SPECIMEN)


def lineage_key(lin: MaterialLineage) -> str:
    """Batch-level grouping key (the minimum acceptable for integrated evidence)."""
    return f"{lin.material_family_id}/{lin.preparation_batch_id}"


def group_by_lineage(items: tuple[tuple[MaterialLineage, object], ...]) -> dict[str, list]:
    """Group (lineage, payload) pairs by batch-level key. Deterministic (sorted keys)."""
    groups: dict[str, list] = {}
    for lin, payload in items:
        groups.setdefault(lineage_key(lin), []).append(payload)
    return dict(sorted(groups.items()))


def after_treatment(lin: MaterialLineage, treatment: str, fingerprint: str) -> MaterialLineage:
    """The resulting material state after a treatment: a NEW lineage node with the treatment
    appended to processing_history and an updated fingerprint. The original is unchanged."""
    return replace(lin, processing_history=lin.processing_history + (treatment,),
                   characterization_fingerprint=fingerprint)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_lineage.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/lineage.py tests/test_lineage.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): material lineage / provenance model"
```

---

### Task 2: Ledger foundation — enums, records, config thresholds

**Files:** Create `src/orme_lab/hudson_ledger.py`; Modify `src/orme_lab/config.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: nothing new.
- Produces: `HudsonClaimId(str, Enum)` HC_01..HC_08; `ClaimStatus(IntEnum)` CANDIDATE=0<LEAD=1<ANOMALOUS=2<PROVISIONALLY_SUPPORTED=3<SUPPORTED=4<INDEPENDENTLY_REPLICATED=5; `Route(str, Enum)` CONVENTIONAL/OPTICAL/NONE; `ClaimRecord(frozen)`; `ReplicationEvidence(frozen)`; `MeasuredEvidence(frozen)`. `ModelThresholds` gains `hudson_hc02_min_isolated_fraction`, `hudson_hc02_max_clustered_fraction`, `hudson_hc02_cluster_margin`, `hudson_hc02_pgm_pgm_tolerance`, `hudson_hc02_bond_length_ang`, `hudson_replication_min_batches`, `hudson_replication_min_labs`.

- [ ] **Step 1: Add config thresholds**

In `config.py` `ModelThresholds`, after the Branch-B block, add:

```python
    # --- Hudson Claim Ledger (HC-02 dispersion policy + replication minima) -----
    hudson_hc02_min_isolated_fraction: float = 0.85   # f_single floor for "atomically dispersed"
    hudson_hc02_max_clustered_fraction: float = 0.20  # upper-bound cap on the clustered fraction
    hudson_hc02_cluster_margin: float = 0.05          # uncertainty margin added to clustered fraction
    hudson_hc02_pgm_pgm_tolerance: float = 0.15       # max fraction with a real PGM-PGM bond
    hudson_hc02_bond_length_ang: float = 3.2          # nn distance at/below this = a PGM-PGM bond
    hudson_replication_min_batches: int = 3           # G_replication: >= 3 independent batches
    hudson_replication_min_labs: int = 2              # G_replication: > 1 lab
```

- [ ] **Step 2: Write the failing test**

Create `tests/test_hudson_ledger.py`:

```python
"""Tests for the Hudson Claim Ledger."""
from __future__ import annotations

from orme_lab.hudson_ledger import (
    ClaimRecord,
    ClaimStatus,
    HudsonClaimId,
    MeasuredEvidence,
    ReplicationEvidence,
    Route,
)


def test_status_ladder_is_ordered():
    assert ClaimStatus.CANDIDATE < ClaimStatus.LEAD < ClaimStatus.SUPPORTED < ClaimStatus.INDEPENDENTLY_REPLICATED


def test_claim_ids_cover_all_eight():
    assert [c.value for c in HudsonClaimId] == [f"HC-0{i}" for i in range(1, 9)]


def test_records_construct():
    r = ClaimRecord(HudsonClaimId.HC_07, "superconductivity", "R->0 + magnetic + thermo",
                    "ionic/percolation/artifact", ClaimStatus.LEAD, 2, Route.CONVENTIONAL, True, None, "note")
    assert r.status is ClaimStatus.LEAD and r.route is Route.CONVENTIONAL
    rep = ReplicationEvidence(3, 2, True, True, True)
    assert rep.n_batches == 3
    m = MeasuredEvidence()
    assert m.zero_resistance is False and m.optical_result is None
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ModuleNotFoundError`.

- [ ] **Step 4: Implement**

Create `src/orme_lab/hudson_ledger.py`:

```python
"""Hudson Claim Ledger — falsify-first assessment of Hudson's eight ORME claims.

A REPORTING layer above the per-candidate pipeline (not a gate inside the SC AND-gate or its
closure oracle; distinct from lab_loop/ledger.py, the experiment ledger). Objective: determine
whether a reproducible material state exists that satisfies Hudson's stated properties —
attacking the ordinary explanation of each claim first. Extraordinary claims are default-blocked;
the ledger never self-asserts the Hudson mechanism from simulation and never emits "VALIDATED".
See docs/hudson_claim_ledger.md and the design spec.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class HudsonClaimId(str, Enum):
    HC_01 = "HC-01"; HC_02 = "HC-02"; HC_03 = "HC-03"; HC_04 = "HC-04"
    HC_05 = "HC-05"; HC_06 = "HC-06"; HC_07 = "HC-07"; HC_08 = "HC-08"


class ClaimStatus(IntEnum):
    """Per-claim evidentiary status. Ordered so max/min roll-ups are numeric. A 'lead' is
    promising evidence, NOT support; simulation caps at LEAD."""
    CANDIDATE = 0
    LEAD = 1
    ANOMALOUS = 2
    PROVISIONALLY_SUPPORTED = 3
    SUPPORTED = 4
    INDEPENDENTLY_REPLICATED = 5


class Route(str, Enum):
    CONVENTIONAL = "conventional"   # Branch A: R->0, Meissner flux exclusion
    OPTICAL = "optical"             # Branch B: persistent ring-down, dM/dP tracking resonance
    NONE = "none"


@dataclass(frozen=True)
class ClaimRecord:
    id: HudsonClaimId
    claim_text: str
    required_observation: str
    mundane_alternative: str
    status: ClaimStatus
    evidence_level: int
    route: Route = Route.NONE
    computable: bool = True
    decisive_experiment: object = None   # validator.ValidationSuite | None (procedural claims)
    note: str = ""


@dataclass(frozen=True)
class ReplicationEvidence:
    """External replication metadata. Default-blocked: absent this record, G_replication is False."""
    n_batches: int
    n_labs: int
    preregistered_thresholds: bool
    raw_data_retained: bool
    blinded_controls_correct: bool


@dataclass(frozen=True)
class MeasuredEvidence:
    """Researcher-supplied measured results for ONE lineage. All default False/None -> the
    default-blocked simulation path (gates cannot climb past LEAD)."""
    # conventional superconductivity route
    zero_resistance: bool = False
    flux_exclusion: bool = False
    critical_behavior: bool = False
    artifact_excluded: bool = False
    # optical route: a HudsonOpticalResult computed WITH the researcher's measured inputs
    optical_result: object = None       # hudson_optical.HudsonOpticalResult | None
    # claim-specific measured confirmations (mundane alternative excluded)
    hc01_nonmetallic_confirmed: bool = False
    hc03_orbital_confirmed: bool = False
    hc04_isotope_confirmed: bool = False
    hc05_recovery_confirmed: bool = False
    hc08_mass_confirmed: bool = False
    replication: ReplicationEvidence | None = None
```

- [ ] **Step 5: Run to verify it passes + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/config.py src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): foundation enums, records, HC-02/replication thresholds"
```

---

### Task 3: Identity gates + HC-01 assessor

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: `identity.IdentityWitness` (composition, phase, morphology, oxidation_state).
- Produces: `HudsonIdentity(str, Enum)` {ESTABLISHED, HUDSON_SATISFIED, HUDSON_FAILED, HUDSON_UNRESOLVED}; `g_identity_established(witness) -> bool`; `assess_hc01(witness, target, th) -> ClaimRecord`; `_OX_TOL = 0.5`; the phase constant `NONMETALLIC_ELEMENTAL = "nonmetallic-elemental"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.hudson_ledger import (
    HudsonIdentity,
    NONMETALLIC_ELEMENTAL,
    assess_hc01,
    g_identity_established,
)
from orme_lab.identity import IdentityWitness

TH = DEFAULT_CONFIG.thresholds


def test_identity_established_is_phase_agnostic():
    # a fully-characterized METAL is "established" (we know what it is) even though it is NOT Hudson's state
    metal = IdentityWitness("Ir", "metallic", "bulk", 0.0)
    assert g_identity_established(metal) is True
    hc01 = assess_hc01(metal, "Ir", TH)
    assert hc01.status.name in ("CANDIDATE",)            # metallic -> HC-01 not supported (ruled against)


def test_hc01_supported_only_for_nonmetallic_elemental():
    hud = IdentityWitness("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0)
    hc01 = assess_hc01(hud, "Ir", TH)
    assert hc01.status >= __import__("orme_lab.hudson_ledger", fromlist=["ClaimStatus"]).ClaimStatus.PROVISIONALLY_SUPPORTED
    # an oxide/salt is the ruled-out mundane alternative
    oxide = IdentityWitness("IrO2", "oxide", "nanoparticle", 4.0)
    assert assess_hc01(oxide, "Ir", TH).status.name == "CANDIDATE"


def test_identity_unresolved_when_uncharacterized():
    blank = IdentityWitness(None, None, None, None)
    assert g_identity_established(blank) is False
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError: cannot import name 'assess_hc01'`.

- [ ] **Step 3: Implement**

Add to `hudson_ledger.py` (add `from .config import ModelThresholds` and `from .identity import IdentityWitness`):

```python
#: Hudson's claimed novel phase: elemental composition, zero oxidation, but NOT the metallic
#: lattice — distinct from both "metallic" and the compound phases (oxide/salt/...).
NONMETALLIC_ELEMENTAL = "nonmetallic-elemental"
_OX_TOL = 0.5   # |oxidation| above this implies a compound, not an elemental phase


class HudsonIdentity(str, Enum):
    ESTABLISHED = "established"              # characterization complete (phase-agnostic)
    HUDSON_SATISFIED = "hudson-satisfied"   # established AND nonmetallic AND atomically dispersed
    HUDSON_FAILED = "hudson-failed"         # identified but metallic / clustered / compound
    HUDSON_UNRESOLVED = "hudson-unresolved" # cannot distinguish isolated atoms from clusters/phases


def g_identity_established(witness: IdentityWitness) -> bool:
    """Phase-AGNOSTIC: every descriptor is known within stated uncertainty. 'We know what it
    physically is' — whether metal, compound, or the novel phase. (This is NOT identity.py's
    metallic-target gate, which is Branch-A-specific.)"""
    return (witness.composition is not None and witness.phase is not None
            and witness.morphology is not None and witness.oxidation_state is not None)


def assess_hc01(witness: IdentityWitness, target: str, th: ModelThresholds) -> ClaimRecord:
    """HC-01: a stable NONMETALLIC ELEMENTAL PGM form (composition = target, |oxidation| <= tol,
    phase = nonmetallic-elemental). The oxide/hydroxide/salt/complex phases are the ruled-out
    mundane alternative. Simulation caps at PROVISIONALLY_SUPPORTED via witness; a MEASURED
    confirmation (loaded separately) is what reaches SUPPORTED."""
    text = "stable nonmetallic PGM form"
    mundane = "oxide / hydroxide / salt / ligand complex"
    if not g_identity_established(witness):
        return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                           mundane, ClaimStatus.CANDIDATE, 2, Route.NONE, True, None,
                           "identity not established")
    is_elemental = (witness.composition == target and abs(witness.oxidation_state) <= _OX_TOL)
    if witness.phase == NONMETALLIC_ELEMENTAL and is_elemental:
        return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                           mundane, ClaimStatus.PROVISIONALLY_SUPPORTED, 2, Route.NONE, True, None,
                           "witness: nonmetallic-elemental phase")
    return ClaimRecord(HudsonClaimId.HC_01, text, "elemental PGM, zero oxidation, non-metallic",
                       mundane, ClaimStatus.CANDIDATE, 2, Route.NONE, True, None,
                       f"phase '{witness.phase}' is not nonmetallic-elemental "
                       f"(mundane alternative: {mundane})")
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): identity split (established vs Hudson-conformant) + HC-01"
```

---

### Task 4: HC-02 dispersion policy + G_hudson_material_state

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: `structure.StructuralDistribution` (`f1()`, `nn_distances()`), `IdentityWitness`.
- Produces: `assess_hc02(distribution, th) -> ClaimRecord`; `g_hudson_material_state(witness, distribution, target, th) -> tuple[bool, HudsonIdentity]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.hudson_ledger import assess_hc02, g_hudson_material_state
from orme_lab.elements import get_element
from orme_lab.structure import dispersed_sample, make_distribution
from orme_lab.geometry import make_compact_cluster, make_monomer


def test_hc02_clears_for_well_dispersed_sample():
    el = get_element("Ir")
    disp = dispersed_sample(el, 0.95)                    # 95% isolated
    r = assess_hc02(disp, TH)
    assert r.status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    # a clustered sample fails the policy
    clustered = make_distribution([(make_compact_cluster(el, 13), 1.0)])
    assert assess_hc02(clustered, TH).status.name == "CANDIDATE"


def test_hc02_flags_pgm_pgm_coordination():
    el = get_element("Ir")
    # 60% isolated / 40% clustered: below the isolated floor AND above clustered cap -> fails
    mixed = dispersed_sample(el, 0.60)
    assert assess_hc02(mixed, TH).status.name == "CANDIDATE"


def test_material_state_gate_combines_hc01_and_hc02():
    el = get_element("Ir")
    hud_witness = IdentityWitness("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0)
    ok, ident = g_hudson_material_state(hud_witness, dispersed_sample(el, 0.95), "Ir", TH)
    assert ok is True and ident is HudsonIdentity.HUDSON_SATISFIED
    metal_witness = IdentityWitness("Ir", "metallic", "bulk", 0.0)
    ok2, ident2 = g_hudson_material_state(metal_witness, dispersed_sample(el, 0.95), "Ir", TH)
    assert ok2 is False and ident2 is HudsonIdentity.HUDSON_FAILED
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError: cannot import name 'assess_hc02'`.

- [ ] **Step 3: Implement**

Add to `hudson_ledger.py` (add `import math` and `from .structure import StructuralDistribution`):

```python
def assess_hc02(distribution: StructuralDistribution, th: ModelThresholds) -> ClaimRecord:
    """HC-02 is a POLICY over measurements, not a Boolean. Clears when: isolated fraction is
    above the floor AND the upper-bounded clustered fraction is under the cap AND no PGM-PGM
    coordination signal exceeds tolerance. A monomer has nn distance +inf (no bond)."""
    f_single = distribution.f1()
    clustered_ub = min(1.0, (1.0 - f_single) + th.hudson_hc02_cluster_margin)
    coordinated = sum(frac for dist, frac in distribution.nn_distances()
                      if math.isfinite(dist) and dist <= th.hudson_hc02_bond_length_ang)
    text, mundane = "atomically dispersed ('monoatomic')", "undetected clusters / nanoparticles"
    req = "predominantly isolated atoms (EXAFS/STEM/PDF)"
    clears = (f_single >= th.hudson_hc02_min_isolated_fraction
              and clustered_ub <= th.hudson_hc02_max_clustered_fraction
              and coordinated <= th.hudson_hc02_pgm_pgm_tolerance)
    if clears:
        return ClaimRecord(HudsonClaimId.HC_02, text, req, mundane,
                           ClaimStatus.PROVISIONALLY_SUPPORTED, 2, Route.NONE, True, None,
                           f"f_single={f_single:.2f}, clustered_ub={clustered_ub:.2f}, "
                           f"pgm-pgm={coordinated:.2f}")
    return ClaimRecord(HudsonClaimId.HC_02, text, req, mundane, ClaimStatus.CANDIDATE, 2,
                       Route.NONE, True, None,
                       f"dispersion policy not met (f_single={f_single:.2f}, "
                       f"clustered_ub={clustered_ub:.2f}, pgm-pgm={coordinated:.2f})")


def g_hudson_material_state(witness: IdentityWitness, distribution: StructuralDistribution,
                            target: str, th: ModelThresholds) -> tuple[bool, "HudsonIdentity"]:
    """G_hudson_material_state = HC-01 (nonmetallic-elemental) AND HC-02 (atomically dispersed).
    Returns (passed, HudsonIdentity outcome)."""
    if not g_identity_established(witness):
        return False, HudsonIdentity.HUDSON_UNRESOLVED
    hc01 = assess_hc01(witness, target, th).status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    hc02 = assess_hc02(distribution, th).status >= ClaimStatus.PROVISIONALLY_SUPPORTED
    if hc01 and hc02:
        return True, HudsonIdentity.HUDSON_SATISFIED
    return False, HudsonIdentity.HUDSON_FAILED
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): HC-02 dispersion policy + G_hudson_material_state"
```

---

### Task 5: Conventional-SC, optical, causality, replication gates

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: `hudson_optical.HudsonClaim`, `HudsonOpticalResult` (`.supported`), `MeasuredEvidence`, `ReplicationEvidence`.
- Produces: `g_conventional_superconductivity(measured) -> bool`; `g_candidate_optical(optical_result) -> bool`; `optical_magnetic_causality(optical_result) -> bool`; `replication_gate(rep, th) -> bool`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.hudson_ledger import (
    g_candidate_optical,
    g_conventional_superconductivity,
    optical_magnetic_causality,
    replication_gate,
)
from orme_lab.hudson_optical import evaluate_hudson_optical


def _optical(**kw):
    return evaluate_hudson_optical(number_density_m3=9.5e28, anisotropy_score=0.4, thresholds=TH,
                                   matter_ev=9.0, coupling_fraction=0.3, cavity_loss_ev=0.02,
                                   matter_loss_ev=0.02, **kw)


def test_conventional_sc_gate_is_default_blocked():
    assert g_conventional_superconductivity(MeasuredEvidence()) is False
    full = MeasuredEvidence(zero_resistance=True, flux_exclusion=True,
                            critical_behavior=True, artifact_excluded=True)
    assert g_conventional_superconductivity(full) is True


def test_optical_gates_need_measured_persistence_and_magnetism():
    # simulation-only optical result: strong coupling but NO persistence/magnetism -> gates False
    assert g_candidate_optical(_optical()) is False
    assert optical_magnetic_causality(_optical()) is False
    full = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    assert g_candidate_optical(full) is True
    assert optical_magnetic_causality(full) is True


def test_replication_gate_is_default_blocked():
    assert replication_gate(None, TH) is False
    assert replication_gate(ReplicationEvidence(3, 2, True, True, True), TH) is True
    assert replication_gate(ReplicationEvidence(2, 2, True, True, True), TH) is False   # < 3 batches
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Add to `hudson_ledger.py` (add `from .hudson_optical import HudsonClaim`):

```python
def g_conventional_superconductivity(measured: MeasuredEvidence) -> bool:
    """Branch A, measured: zero_resistance AND flux_exclusion AND critical_behavior AND
    artifact_excluded. Default-blocked (all False by default)."""
    return (measured.zero_resistance and measured.flux_exclusion
            and measured.critical_behavior and measured.artifact_excluded)


def g_candidate_optical(optical_result) -> bool:
    """Branch B: coherent-mode (L3+L4) AND material-coupling (L6) AND energy-transport (L5).
    L5 requires a PERSISTENT measured ring-down, so this is default-blocked at sim level."""
    if optical_result is None:
        return False
    s = optical_result.supported
    return {HudsonClaim.STRONG_COUPLING, HudsonClaim.MACRO_COHERENCE,
            HudsonClaim.ELECTRONIC_COUPLING, HudsonClaim.LOW_LOSS_TRANSPORT}.issubset(s)


def optical_magnetic_causality(optical_result) -> bool:
    """Branch B level-7: magnetic response tracks the optical resonance (measured dM/dP)."""
    return optical_result is not None and HudsonClaim.MAGNETISM_COUPLED in optical_result.supported


def replication_gate(rep: "ReplicationEvidence | None", th: ModelThresholds) -> bool:
    """Default-blocked: >= min_batches, > 1 lab (>= min_labs), preregistered thresholds, raw data
    retained, blinded controls correctly classified."""
    if rep is None:
        return False
    return (rep.n_batches >= th.hudson_replication_min_batches
            and rep.n_labs >= th.hudson_replication_min_labs
            and rep.preregistered_thresholds and rep.raw_data_retained
            and rep.blinded_controls_correct)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): conventional-SC / optical / causality / replication gates"
```

---

### Task 6: Computable claim assessors HC-04, HC-06, HC-07 (+ either-route, status ladder)

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: `pipeline.CandidateRecord` (credited_sc_lead, hudson_supported_levels, meissner_screening), `meissner_field.screen_meissner`, `ir_contaminant.screen_contaminants`, `MeasuredEvidence`.
- Produces: `assess_hc04(observed_doublet, th) -> ClaimRecord`; `assess_hc06(candidate, measured, th) -> ClaimRecord`; `assess_hc07(candidate, measured, th) -> ClaimRecord`.

- [ ] **Step 1: Inspect the Meissner verdict strings**

Run: `cd /orme-lab && python3 -c "from orme_lab.meissner_field import screen_meissner as s; print(s(isolated_premise=True).verdict); print(s(isolated_premise=False).verdict)"`
Note the verdict strings; HC-06's conventional route is a LEAD when the screen yields a physical (not "outside physical") diamagnetic result.

- [ ] **Step 2: Write the failing test**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.hudson_ledger import assess_hc04, assess_hc06, assess_hc07
from orme_lab.geometry import make_compact_cluster
from orme_lab.pipeline import evaluate_candidate
from orme_lab.spin_states import high_spin_state
from orme_lab.identity import IdentityWitness as IW


def _candidate(sym):
    el = get_element(sym)
    return evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                              high_spin_state(el), DEFAULT_CONFIG)


def test_hc07_credited_lead_is_lead_not_supported():
    # a credited_sc_lead candidate gives HC-07 status LEAD (never SUPPORTED from a sim lead)
    rec = _candidate("Os")
    r = assess_hc07(rec, MeasuredEvidence(), TH)
    assert r.status is ClaimStatus.LEAD or r.status is ClaimStatus.CANDIDATE
    assert r.status < ClaimStatus.SUPPORTED
    # measured conventional evidence reaches SUPPORTED, route=conventional
    full = MeasuredEvidence(zero_resistance=True, flux_exclusion=True,
                            critical_behavior=True, artifact_excluded=True)
    r2 = assess_hc07(rec, full, TH)
    assert r2.status >= ClaimStatus.SUPPORTED and r2.route is Route.CONVENTIONAL


def test_hc06_either_route_labelled():
    rec = _candidate("Os")
    conv = assess_hc06(rec, MeasuredEvidence(flux_exclusion=True), TH)
    assert conv.status >= ClaimStatus.SUPPORTED and conv.route is Route.CONVENTIONAL
    opt_result = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    opt = assess_hc06(rec, MeasuredEvidence(optical_result=opt_result), TH)
    assert opt.route is Route.OPTICAL and opt.status >= ClaimStatus.SUPPORTED


def test_hc04_folds_the_ir_control():
    r = assess_hc04((1429.53, 1490.99), TH)
    assert r.id.value == "HC-04"
    assert "contaminant" in r.mundane_alternative.lower()
```

- [ ] **Step 3: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError`.

- [ ] **Step 4: Implement**

Add to `hudson_ledger.py` (add `from .meissner_field import screen_meissner`, `from .ir_contaminant import screen_contaminants`, `from .pipeline import CandidateRecord`):

```python
def assess_hc04(observed_doublet, th: ModelThresholds) -> ClaimRecord:
    """HC-04: the 1400-1600 cm^-1 doublet. Attacks the contaminant alternative first via the
    IR contaminant screen. A plausible match to a mundane species keeps HC-04 at LEAD/CANDIDATE
    (the doublet is explained by contamination); intrinsic assignment needs measured isotope/
    atmosphere sensitivity (loaded separately)."""
    text = "1400-1600 cm^-1 doublet"
    mundane = "water / carbonate / nitrate / ligand / instrument bkg (carboxylate contaminant)"
    match = screen_contaminants(tuple(observed_doublet))
    note = getattr(match, "explain", lambda: "")()
    return ClaimRecord(HudsonClaimId.HC_04, text, "reproducible isotope- & atmosphere-sensitive assignment",
                       mundane, ClaimStatus.LEAD, 2, Route.NONE, True, None,
                       f"IR contaminant screen: {note}")


def assess_hc06(candidate: CandidateRecord, measured: MeasuredEvidence,
                th: ModelThresholds) -> ClaimRecord:
    """HC-06: flux exclusion > 200 K. Either route, labelled. Conventional = Meissner screen
    (LEAD) / measured flux exclusion (SUPPORTED); optical = Branch-B level-7 (measured dM/dP)."""
    text, mundane = "flux exclusion > 200 K", "magnetic artifact / ordinary diamagnetism"
    req = "geometry-corrected diamagnetic shielding"
    if measured.flux_exclusion:
        return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.CONVENTIONAL, True, None, "measured diamagnetic flux exclusion")
    if optical_magnetic_causality(measured.optical_result):
        return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.OPTICAL, True, None, "measured dM/dP tracks the optical resonance")
    screen = screen_meissner(isolated_premise=True)
    return ClaimRecord(HudsonClaimId.HC_06, text, req, mundane, ClaimStatus.LEAD, 2,
                       Route.CONVENTIONAL, True, None, f"Meissner screen: {screen.verdict}")


def assess_hc07(candidate: CandidateRecord, measured: MeasuredEvidence,
                th: ModelThresholds) -> ClaimRecord:
    """HC-07: superconductivity. credited_sc_lead -> LEAD (never SUPPORTED from a sim lead).
    Measured conventional evidence -> SUPPORTED route=conventional; measured optical phase
    (Branch-B transport) -> SUPPORTED route=optical."""
    text, mundane = "superconductivity", "ionic conduction / percolation / contact artifact"
    req = "R->0 + magnetic + thermodynamic evidence"
    if g_conventional_superconductivity(measured):
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.CONVENTIONAL, True, None, "measured R->0 + magnetic + thermodynamic")
    if g_candidate_optical(measured.optical_result):
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.SUPPORTED, 4,
                           Route.OPTICAL, True, None, "measured persistent optical transport (Branch B)")
    if candidate.credited_sc_lead:
        return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.LEAD, 2,
                           Route.NONE, True, None, "credited_sc_lead (simulation lead, not support)")
    return ClaimRecord(HudsonClaimId.HC_07, text, req, mundane, ClaimStatus.CANDIDATE, 2,
                       Route.NONE, True, None, "no SC lead")
```

- [ ] **Step 5: Run to verify it passes + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q && python3 -m pytest -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): HC-04/06/07 assessors, either-route labelled, lead != supported"
```

---

### Task 7: Procedural assessors HC-03, HC-05, HC-08 (decisive-experiment designs)

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: `MeasuredEvidence`.
- Produces: `assess_hc03(measured) -> ClaimRecord`, `assess_hc05(measured) -> ClaimRecord`, `assess_hc08(measured) -> ClaimRecord` — each `computable=False` with a Level-3 decisive-experiment string design in `note` and the mundane alternative named. `decisive_experiment` stays `None` (these are procedural, not routed through `validator.design_validation`, which is candidate-scoped); the design lives in `required_observation` + `note`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.hudson_ledger import assess_hc03, assess_hc05, assess_hc08


def test_procedural_claims_emit_level3_designs_and_default_to_candidate():
    for fn, hc in ((assess_hc03, "HC-03"), (assess_hc05, "HC-05"), (assess_hc08, "HC-08")):
        r = fn(MeasuredEvidence())
        assert r.id.value == hc
        assert r.computable is False
        assert r.evidence_level == 3                    # a laboratory-prediction design
        assert r.status is ClaimStatus.CANDIDATE
        assert r.mundane_alternative and r.required_observation


def test_procedural_claims_reach_supported_only_with_measured_confirmation():
    assert assess_hc05(MeasuredEvidence(hc05_recovery_confirmed=True)).status >= ClaimStatus.SUPPORTED
    assert assess_hc08(MeasuredEvidence(hc08_mass_confirmed=True)).status >= ClaimStatus.SUPPORTED
    assert assess_hc03(MeasuredEvidence(hc03_orbital_confirmed=True)).status >= ClaimStatus.SUPPORTED
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Add to `hudson_ledger.py`:

```python
def _procedural(hc, text, required, mundane, confirmed) -> ClaimRecord:
    status = ClaimStatus.SUPPORTED if confirmed else ClaimStatus.CANDIDATE
    ev = 4 if confirmed else 3   # a measured confirmation is an observation (L4); the design is L3
    note = ("measured confirmation loaded" if confirmed
            else f"Level-3 decisive-experiment design; attack the mundane alternative first: {mundane}")
    return ClaimRecord(hc, text, required, mundane, status, ev, Route.NONE, False, None, note)


def assess_hc03(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_03, "orbital rearrangement",
                       "reproducible electronic structure distinct from known compounds (XPS/XAS/EELS)",
                       "ordinary crystal-field / oxidation-state change", measured.hc03_orbital_confirmed)


def assess_hc05(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_05, "conversion back to metal",
                       "mass-balanced recovery of the original PGM",
                       "contamination / reduction of an ordinary salt", measured.hc05_recovery_confirmed)


def assess_hc08(measured: MeasuredEvidence) -> ClaimRecord:
    return _procedural(HudsonClaimId.HC_08, "anomalous apparent mass",
                       "replication on independent balances under controlled gas flow",
                       "buoyancy / convection / magnetic force / balance coupling", measured.hc08_mass_confirmed)
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): procedural HC-03/05/08 decisive-experiment designs"
```

---

### Task 8: Roll-ups, G_Hudson gates, interim verdict, `evaluate_hudson_ledger`

**Files:** Modify `src/orme_lab/hudson_ledger.py`; Test `tests/test_hudson_ledger.py`.

**Interfaces:**
- Consumes: everything above; `lineage.singleton_lineage`, `lineage.lineage_key`.
- Produces: `HudsonGateResult(frozen)`, `HudsonLedger(frozen)`, `evaluate_hudson_ledger(candidates, *, witnesses=None, distributions=None, lineages=None, measured=None, observed_doublet=None, thresholds) -> HudsonLedger`, with `claim_status(hc)`, `integrated_status`, `explain()`.

- [ ] **Step 1: Write the failing test (incl. the anti-Frankenstein keystone)**

Append to `tests/test_hudson_ledger.py`:

```python
from orme_lab.hudson_ledger import HudsonLedger, evaluate_hudson_ledger


def _sat_witness():
    return IW("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0)


def test_ledger_default_path_is_default_blocked_and_never_validated():
    led = evaluate_hudson_ledger([_candidate("Os")], thresholds=TH)
    assert isinstance(led, HudsonLedger)
    assert led.gate.g_hudson_mechanism is False           # no measured evidence
    assert led.gate.g_conventional_superconductivity is False
    assert "VALIDATED" not in led.gate.interim_verdict.upper() or "NOT" in led.gate.interim_verdict.upper()
    assert led.gate.interim_verdict != "HUDSON CLAIM VALIDATED"


def test_anti_frankenstein_portfolio_vs_integrated():
    # five candidates, each cleared for a DIFFERENT claim, all in DIFFERENT lineages
    el = get_element("Ir")
    cands = [_candidate("Os"), _candidate("Ir"), _candidate("Pt"), _candidate("Rh"), _candidate("Ru")]
    # give each its own measured win on a different claim, distinct lineages
    ids = [f"lin{i}" for i in range(5)]
    lineages = [singleton_lineage(i) for i in ids]
    opt = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    measured = {
        "lin0/lin0": MeasuredEvidence(hc01_nonmetallic_confirmed=True),
        "lin1/lin1": MeasuredEvidence(hc05_recovery_confirmed=True),
        "lin2/lin2": MeasuredEvidence(optical_result=opt),                       # optical mode+transport
        "lin3/lin3": MeasuredEvidence(flux_exclusion=True),                      # magnetism
        "lin4/lin4": MeasuredEvidence(zero_resistance=True, flux_exclusion=True,
                                      critical_behavior=True, artifact_excluded=True),  # transport
    }
    led = evaluate_hudson_ledger(cands, witnesses=[_sat_witness()] * 5,
                                 distributions=[dispersed_sample(el, 0.95)] * 5,
                                 lineages=lineages, measured=measured, thresholds=TH)
    # portfolio best-of shows several claims supported across the fleet...
    supported_claims = [hc for hc in HudsonClaimId if led.claim_status(hc) >= ClaimStatus.SUPPORTED]
    assert len(supported_claims) >= 3
    # ...but NO single lineage clears the core conjunction -> integrated not supported
    assert led.integrated_status < ClaimStatus.SUPPORTED
    assert led.gate.g_hudson_mechanism is False


def test_single_lineage_full_stack_supports_integrated_but_still_not_validated():
    el = get_element("Ir")
    opt = _optical(measured_ringdown_fs=1e30, measured_dM_dP=1.0, dM_dP_on_resonance=True)
    m = MeasuredEvidence(optical_result=opt, hc01_nonmetallic_confirmed=True,
                         flux_exclusion=True, hc04_isotope_confirmed=True,
                         replication=ReplicationEvidence(3, 2, True, True, True))
    led = evaluate_hudson_ledger([_candidate("Ir")], witnesses=[_sat_witness()],
                                 distributions=[dispersed_sample(el, 0.95)],
                                 lineages=[singleton_lineage("Ir")],
                                 measured={"Ir/Ir": m}, observed_doublet=(1429.53, 1490.99),
                                 thresholds=TH)
    assert led.gate.g_hudson_mechanism is True             # one lineage clears the mechanism
    assert led.gate.interim_verdict != "HUDSON CLAIM VALIDATED"   # never that string
    assert "replication" in led.gate.interim_verdict or "supported" in led.gate.interim_verdict
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implement**

Add to `hudson_ledger.py` (add `from .lineage import MaterialLineage, singleton_lineage, lineage_key`):

```python
_CORE = (HudsonClaimId.HC_01, HudsonClaimId.HC_02, HudsonClaimId.HC_04,
         HudsonClaimId.HC_06, HudsonClaimId.HC_07)


@dataclass(frozen=True)
class HudsonGateResult:
    g_identity_established: bool
    g_hudson_material_state: bool
    g_conventional_superconductivity: bool
    g_candidate_optical: bool
    optical_magnetic_causality: bool
    replication: bool
    g_hudson_mechanism: bool
    interim_verdict: str


@dataclass(frozen=True)
class HudsonLedger:
    claims: tuple[ClaimRecord, ...]                 # portfolio best-of, fixed HC order
    gate: HudsonGateResult
    integrated_status: ClaimStatus
    integrated_lineage_id: str | None
    per_lineage: tuple[tuple[str, ClaimStatus], ...]

    def claim_status(self, hc: HudsonClaimId) -> ClaimStatus:
        return next(c.status for c in self.claims if c.id == hc)

    def explain(self) -> str:
        return (f"Hudson ledger: integrated_status={self.integrated_status.name} "
                f"(lineage {self.integrated_lineage_id}); {self.gate.interim_verdict}. "
                f"Conventional SC gate={self.gate.g_conventional_superconductivity}; "
                f"Hudson mechanism gate={self.gate.g_hudson_mechanism}. Portfolio best-of and the "
                f"integrated weakest-link roll-up are reported separately; the lab never emits "
                f"'HUDSON CLAIM VALIDATED'.")


def _interim_verdict(gate_bits: dict) -> str:
    """Deterministic priority ladder. NEVER returns 'HUDSON CLAIM VALIDATED'."""
    if gate_bits["g_hudson_mechanism"] and gate_bits["replication"]:
        return "independent-replication-achieved (Hudson mechanism supported on one replicated lineage)"
    if gate_bits["g_conventional_superconductivity"]:
        return "bulk-SC-supported (conventional route; distinct from the Hudson optical mechanism)"
    if gate_bits["g_candidate_optical"]:
        return "SC-like-response (optical coherent transport; mechanism not yet fully closed)"
    if gate_bits["g_hudson_material_state"]:
        return "novel-phase-candidate (Hudson material state; no transport/magnetism established)"
    if gate_bits["g_identity_established"]:
        return "identity-established (not Hudson-conformant)"
    return "identity-unresolved"


def _candidate_claim_records(cand, witness, dist, measured, observed_doublet, target, th):
    """All eight ClaimRecords for ONE candidate/lineage."""
    m = measured if measured is not None else MeasuredEvidence()
    hc01 = assess_hc01(witness, target, th) if witness is not None else \
        ClaimRecord(HudsonClaimId.HC_01, "stable nonmetallic PGM form", "", "", ClaimStatus.CANDIDATE, 2)
    if m.hc01_nonmetallic_confirmed and hc01.status >= ClaimStatus.PROVISIONALLY_SUPPORTED:
        hc01 = ClaimRecord(hc01.id, hc01.claim_text, hc01.required_observation, hc01.mundane_alternative,
                           ClaimStatus.SUPPORTED, 4, hc01.route, True, None, "measured nonmetallic confirmation")
    hc02 = assess_hc02(dist, th) if dist is not None else \
        ClaimRecord(HudsonClaimId.HC_02, "atomically dispersed", "", "", ClaimStatus.CANDIDATE, 2)
    hc03 = assess_hc03(m)
    hc04 = assess_hc04(observed_doublet, th) if observed_doublet is not None else \
        ClaimRecord(HudsonClaimId.HC_04, "1400-1600 cm^-1 doublet", "", "carboxylate contaminant",
                    ClaimStatus.CANDIDATE, 2)
    if m.hc04_isotope_confirmed:
        hc04 = ClaimRecord(hc04.id, hc04.claim_text, hc04.required_observation, hc04.mundane_alternative,
                           ClaimStatus.SUPPORTED, 4, hc04.route, True, None, "measured isotope/atmosphere sensitivity")
    hc05 = assess_hc05(m)
    hc06 = assess_hc06(cand, m, th)
    hc07 = assess_hc07(cand, m, th)
    hc08 = assess_hc08(m)
    return (hc01, hc02, hc03, hc04, hc05, hc06, hc07, hc08)


def evaluate_hudson_ledger(candidates, *, witnesses=None, distributions=None, lineages=None,
                           measured=None, observed_doublet=None, thresholds):
    """Two-layer roll-up. Portfolio best-of over all candidates (per claim); integrated
    weakest-link within one lineage, then best across (never min_j[max_c])."""
    th = thresholds
    n = len(candidates)
    witnesses = witnesses if witnesses is not None else [None] * n
    distributions = distributions if distributions is not None else [None] * n
    lineages = lineages if lineages is not None else [singleton_lineage(
        f"{c.element}/{c.geometry}/{c.spin_label}") for c in candidates]
    measured = measured or {}

    # per-candidate records (fixed order)
    per_candidate = []
    for i, cand in enumerate(candidates):
        lin = lineages[i]
        recs = _candidate_claim_records(cand, witnesses[i], distributions[i],
                                        measured.get(lineage_key(lin)), observed_doublet,
                                        cand.element, th)
        per_candidate.append((lin, recs))

    # Layer 1: portfolio best-of per claim (max status across candidates); pick a representative record
    portfolio = []
    for j, hc in enumerate(HudsonClaimId):
        best = max((recs[j] for _, recs in per_candidate), key=lambda r: r.status)
        portfolio.append(best)

    # Layer 2: integrated weakest-link WITHIN one lineage over CORE, then best across lineages
    core_idx = [list(HudsonClaimId).index(hc) for hc in _CORE]
    best_lineage_id, best_status = None, ClaimStatus.CANDIDATE
    per_lineage = []
    # group by lineage key so aliquots of one batch combine (take the max per claim within a batch)
    from .lineage import group_by_lineage
    grouped = group_by_lineage(tuple((lin, recs) for lin, recs in per_candidate))
    for key, recs_list in grouped.items():
        combined = [max((recs[j] for recs in recs_list), key=lambda r: r.status) for j in range(8)]
        weakest = min(combined[j].status for j in core_idx)
        per_lineage.append((key, weakest))
        if weakest > best_status:
            best_status, best_lineage_id = weakest, key

    # gates evaluated on the WINNING lineage's measured evidence (same-lineage requirement)
    win_measured = measured.get(best_lineage_id, MeasuredEvidence()) if best_lineage_id else MeasuredEvidence()
    win_idx = next((i for i, l in enumerate(lineages) if lineage_key(l) == best_lineage_id), 0)
    g_id = g_identity_established(witnesses[win_idx]) if witnesses[win_idx] is not None else False
    g_mat, _ident = (g_hudson_material_state(witnesses[win_idx], distributions[win_idx],
                                             candidates[win_idx].element, th)
                     if witnesses[win_idx] is not None and distributions[win_idx] is not None
                     else (False, None))
    g_conv = g_conventional_superconductivity(win_measured)
    g_opt = g_candidate_optical(win_measured.optical_result)
    g_caus = optical_magnetic_causality(win_measured.optical_result)
    g_rep = replication_gate(win_measured.replication, th)
    g_mech = g_mat and g_opt and g_caus and g_rep
    bits = {"g_identity_established": g_id, "g_hudson_material_state": g_mat,
            "g_conventional_superconductivity": g_conv, "g_candidate_optical": g_opt,
            "optical_magnetic_causality": g_caus, "replication": g_rep, "g_hudson_mechanism": g_mech}
    gate = HudsonGateResult(g_id, g_mat, g_conv, g_opt, g_caus, g_rep, g_mech, _interim_verdict(bits))
    return HudsonLedger(tuple(portfolio), gate, best_status, best_lineage_id, tuple(per_lineage))
```

- [ ] **Step 4: Run to verify it passes + full suite**

Run: `cd /orme-lab && python3 -m pytest tests/test_hudson_ledger.py -q && python3 -m pytest -q`
Expected: PASS (incl. the anti-Frankenstein keystone).

- [ ] **Step 5: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add src/orme_lab/hudson_ledger.py tests/test_hudson_ledger.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "feat(ledger): two roll-ups, G_Hudson gate, interim verdict (anti-Frankenstein)"
```

---

### Task 9: Documentation

**Files:** Create `docs/hudson_claim_ledger.md`.

- [ ] **Step 1: Write the doc**

Create `docs/hudson_claim_ledger.md` documenting: the falsify-first framing (determine whether a reproducible state satisfies Hudson's properties, not validate-Hudson); the HC-01..HC-08 table with required observation + mundane alternative + source; the evidentiary-status ladder (candidate → … → independently_replicated) and `credited_sc_lead → LEAD`; the six gates with the identity split (`G_identity_established` phase-agnostic vs `G_hudson_material_state`); HC-02 as a policy over `structure`'s `f1`/`P(n)`/`R_PGM–PGM`; the two roll-ups with the exact formulas and the explicit ban on `min_j[max_c …]` (the Frankenstein bug); the lineage model (three integration levels, claims attaching to the resulting state); the default-blocks; and the invariant that the ledger never emits "HUDSON CLAIM VALIDATED". Cross-reference the design spec and `research-wiki/prior-art/hudson-orme-patents-de3920144a1.md`. No new citations.

- [ ] **Step 2: Verify the doc references match the code**

Run: `cd /orme-lab && python3 -c "import orme_lab.hudson_ledger as h; print([c.value for c in h.HudsonClaimId]); print([s.name for s in h.ClaimStatus])"`
Confirm the doc's claim ids and status ladder match the module exactly.

- [ ] **Step 3: Commit**

```bash
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  add docs/hudson_claim_ledger.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' \
  commit -m "docs: Hudson Claim Ledger reference (claims, gates, roll-ups, default-blocks)"
```

---

## Self-Review

**Spec coverage:** falsify-first framing (Global Constraints + Task 9); 8 claims (T3/T4 HC-01/02, T6 HC-04/06/07, T7 HC-03/05/08); evidentiary-status ladder + `credited_sc_lead → LEAD` (T2, T6); six gates + identity split (T3/T4/T5); HC-02 policy over `structure` (T4); two roll-ups + anti-Frankenstein keystone (T8); lineage model (T1); default-blocks (T5, T8); never "VALIDATED" (T8 verdict + tests); evidence ceilings (per-record `evidence_level`).

**Placeholder scan:** none — every step has real code and real tests.

**Type consistency:** `ClaimStatus` is the ordered `IntEnum` used by every assessor and both roll-ups; `MeasuredEvidence`/`ReplicationEvidence` fields referenced in T5–T8 are all defined in T2; `HudsonClaimId` iteration order (HC_01..HC_08) is the fixed claim order used in T8's portfolio and `_CORE`; `evaluate_hudson_ledger` keys `measured` by `lineage_key` (family/batch) consistently in T8 and the tests.

**Known implementation notes for the executor:**
- T6 Step 1 must inspect the real Meissner `verdict` strings before finalizing the HC-06 note; the status logic does not depend on the exact string (only measured/optical routes reach SUPPORTED), so this is cosmetic.
- The winning-lineage gate evaluation in T8 uses the lineage that maximizes the integrated weakest-link; ties resolve to the first in candidate order (deterministic). This is the same-lineage requirement enforced in code — gates read only the winning lineage's measured evidence, never a cross-lineage union.
- `screen_contaminants` returns a result whose `explain()` may vary; T6's HC-04 test asserts only the id and the mundane-alternative text, not the note, to stay robust.
