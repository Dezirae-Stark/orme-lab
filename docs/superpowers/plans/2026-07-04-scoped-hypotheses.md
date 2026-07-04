# Scoped Hypotheses (H1/H3 split) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the lab loop's binary H1/H3 hypotheses into element/geometry-scoped variants that retire independently, with a grounded validation guard so a mislabeled scoped avenue is skipped honestly instead of producing a bogus verdict.

**Architecture:** Extract a focused `lab_loop/hypotheses.py` owning the scoped `HYPOTHESES` registry plus per-hypothesis scope predicates grounded in the real `Element.d_shell_vacancies` property (and geometry kind for H3); `ledger.py` imports the registry from it; `loop.py` calls `validate_scope` at proposal intake and skips mismatches via the existing skip machinery.

**Tech Stack:** Python 3, stdlib + existing `orme_lab` modules, pytest. No new deps.

## Global Constraints

- **Determinism in the critical path:** no `time.time()`, `datetime.now()`, unseeded RNG, or order-dependent iteration. `validate_scope` is pure (element lookup + property compare).
- **No fabricated physics:** the class boundary is the real `Element.d_shell_vacancies` property, which exactly matches the model's measured anisotropy (closed-shell d¹⁰ → 0.000; open-shell → 0.165–0.458). Do not invent a boundary.
- **Evidence ceiling unchanged:** `LAB_CEILING = 2`.
- **No AI-identity git trailers.** Commit as `Dezirae Stark <deziraestark69@gmail.com>` via `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m '...'`. No `Co-Authored-By` / `Signed-off-by` / `Claude-Session`.
- **Interpreter is `python3`**, not `python`.
- Spec: `docs/superpowers/specs/2026-07-04-scoped-hypotheses-design.md`.

**Grounded class table (measured, verified — use these exact members):**
- closed-shell `{Ag, Au, Pd}` — `d_shell_vacancies == 0` — anisotropy 0.000.
- open-shell `{Ir, Os, Pt, Rh, Ru}` — `d_shell_vacancies > 0` — anisotropy 0.165–0.458.

## File Structure

| File | Change |
|---|---|
| `src/orme_lab/lab_loop/hypotheses.py` | Create: `HYPOTHESES`, `SCOPE_PREDICATES`, `validate_scope`. |
| `src/orme_lab/lab_loop/ledger.py` | Import `HYPOTHESES` from `hypotheses.py`; drop the local tuple. |
| `src/orme_lab/lab_loop/loop.py` | Call `validate_scope` at intake; generalize the skip digest header; import `validate_scope`. |
| `docs/hypothesis_matrix.md` | Split H1/H3 rows into scoped variants with the measured class table. |
| `tests/lab_loop/test_hypotheses.py`, `tests/lab_loop/test_hypothesis_split.py` | New tests. |

Consumed signatures (verified):
- `orme_lab.elements.get_element(sym: str) -> Element`; `Element.d_shell_vacancies -> int` (`10 - d_electrons`).
- `orme_lab.lab_loop.avenue.Avenue` with `.targeted_hypothesis: str`, `.action: ActionSpec`; `ActionSpec.elements: tuple[str,...]`, `.geometry_kinds: tuple[str,...]`.
- `ledger.py` currently defines `HYPOTHESES` at line 17 and imports from `.avenue`, `.objective`, `.triage`; `Ledger.open_hypotheses` returns `frozenset(h for h in HYPOTHESES if h not in self._killed)`.
- `loop.py:22` imports `from .runner import run_avenue, validate_runnable`; intake loop appends `(av.id, reason)` to `skipped` with `skipped_ids` dedup; skip digest header at `loop.py:108` reads `"## Skipped (malformed proposals — not run, not findings)"`.

---

### Task 1: `hypotheses.py` — scoped registry + scope predicates; rewire ledger

**Files:**
- Create: `src/orme_lab/lab_loop/hypotheses.py`
- Modify: `src/orme_lab/lab_loop/ledger.py` (import `HYPOTHESES`, drop local tuple)
- Test: `tests/lab_loop/test_hypotheses.py`

