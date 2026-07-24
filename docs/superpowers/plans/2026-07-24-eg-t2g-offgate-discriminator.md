# eg–t2g speculative off-gate discriminator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move eg–t2g imbalance out of the gate anisotropy (gate reverts to full-quadrupole-only) and wire it as a Level-2, explicitly-SPECULATIVE off-gate against-`H7-triplet` discriminator, with every honesty invariant preserved.

**Architecture:** eg–t2g leaves `OrbitalResult.anisotropy` (which becomes `quadrupole_anisotropy` only) and becomes its own nullable `OrbitalResult`/`CandidateRecord` field, wired off-gate exactly like the existing `orbital_order_param` (P). It drives an `H7-triplet` falsifier `max_eg_t2g_imbalance > θ`, disclosed as speculation everywhere. Builds on PR #27; the prior (eg–t2g-in-gate) state is frozen at branch `orbital-order-followups-frozen` / tag `pr27-eg-t2g-in-gate` for reversion.

**Tech Stack:** Python 3 (stdlib), pytest, vanilla JS (`web/metrics.js`).

## Global Constraints

- No new Verdict members (no VALIDATED/CONFIRMED). **Evidence stays Level 2.**
- **Anti-tautology gate EXTENDED not weakened:** `eg_t2g_imbalance` added to pinned `OFF_GATE_INVARIANTS` (+ golden `tests/lab_loop/test_closure.py`), AND removed from the gate anisotropy so it is genuinely not re-derivable from the gate's scalar `anisotropy`.
- **Default path byte-identical:** gated behind `LabConfig.compute_orbital_order` (default off); flag off / backend absent → every existing `CandidateRecord` field + metric unchanged.
- **No positive scoring term, no new hypothesis** (reuses `H7-triplet`). eg–t2g only ever the against-triplet discriminator; never pairing/SC evidence.
- **Speculative disclosure MANDATORY** on every surface (module docstring, avenue provenance, `metrics.js`, changelog): *"SPECULATIVE — unverified extrapolation from the t2g-manifold requirement of the Hund's interorbital-triplet mechanism (Clepkens-Kee); NOT independently grounded, directionally redundant with the grounded P discriminator. 'Triplet' = Cooper-pair spin symmetry, NOT a local ionic spin multiplet."*
- Determinism: no time/RNG/order-dependent iteration.
- Commit as `git -c user.name='Dezirae Stark' -c user.email='deziraestark69@gmail.com'`; never AI-identity trailers.
- Branch `orbital-order-followups`. Run tests: `cd /orme-lab && python3 -m pytest`.

---

### Task 1: Gate reframe — gate anisotropy = full quadrupole only

**Files:** Modify `src/orme_lab/epw/orbital_result.py`, `src/orme_lab/orbital_order.py`, `tests/test_orbital_order.py`, `docs/epw-orbital-order-run.md`.

**Interfaces:** `OrbitalResult.from_occupations` uses `quadrupole_anisotropy` for `anisotropy`; `d_manifold_anisotropy` is deleted.

- [ ] **Step 1: Update the failing tests.** In `tests/test_orbital_order.py`, remove the `d_manifold_anisotropy` import and its four tests (`test_d_manifold_sees_cubic_split_where_quadrupole_is_blind`, `test_d_manifold_bounded_and_zero_for_equal`, `test_d_manifold_captures_axial_quadrupole_too`), and in `test_full_quadrupole_catches_in_plane_redistribution` replace the final `assert d_manifold_anisotropy(occ) > 0.0` with `assert quadrupole_anisotropy(occ) > 0.0  # gate uses the full quadrupole directly`. Keep the `eg_t2g_imbalance` import and its tests (eg–t2g stays a public function). Add:
```python
def test_gate_anisotropy_is_quadrupole_only_cubic_blind():
    # gate reframe: OrbitalResult.anisotropy is the full quadrupole ONLY; for cubic Ir it is 0.0,
    # honestly rank-2 (conservative). eg-t2g no longer enters the gate.
    from orme_lab.epw.orbital_result import OrbitalResult
    ir = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)
    r = OrbitalResult.from_occupations((ir,), source="qe:projwfc")
    assert r.anisotropy == pytest.approx(quadrupole_anisotropy(ir))
    assert r.anisotropy == pytest.approx(0.0, abs=1e-9)
```
- [ ] **Step 2: Run → FAIL** (`cd /orme-lab && python3 -m pytest tests/test_orbital_order.py -q`) — `d_manifold_anisotropy` still imported by orbital_result / test refs removed function.
- [ ] **Step 3: Implement.** In `orbital_result.py`: change the import to `from ..orbital_order import d_polarization, dominant_orbital, quadrupole_anisotropy`, and the aggregation to:
```python
        # gate-facing shape anisotropy: FULL rank-2 quadrupole tensor ONLY (real-space charge
        # shape). Honestly cubic-blind (0 for an Oh site, e.g. fcc Ir) = conservative; the cubic
        # eg-t2g split is now an OFF-GATE discriminator, not folded into the gate.
        aniso = sum(quadrupole_anisotropy(a) for a in per_atom) / n
```
In `orbital_order.py`: delete the `d_manifold_anisotropy` function entirely.
- [ ] **Step 4: Run → PASS**, full suite (`python3 -m pytest -q`).
- [ ] **Step 5: Update run-log.** In `docs/epw-orbital-order-run.md`, in the PR#27 follow-up note, change "the gate uses `d_manifold_anisotropy = max(full quadrupole, eg-t2g)`, which reads **0.0652**" to state the gate is now full-quadrupole-only (Ir gate anisotropy **0.0**, rank-2 conservative), and eg–t2g became a separate speculative off-gate discriminator (this PR).
- [ ] **Step 6: Commit** `feat: gate anisotropy = full quadrupole only (eg-t2g leaves the gate)`.

