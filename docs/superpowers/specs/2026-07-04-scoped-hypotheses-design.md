# Scoped Hypotheses (H1/H3 split) — Design Spec

**Date:** 2026-07-04
**Status:** Approved design, pre-plan. Next: `writing-plans`.
**Author:** ORME Lab (operator: Desirae Stark)

---

## 1. Problem

The lab loop models each hypothesis as a single binary switch (`HYPOTHESES` in `ledger.py`,
retired atomically on the first refutation). But some hypotheses are **element/geometry-specific
truths**, so the first counterexample wrongly retires them globally. Observed in the earlier
faithful run: H1 ("high-spin PGM units show prolate anisotropy") was killed globally by a
closed-shell (Pd/Au/Ag, anisotropy 0) panel, and the Ir-supporting avenue (Ir anisotropy 0.385)
then read `INCONCLUSIVE` because H1 was already closed. H3 ("compactness controls stability")
showed the identical pathology (monomer stability 0 vs cluster 0.333).

## 2. Goal

Split H1 and H3 into scoped variants that are **independent registry entries**, so retiring the
class where a claim fails leaves open the class where it holds. Add a **grounded validation guard**
so a mislabeled scoped avenue (e.g. an `H1-closed-shell` avenue using Ir) is skipped honestly
rather than producing a bogus verdict.

## 3. Grounded class boundaries (measured, not assumed)

`d_shell_vacancies` (a real `Element` property) exactly predicts the toy anisotropy class,
because the toy anisotropy is driven by unpaired d-electrons, which require d-shell vacancies.
Measured (dimer, high-spin), verified before this design:

| class | elements | d_shell_vacancies | anisotropy (high-spin) |
|---|---|---|---|
| closed-shell | Ag, Au, Pd | 0 (d¹⁰) | 0.000 (all, both spins) |
| open-shell | Ir, Os, Pt, Rh, Ru | 1–4 | 0.165–0.458 (all positive) |

No fabrication: the boundary is a real property that matches the model's own behavior.

## 4. The scoped registry

Replace `H1` and `H3` in `HYPOTHESES` with:

- `H1-open-shell` — `d_shell_vacancies > 0` {Ir, Os, Pt, Rh, Ru}: high-spin units show prolate
  anisotropy → H1 holds (survives).
- `H1-closed-shell` — `d_shell_vacancies == 0` {Ag, Au, Pd}: even high-spin shows no anisotropy →
  H1 fails here (falsifier fires → retired).
- `H3-cluster` — `geometry_kinds ⊆ {compact_cluster}` (stability 0.333): compact clusters are
  stable → H3 holds.
- `H3-monomer` — `geometry_kinds ⊆ {monomer}` (stability 0.000): monomers carry no stability →
  H3-as-"these are stable" fails.

`H2, H4, H5, H6, H7, H12, H16` stay unscoped. **Naming:** `open-shell`/`closed-shell`, not `H1-Ir`
— the guard is grounded in d-shell filling, and Ir is only one of five open-shell members (Os shows
the strongest anisotropy, 0.458).

## 5. Structure — extract `lab_loop/hypotheses.py`

The hypothesis registry is now a growing concern that sat incidentally in `ledger.py`. Extract a
focused module `src/orme_lab/lab_loop/hypotheses.py`:

- `HYPOTHESES: tuple[str, ...]` — the scoped registry of §4.
- `SCOPE_PREDICATES: dict[str, callable]` — scoped-id → `predicate(action: ActionSpec) -> tuple[bool, str]`,
  grounded in `get_element(sym).d_shell_vacancies` (H1) and `action.geometry_kinds` (H3).
- `validate_scope(avenue) -> tuple[bool, str]` — if `avenue.targeted_hypothesis` is in
  `SCOPE_PREDICATES`, apply the predicate to `avenue.action`; otherwise return `(True, "")`
  (unscoped hypotheses always pass). An H1 predicate requires **all** elements to match the class;
  an H3 predicate requires **all** geometry kinds to match.

`ledger.py` imports `HYPOTHESES` from `hypotheses.py` (no behavior change; `open_hypotheses`
still filters `HYPOTHESES` minus killed).

## 6. Guard wiring (reuses the existing intake gate)