**Interfaces:**
- Consumes: `orme_lab.elements.get_element`; `orme_lab.lab_loop.avenue.Avenue`/`ActionSpec`.
- Produces: `HYPOTHESES: tuple[str, ...]`; `SCOPE_PREDICATES: dict[str, callable]`; `validate_scope(avenue) -> tuple[bool, str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_hypotheses.py
from orme_lab.lab_loop.hypotheses import HYPOTHESES, validate_scope
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)


def _av(hyp, elements=("Ir",), geoms=("dimer",)):
    return Avenue(
        id="x", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, geoms, ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_registry_has_scoped_variants_not_bare_h1_h3():
    for h in ("H1-open-shell", "H1-closed-shell", "H3-cluster", "H3-monomer"):
        assert h in HYPOTHESES
    assert "H1" not in HYPOTHESES
    assert "H3" not in HYPOTHESES
    for h in ("H2", "H4", "H5", "H6", "H7", "H12", "H16"):
        assert h in HYPOTHESES


def test_h1_element_scope():
    assert validate_scope(_av("H1-open-shell", elements=("Ir",)))[0] is True
    assert validate_scope(_av("H1-open-shell", elements=("Os", "Pt", "Rh", "Ru")))[0] is True
    assert validate_scope(_av("H1-open-shell", elements=("Pd",)))[0] is False        # closed
    assert validate_scope(_av("H1-closed-shell", elements=("Pd", "Au", "Ag")))[0] is True
    assert validate_scope(_av("H1-closed-shell", elements=("Ir",)))[0] is False       # open


def test_h1_mixed_panel_fails_not_all_match():
    ok, reason = validate_scope(_av("H1-open-shell", elements=("Ir", "Pd")))
    assert ok is False and "Pd" in reason


def test_h3_geometry_scope():
    assert validate_scope(_av("H3-cluster", geoms=("compact_cluster",)))[0] is True
    assert validate_scope(_av("H3-cluster", geoms=("monomer",)))[0] is False
    assert validate_scope(_av("H3-monomer", geoms=("monomer",)))[0] is True
    assert validate_scope(_av("H3-monomer", geoms=("dimer",)))[0] is False


def test_unscoped_hypothesis_always_passes():
    assert validate_scope(_av("H5", elements=("Pd",), geoms=("monomer",))) == (True, "")


def test_reason_present_on_mismatch():
    ok, reason = validate_scope(_av("H1-closed-shell", elements=("Ir",)))
    assert ok is False and reason and "H1-closed-shell" in reason
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_hypotheses.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'orme_lab.lab_loop.hypotheses'`.

- [ ] **Step 3: Write minimal implementation**

```python
# src/orme_lab/lab_loop/hypotheses.py
"""The retireable-claim registry and per-hypothesis scope predicates.

Some hypotheses are element/geometry-specific truths, so a single binary switch
would wrongly retire them globally on the first counterexample. H1 and H3 are
split into scoped variants that retire independently. The scope boundary is the
real ``Element.d_shell_vacancies`` property (H1) / geometry kind (H3) -- grounded,
not invented: d_shell_vacancies exactly predicts the toy anisotropy class
(closed-shell d10 -> 0.0; open-shell -> 0.165-0.458).
"""

from __future__ import annotations

from ..elements import get_element
from .avenue import Avenue

#: The retireable claims. H1/H3 are element/geometry-scoped; the rest are global.
HYPOTHESES: tuple[str, ...] = (
    "H1-open-shell", "H1-closed-shell",
    "H2",
    "H3-cluster", "H3-monomer",
    "H4", "H5", "H6", "H7", "H12", "H16",
)


def _all_elements_open_shell(action) -> tuple[bool, str]:
    """H1-open-shell: every element must have an open d-shell (d_shell_vacancies > 0)."""
    for sym in action.elements:
        if get_element(sym).d_shell_vacancies == 0:
            return False, (f"scope mismatch: H1-open-shell requires open-shell "
                           f"(d_shell_vacancies>0) elements, got closed-shell {sym}")
    return True, ""


def _all_elements_closed_shell(action) -> tuple[bool, str]:
    """H1-closed-shell: every element must be closed-shell (d10, d_shell_vacancies == 0)."""
    for sym in action.elements:
        if get_element(sym).d_shell_vacancies != 0:
            return False, (f"scope mismatch: H1-closed-shell requires closed-shell "
                           f"(d10) elements, got open-shell {sym}")
    return True, ""


def _all_geoms(kind: str):
    def _pred(action) -> tuple[bool, str]:
        for g in action.geometry_kinds:
            if g != kind:
                return False, (f"scope mismatch: requires geometry {kind!r}, got {g!r}")
        return True, ""
    return _pred


#: scoped-hypothesis id -> predicate(action) -> (ok, reason). Absent id == unscoped.
SCOPE_PREDICATES: dict[str, callable] = {
    "H1-open-shell": _all_elements_open_shell,
    "H1-closed-shell": _all_elements_closed_shell,
    "H3-cluster": _all_geoms("compact_cluster"),
    "H3-monomer": _all_geoms("monomer"),
}


def validate_scope(avenue: Avenue) -> tuple[bool, str]:
    """Whether a scoped avenue's action matches its hypothesis's element/geometry
    class. Unscoped hypotheses always pass. A scoped variant with a reason string
    on mismatch is skipped honestly by the loop (never run)."""
    pred = SCOPE_PREDICATES.get(avenue.targeted_hypothesis)
    if pred is None:
        return True, ""
    ok, reason = pred(avenue.action)
    if not ok and avenue.targeted_hypothesis not in reason:
        reason = f"{avenue.targeted_hypothesis}: {reason}"
    return ok, reason
```