---

### Task 2: eg–t2g as a recorded off-gate field (OrbitalResult + CandidateRecord + pipeline)

**Files:** Modify `src/orme_lab/epw/orbital_result.py`, `src/orme_lab/pipeline.py`; Test `tests/test_orbital_pipeline.py`.

**Interfaces:** `OrbitalResult.eg_t2g_imbalance: float | None`; `CandidateRecord.eg_t2g_imbalance: float | None = None`.

- [ ] **Step 1: Failing tests** (add to `tests/test_orbital_pipeline.py`, matching its existing fake-backend fixture style):
```python
def test_eg_t2g_recorded_when_computed(fake_qe_backend):
    r = _rec(compute_orbital_order=True, backend=fake_qe_backend)
    assert r.eg_t2g_imbalance is not None
    assert r.eg_t2g_imbalance == pytest.approx(fake_qe_backend._orbital.eg_t2g_imbalance)


def test_eg_t2g_none_on_default_path():
    r = _rec(compute_orbital_order=False)
    assert r.eg_t2g_imbalance is None
```
(Extend the `fake_qe_backend`'s canned `OrbitalResult` to carry an `eg_t2g_imbalance` value.)
- [ ] **Step 2: Run → FAIL** — `OrbitalResult`/`CandidateRecord` lack `eg_t2g_imbalance`.
- [ ] **Step 3: Implement.**
`orbital_result.py`: add field `eg_t2g_imbalance: float | None` (after `polarization`); import `eg_t2g_imbalance` from `..orbital_order`; in `from_occupations` add `egt2g = sum(eg_t2g_imbalance(a) for a in per_atom) / n` and pass it: `return cls(aniso, pol, egt2g, dom, source, provenance)`. Update every constructor/null-object (`toy_absent`, `not_applicable`, `failed`) to pass `None` for the new field (keep positional order consistent — add `eg_t2g_imbalance` as the 3rd field so nulls read `cls(None, None, None, None, "src", reason)`).
`pipeline.py`: add to `CandidateRecord` (after `orbital_order_source`):
```python
    # SPECULATIVE off-gate against-triplet discriminator (eg-t2g crystal-field imbalance). Level 2,
    # never positive evidence; disclosed as an unverified extrapolation (see orbital_order.py).
    eg_t2g_imbalance: float | None = None
```
In the gated block, add `eg_t2g_imbalance: float | None = None` beside the orbital defaults, and in the computed branch (`if oo.anisotropy is not None:`) add `eg_t2g_imbalance = oo.eg_t2g_imbalance`. Pass `eg_t2g_imbalance=eg_t2g_imbalance` in the `CandidateRecord(...)` constructor (beside `orbital_order_param`).
- [ ] **Step 4: Run → PASS**, full suite (default byte-identical).
- [ ] **Step 5: Commit** `feat: record eg_t2g_imbalance as an off-gate field (OrbitalResult + CandidateRecord)`.

---

### Task 3: off-gate wiring (closure + metric + runner guard)

**Files:** Modify `src/orme_lab/lab_loop/closure.py`, `avenue.py`, `runner.py`, `tests/lab_loop/test_closure.py`; Test `tests/test_orbital_offgate.py` (extend).

- [ ] **Step 1: Failing tests** (add to `tests/test_orbital_offgate.py`):
```python
def test_eg_t2g_is_off_gate():
    from orme_lab.lab_loop.closure import OFF_GATE_INVARIANTS, GATE_INPUT_CLOSURE, is_independent
    assert "eg_t2g_imbalance" in OFF_GATE_INVARIANTS
    assert "eg_t2g_imbalance" not in GATE_INPUT_CLOSURE
    assert is_independent(("eg_t2g_imbalance",))


def test_eg_t2g_metric_range_and_guard():
    from orme_lab.lab_loop.avenue import METRIC_RANGES, FalsificationCondition, Comparator
    assert METRIC_RANGES["max_eg_t2g_imbalance"] == (0.0, 1.0)
    assert FalsificationCondition("max_eg_t2g_imbalance", Comparator.GT, 0.5).fireable()
```
- [ ] **Step 2: Run → FAIL.**
- [ ] **Step 3: Implement** (mirror `orbital_order_param` exactly):
  - `closure.py`: add `"eg_t2g_imbalance",` to `OFF_GATE_INVARIANTS` with a comment noting it comes from the computed orbital-resolved density and is SPECULATIVE-labeled.
  - `avenue.py`: add `"max_eg_t2g_imbalance": (0.0, 1.0),` to `METRIC_RANGES`.
  - `runner.py`: add `"max_eg_t2g_imbalance"` to `_METRIC_KEYS` and `_NONE_WHEN_UNMEASURED`; add `"max_eg_t2g_imbalance": _max_or_none("eg_t2g_imbalance"),` to the metrics dict; add a `validate_runnable` guard: `if m == "max_eg_t2g_imbalance" and not avenue.action.compute_orbital_order: return False, "max_eg_t2g_imbalance falsifier requires compute_orbital_order (needs a QE projwfc run)"`.
  - `tests/lab_loop/test_closure.py`: add `"eg_t2g_imbalance"` to the golden expected off-gate set.
- [ ] **Step 4: Run → PASS**, full suite.
- [ ] **Step 5: Commit** `feat: eg_t2g_imbalance off-gate wiring (closure golden + metric + runner guard)`.

---

### Task 4: speculative against-triplet discriminator + labeling + acceptance tests

**Files:** Modify `src/orme_lab/orbital_order.py` (docstring disclosure); Test `tests/test_orbital_offgate.py`, `tests/test_orbital_acceptance.py`.

**Interfaces:** discriminator semantics only (data-driven via `FalsificationCondition`); no new function.

- [ ] **Step 1: Add the disclosure** to `orbital_order.py`'s `eg_t2g_imbalance` docstring — append the mandatory SPECULATIVE paragraph verbatim from Global Constraints (t2g-mechanism extrapolation; not grounded; redundant with P; Cooper-pair vs ionic-multiplet disambiguation).
- [ ] **Step 2: Failing acceptance tests** (add to `tests/test_orbital_offgate.py`):
```python
def _av(target, metric, comp, thr, invariants):
    from orme_lab.lab_loop.avenue import Avenue, ActionSpec, Tier, FalsificationCondition, Comparator
    action = ActionSpec(("Ir",), ("compact_cluster",), ("high_spin",), 0.0, 300.0,
                        False, False, None, "undetermined", compute_orbital_order=True)
    return Avenue("a", Tier.TIER1, "d", target, action,
                  FalsificationCondition(metric, comp, thr), invariants, "SPECULATIVE eg-t2g")


def test_high_eg_t2g_kills_triplet():
    from orme_lab.lab_loop.runner import AvenueResult
    from orme_lab.lab_loop.triage import triage, Verdict
    from orme_lab.lab_loop.hypotheses import HYPOTHESES
    from orme_lab.lab_loop.avenue import Comparator
    av = _av("H7-triplet", "max_eg_t2g_imbalance", Comparator.GT, 0.5, ("eg_t2g_imbalance",))
    hi = AvenueResult(av, (), {"max_eg_t2g_imbalance": 0.8})
    lo = AvenueResult(av, (), {"max_eg_t2g_imbalance": 0.2})
    none = AvenueResult(av, (), {"max_eg_t2g_imbalance": None})
    assert triage(hi, frozenset(HYPOTHESES)).verdict == Verdict.KILLED_HYPOTHESIS
    assert triage(lo, frozenset(HYPOTHESES)).verdict == Verdict.SURVIVED
    assert triage(none, frozenset(HYPOTHESES)).verdict == Verdict.INCONCLUSIVE  # never fires on absent


def test_eg_t2g_anti_tautology_distinct_from_gate():
    # eg-t2g is now OUT of the gate: two occupations with the SAME gate anisotropy (both cubic ->
    # quadrupole 0) but DIFFERENT eg-t2g -> distinct off-gate value not derivable from the gate.
    from orme_lab.orbital_order import quadrupole_anisotropy, eg_t2g_imbalance
    a = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)   # eg > t2g
    b = (1.4823, 1.4823, 1.4823, 1.4823, 1.4823)   # equal fill
    assert quadrupole_anisotropy(a) == pytest.approx(quadrupole_anisotropy(b), abs=1e-9)  # same gate
    assert eg_t2g_imbalance(a) != pytest.approx(eg_t2g_imbalance(b))                        # different off-gate


def test_speculative_disclosure_present():
    import orme_lab.orbital_order as oo
    doc = oo.eg_t2g_imbalance.__doc__
    assert "SPECULATIVE" in doc.upper()
    assert "Cooper" in doc  # the ionic-vs-Cooper disambiguation
```
- [ ] **Step 3: Run → FAIL** (disclosure/tests), implement Step 1 disclosure, → PASS.
- [ ] **Step 4:** In `tests/test_orbital_acceptance.py` add a guardrail: toggling `compute_orbital_order` with a fake backend does not change any positive field (`sc_plausibility`, `credited_sc_lead`, `evidence_level`) — eg–t2g contributes no positive score; and `evidence_level <= 2` on the computed path. Run full suite.
- [ ] **Step 5: Commit** `feat: eg_t2g speculative against-triplet discriminator + disclosure + acceptance tests`.

---

### Task 5: UI honesty label + changelog + docs

**Files:** Modify `web/metrics.js`, `docs/epw-orbital-order-run.md`.

- [ ] **Step 1:** In `web/metrics.js`, add an `egT2gImbalance` entry: title "eg–t2g imbalance (model-derived, SPECULATIVE)", eyebrow "Off-gate discriminator (H7-triplet) — speculative", a `get(r)` returning the value with "computed" / "absent" provenance (mirror the `orbitalOrder` entry), a `definition`/`confidence` carrying the full SPECULATIVE disclosure + the Cooper-pair-vs-ionic-multiplet disambiguation, `source: "src/orme_lab/orbital_order.py"`. Match the existing "Toy (Level 2)" wording convention.
- [ ] **Step 2:** `cd /orme-lab && node --check web/metrics.js` + `python3 -m pytest -q`.
- [ ] **Step 3:** Append a changelog note to `docs/epw-orbital-order-run.md` (or the spec's Result section): eg–t2g moved gate→speculative off-gate discriminator; gate now full-quadrupole-only (conservative, cubic-blind); reversion point at `orbital-order-followups-frozen`/tag `pr27-eg-t2g-in-gate`; no invariant weakened, Level 2, physics disclosed as speculation.
- [ ] **Step 4: Commit** `feat(web+docs): eg-t2g speculative off-gate honesty label + changelog`.

---

## Final: update PR #27 (do not merge)

```bash
cd /orme-lab
git push origin orbital-order-followups
BODY="Orbital-order follow-ups, final design. (1) Runner dedup (_spawn_qe). (2) Gate anisotropy = FULL quadrupole tensor only (real-space charge shape; honestly rank-2 / cubic-blind = conservative). (3) eg-t2g imbalance moved OUT of the gate to a Level-2, explicitly-SPECULATIVE off-gate against-H7-triplet discriminator: prior-art returned SPECULATIVE-NOT-FOUND (no source links eg-t2g occupation to Cooper-pair symmetry; it is an unverified extrapolation from the t2g-manifold triplet mechanism and directionally redundant with the grounded P discriminator) — shipped labeled as speculation on every surface, with the Cooper-pair-vs-ionic-multiplet disambiguation. Anti-tautology gate EXTENDED (eg-t2g genuinely off-gate now that it left the gate), no VALIDATED, Level 2, default path byte-identical, no positive scoring term. Prior eg-t2g-in-gate state preserved at branch orbital-order-followups-frozen / tag pr27-eg-t2g-in-gate for reversion. Do not merge without operator review."
gh pr edit 27 -R Dezirae-Stark/orme-lab \
  --title "Orbital-order follow-ups: full-quadrupole gate + eg-t2g speculative off-gate discriminator" \
  --body "$BODY"
```
Report to the operator; do not merge — operator-reserved.