In `loop.py`'s proposal-intake loop, immediately after `validate_runnable(av)` passes, call
`validate_scope(av)`; on mismatch, append `(av.id, reason)` to the existing `skipped` list (with
the `skipped_ids` dedup) and `continue` — the avenue is never run. `loop.py` gains
`from .hypotheses import validate_scope`.

A scope mismatch is *runnable but mislabeled*, distinct from *malformed*. Generalize the digest
section header from `"Skipped (malformed proposals — not run, not findings)"` to
`"Skipped (not run, not findings — malformed or scope-mismatched)"` and let each entry's reason
string carry the specific cause (e.g. `"scope mismatch: H1-closed-shell requires closed-shell (d¹⁰)
elements, got Ir"`). One list, honest per-avenue reasons, no second collector. The header retains the
`"malformed"` substring, so the existing malformed-skip test still passes.

## 7. Honesty + determinism

- A mislabeled scoped avenue cannot produce a bogus kill — it is skipped and surfaced, not run.
- The two scoped variants are independent registry entries; retiring one never touches the other.
- `validate_scope` is pure (element lookup + property compare); no time/RNG. Evidence ceiling
  (`LAB_CEILING = 2`) unchanged. No fabricated physics — the boundary is a real element property
  matching measured behavior.

## 8. Consequence to state plainly

The earlier generator targeted unscoped `"H1"`/`"H3"`; those are no longer valid registry entries,
so an avenue targeting bare `"H1"` now reads `INCONCLUSIVE` (targeted hypothesis not open). The
generator contract updates to target the scoped variants. This is documented in
`hypothesis_matrix.md` and surfaced honestly (an inconclusive verdict, never a silent pass).

## 9. Test strategy (TDD)

1. `test_hypotheses.py`: `HYPOTHESES` contains `H1-open-shell`, `H1-closed-shell`, `H3-cluster`,
   `H3-monomer`; contains neither bare `"H1"` nor `"H3"`; still contains `H2,H4,H5,H6,H7,H12,H16`.
2. `validate_scope`: `H1-open-shell`+`("Ir",)`→ok, +`("Pd",)`→fail; `H1-closed-shell`+`("Pd","Au","Ag")`→ok,
   +`("Ir",)`→fail; `H3-cluster`+`("compact_cluster",)`→ok, +`("monomer",)`→fail; `H3-monomer`+`("monomer",)`→ok,
   +`("dimer",)`→fail; unscoped `H5`→always ok; mixed `("Ir","Pd")` under `H1-open-shell`→fail (not all match).
3. Integration keystone (`test_hypothesis_split.py`): one run with two avenues — `H1-closed-shell`
   on Pd/Au/Ag (`max_anisotropy < 0.05` fires → KILLED) and `H1-open-shell` on Ir/Os (does not fire
   → SURVIVED). Assert `H1-closed-shell` killed AND `H1-open-shell` SURVIVED (not inconclusive) —
   the literal before/after proof.
4. Integration guard: an `H1-closed-shell` avenue mislabeled onto Ir is skipped (not in records),
   with its scope-mismatch reason in the digest.
5. Full suite green (no existing test targets bare `"H1"`/`"H3"`; `ledger`'s open-hypotheses test
   compares against `HYPOTHESES` itself, self-consistent).

## 10. Files

| File | Change |
|---|---|
| `src/orme_lab/lab_loop/hypotheses.py` | Create: `HYPOTHESES`, `SCOPE_PREDICATES`, `validate_scope`. |
| `src/orme_lab/lab_loop/ledger.py` | Import `HYPOTHESES` from `hypotheses.py`; drop the local tuple. |
| `src/orme_lab/lab_loop/loop.py` | Call `validate_scope` at intake; generalize the skip digest header. |
| `docs/hypothesis_matrix.md` | Split H1/H3 rows into scoped variants with the measured class table. |
| `tests/lab_loop/test_hypotheses.py`, `tests/lab_loop/test_hypothesis_split.py` | New tests. |

## 11. Open questions for the plan

- Whether `SCOPE_PREDICATES` values are named module-level functions or lambdas (readability vs
  brevity) — recommend named functions for the traceback clarity.
- Whether to update the scratch `run_lab_loop.py` generator example to target scoped IDs (nice-to-have,
  not shipped).