Note: the `_all_elements_*` reasons already name the class; `validate_scope` prepends the
hypothesis id for the geometry predicates (whose reason doesn't include it) so every mismatch
reason names its hypothesis — satisfying `test_reason_present_on_mismatch` for all four.

Then rewire `src/orme_lab/lab_loop/ledger.py`: delete the local `HYPOTHESES = (...)` line (line 17) and import it instead. Change the import block near the top so it reads:

```python
from .avenue import Avenue, MechanismProposal
from .hypotheses import HYPOTHESES
from .objective import action_key
from .triage import TriageOutcome, Verdict
```

(Keep everything else in `ledger.py` unchanged — `open_hypotheses` still does
`frozenset(h for h in HYPOTHESES if h not in self._killed)`.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_hypotheses.py -v`
Expected: PASS (6 tests).

- [ ] **Step 5: Run the full suite (registry change is repo-wide)**

Run: `python3 -m pytest -q`
Expected: all pass. No existing test targets bare `"H1"`/`"H3"`; `ledger`'s open-hypotheses test compares against `HYPOTHESES` itself, so it stays self-consistent. If any test fails because it hard-coded the old `("H1",...,"H16")` tuple, that is a legitimate registry-change update — update it to the scoped registry and note it in the report.

- [ ] **Step 6: Commit**

```bash
git add src/orme_lab/lab_loop/hypotheses.py src/orme_lab/lab_loop/ledger.py tests/lab_loop/test_hypotheses.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: scoped hypotheses registry (H1/H3 split by grounded element/geometry class) + validate_scope'
```

---

### Task 2: wire the scope guard into loop intake

**Files:**
- Modify: `src/orme_lab/lab_loop/loop.py`
- Test: `tests/lab_loop/test_loop_scope.py`

**Interfaces:**
- Consumes: `validate_scope` (Task 1); the existing intake `skipped`/`skipped_ids` and `_digest`.
- Produces: scope-mismatched avenues are skipped (never run) and surfaced in the digest.

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_loop_scope.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.loop import run_loop


def _av(aid, hyp, elements):
    return Avenue(
        id=aid, tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("dimer",), ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_scope_mismatched_avenue_is_skipped_not_run():
    # H1-closed-shell mislabeled onto Ir (open-shell) -> skipped, never run, surfaced.
    gen = OneShot([_av("BAD", "H1-closed-shell", ("Ir",))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                               convergence_rounds=1))
    assert "BAD" not in {r.avenue_id for r in rep.ledger.records}
    assert "BAD" in rep.digest
    assert "scope mismatch" in rep.digest.lower()


def test_correctly_scoped_avenue_still_runs():
    # H1-closed-shell on Pd (closed-shell) -> passes scope -> runs.
    gen = OneShot([_av("GOOD", "H1-closed-shell", ("Pd",))])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=3, proposals_per_round=3,
                                               convergence_rounds=1))
    assert "GOOD" in {r.avenue_id for r in rep.ledger.records}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/lab_loop/test_loop_scope.py -v`
Expected: FAIL — `test_scope_mismatched_avenue_is_skipped_not_run` fails (BAD is run / no "scope mismatch" in digest), because the guard isn't wired yet.

- [ ] **Step 3: Write minimal implementation**

In `src/orme_lab/lab_loop/loop.py`, add the import (extend the existing `from .runner ...` area, line ~22):

```python
from .hypotheses import validate_scope
```

In the intake loop, insert the scope check immediately after the `validate_runnable` skip block and before the `key = action_key(av)` line:

```python
                # Reject malformed avenues before they can raise deep in the run.
                ok, reason = validate_runnable(av)
                if not ok:
                    if av.id not in skipped_ids:
                        skipped_ids.add(av.id)
                        skipped.append((av.id, reason))
                    continue
                # Reject scope-mismatched avenues (mislabeled scoped hypothesis).
                ok_scope, scope_reason = validate_scope(av)
                if not ok_scope:
                    if av.id not in skipped_ids:
                        skipped_ids.add(av.id)
                        skipped.append((av.id, scope_reason))
                    continue
                # Drop unfalsifiable / already-run / already-buffered; buffer the rest.
```

Generalize the skip digest header (line ~108) from:

```python
        lines.append("## Skipped (malformed proposals — not run, not findings)")
```

to:

```python
        lines.append("## Skipped (not run, not findings — malformed or scope-mismatched)")
```

(The `"malformed"` substring is retained, so the existing `test_malformed_avenue_is_skipped_not_crashing` assertion `"malformed" in rep.digest.lower()` still passes.)

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/lab_loop/test_loop_scope.py tests/lab_loop/test_loop.py -v`
Expected: PASS (the two new tests + the existing loop tests, including the malformed-skip test).

- [ ] **Step 5: Commit**

```bash
git add src/orme_lab/lab_loop/loop.py tests/lab_loop/test_loop_scope.py
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: scope guard at intake — mislabeled scoped avenues skipped honestly'
```

---

### Task 3: keystone — independent retirement — and docs

**Files:**
- Test: `tests/lab_loop/test_hypothesis_split.py`
- Modify: `docs/hypothesis_matrix.md`

**Interfaces:**
- Consumes: the whole scoped-hypothesis path (Tasks 1–2).

- [ ] **Step 1: Write the failing test**

```python
# tests/lab_loop/test_hypothesis_split.py
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)
from orme_lab.lab_loop.config import LoopConfig
from orme_lab.lab_loop.triage import Verdict
from orme_lab.lab_loop.loop import run_loop


def _h1(aid, hyp, elements):
    # Falsifier fires when anisotropy is absent (< 0.05): closed-shell fires, open-shell does not.
    return Avenue(
        id=aid, tier=Tier.TIER1, description="H1 anisotropy probe", targeted_hypothesis=hyp,
        action=ActionSpec(elements, ("dimer",), ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


class OneShot:
    def __init__(self, avs):
        self._avs = list(avs)

    def propose(self, open_hypotheses, seen_actions, k):
        batch, self._avs = self._avs, []
        return batch


def test_scoped_variants_retire_independently():
    # THE FIX: closed-shell H1 is killed (Pd/Au/Ag anisotropy 0) while open-shell H1
    # SURVIVES (Ir/Os anisotropy > 0) in the SAME run -- neither reads inconclusive.
    gen = OneShot([
        _h1("closed", "H1-closed-shell", ("Pd", "Au", "Ag")),
        _h1("open", "H1-open-shell", ("Ir", "Os")),
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts["closed"] == Verdict.KILLED_HYPOTHESIS.value
    assert verdicts["open"] == Verdict.SURVIVED.value        # NOT inconclusive
    assert "H1-closed-shell" not in rep.ledger.open_hypotheses
    assert "H1-open-shell" in rep.ledger.open_hypotheses      # untouched by the other kill


def test_open_shell_not_globally_killed_by_closed_shell():
    # Order-independent: even if the closed-shell kill is processed first, the
    # open-shell claim stays open (they are separate registry entries).
    gen = OneShot([
        _h1("closed", "H1-closed-shell", ("Pd",)),
        _h1("open", "H1-open-shell", ("Ir",)),
    ])
    rep = run_loop(gen, loop_config=LoopConfig(max_avenues=9, proposals_per_round=9,
                                               convergence_rounds=99))
    verdicts = {r.avenue_id: r.verdict for r in rep.ledger.records}
    assert verdicts["open"] == Verdict.SURVIVED.value
```

- [ ] **Step 2: Run test to verify it fails or passes**

Run: `python3 -m pytest tests/lab_loop/test_hypothesis_split.py -v`
Expected: if Tasks 1–2 are correct this PASSES immediately. If it FAILS, fix the implicated module — do NOT edit the test to match a bug. (If `open` reads `inconclusive`, the registry split didn't take effect; if `closed` isn't killed, the falsifier/anisotropy path regressed.)

- [ ] **Step 3: Update the docs**

In `docs/hypothesis_matrix.md`, replace the single H1 row and single H3 row with their scoped variants, and add the measured class table. Insert this block where the H1/H3 rows currently sit (adapt to the surrounding table format — keep the existing column structure):

```markdown
| H1-open-shell | High-spin **open-shell** PGM units (d_shell_vacancies > 0: Ir, Os, Pt, Rh, Ru) show prolate rice-bean anisotropy | Anisotropy ~0 for an open-shell high-spin element | open |
| H1-closed-shell | High-spin **closed-shell** PGM units (d¹⁰: Ag, Au, Pd) show prolate anisotropy | Anisotropy > 0 for any closed-shell element (in the toy model it is 0 — this variant is expected to be refuted) | open |
| H3-cluster | Compact clusters are structurally stable (compactness controls stability) | A compact cluster scores unstable | open |
| H3-monomer | Isolated monomers carry structural stability | A monomer scores stable (in the toy model stability is 0 — expected refuted) | open |

**Why H1/H3 are element/geometry-scoped (measured):** `d_shell_vacancies` exactly predicts the
toy anisotropy — closed-shell (d¹⁰: Ag, Au, Pd) → 0.000 in both spin states; open-shell (Ir, Os,
Pt, Rh, Ru) → 0.165–0.458 in high-spin. A single binary H1 would be retired globally by the first
closed-shell counterexample even though it holds for open-shell elements; the scoped variants retire
independently. H3 splits the same way by geometry (compact_cluster stability 0.333 vs monomer 0.000).
The lab loop's `HYPOTHESES` registry (`src/orme_lab/lab_loop/hypotheses.py`) carries the scoped ids;
avenues target a scoped variant and a mislabeled one (wrong element/geometry class) is skipped.
```

- [ ] **Step 4: Run the whole suite**

Run: `python3 -m pytest -q`
Expected: all pass (the two keystone tests + everything from Tasks 1–2 + the pre-existing suite).

- [ ] **Step 5: Commit**

```bash
git add tests/lab_loop/test_hypothesis_split.py docs/hypothesis_matrix.md
git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com' commit -m 'lab_loop: keystone — scoped H1 variants retire independently; hypothesis_matrix updated'
```

---

## Self-Review (against the spec)

**Spec coverage:**
- §3 grounded class boundaries → Task 1 (`_all_elements_open/closed_shell` use `d_shell_vacancies`) + Global Constraints table + Task 3 docs.
- §4 scoped registry → Task 1 (`HYPOTHESES`).
- §5 `hypotheses.py` module + `validate_scope` + ledger rewire → Task 1.
- §6 guard wiring + generalized digest header → Task 2.
- §7 honesty/determinism → Task 1 (pure predicates), Task 2 (skip-not-run), Global Constraints.
- §8 bare-H1/H3-now-inconclusive consequence → documented in Task 3 docs; behavior falls out of the registry change (Task 1) since a non-registry target triages INCONCLUSIVE.
- §9 test strategy 1–5 → Task 1 (unit 1,2), Task 2 (guard 4), Task 3 (keystone 3, full suite 5).

**Placeholder scan:** none — every step carries real code and a runnable command. §11 open-questions resolved in the plan (named predicate functions per §11 recommendation; scratch generator not updated — out of scope, YAGNI).

**Type consistency:** `HYPOTHESES` / `SCOPE_PREDICATES` / `validate_scope(avenue) -> (bool, str)` identical across Tasks 1, 2, 3. Scoped ids `H1-open-shell`, `H1-closed-shell`, `H3-cluster`, `H3-monomer` identical everywhere. `validate_scope` consumed by `loop.py` (Task 2) exactly as produced (Task 1).

**Operator-reserved:** writes only under `src/orme_lab/lab_loop/`, `tests/lab_loop/`, `docs/`. No evidence-classification change, no repo-visibility change, pushes nothing. Merge/push are operator decisions at finish time.
