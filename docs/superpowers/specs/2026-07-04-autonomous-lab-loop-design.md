# Autonomous Lab-Scientist Loop — Design Spec

**Date:** 2026-07-04
**Status:** Approved design, pre-plan. Next step: `writing-plans`.
**Author:** ORME Lab (operator: Desirae Stark)
**Seed:** the existing `orme-lab-scientist` subagent (`.claude/agents/orme-lab-scientist.md`).

---

## 1. What this is, and the one thing it must never do

A bounded, self-driving research loop for the ORME lab. It **divergently generates**
research avenues, **runs the simulated screening experiments itself**, **honestly triages**
the results, and **acts on its own suggestions** — retiring dead hypotheses in-sim and
proposing the next avenue or the decisive real-world measurement.

The loop can generate, triage, and prioritize *falsifiable predictions*. It **must never
conflate "survived my triage" with "validated."** Validation and reproducibility live at
physical evidence Levels 4–6 (independent, instrumented, reproducible measurement), which
this toy-model lab structurally cannot reach; everything the loop emits is clamped to
`LAB_CEILING` (Level 2). This is not a disclaimer bolted on the outside — §4 makes it a
property of the types.

**The honesty keystone (SCALAR's seam):** the creative part *proposes*, the deterministic
part *judges*, and they never swap roles. The `orme-lab-scientist` subagent proposes
avenues in divergent-invention mode; a pure, testable Python core runs and judges them. An
LLM ranking its own conjectures is idea-triage, not evidence — so the LLM never scores,
never validates. Cf. the cross-domain note
`~/.claude/research-wiki/cross-domain/scalar-txgraffiti-conjecturing-over-screen.md`.

## 2. Scope

**In (v1):** the deterministic core; tiers 1–2 of the action space; the `orme-lab-scientist`
subagent wired in as an injectable generator; ledger + digest; the full guard set.

**Reserved seam, deferred past v1:** tier-3 auto-prototyping of new model mechanisms as code.
The design reserves the seam and builds the *wall* (quarantine), but not the worktree-codegen
executor.

**Out:** anything that crosses an operator-reserved boundary (evidence-classification changes,
external claims/publication, repo/code changes, repository-visibility changes). The loop
*halts and surfaces* at these; it never acts on them.

## 3. Architecture

New in-repo subpackage `src/orme_lab/lab_loop/`. Deterministic core (pure, no LLM,
byte-reproducible given a fixed avenue stream — same determinism contract as the toy
pipeline; see §7):

| Module | Responsibility | Depends on |
|---|---|---|
| `avenue.py` | `Avenue` frozen dataclass: an executable experiment spec — the knobs it varies, the hypothesis it targets, an explicit falsification condition `F`, the predictor invariants it claims matter, provenance. Validation only, no behavior. | — |
| `closure.py` | Statically derive the AND-gate's transitive input-closure over `CandidateRecord` fields, and its complement (the *off-gate* invariants). The tautology oracle. | `pipeline`, `superconductivity` |
| `runner.py` | `run_avenue(avenue, config) -> AvenueResult` — execute an avenue through the existing `run_screen`. Deterministic. | `pipeline` |
| `triage.py` | Score an `AvenueResult` into an honest `Verdict` enum. Never "validated." | `closure` |
| `objective.py` | Composite acquisition function ranking passed avenues for selection. | `ledger` |
| `ledger.py` | Append-only deterministic memory of avenues + verdicts; open-hypothesis table; seen-set dedup; quarantine queue. | `avenue`, `triage` |
| `loop.py` | Bounded orchestrator + the generator Protocol seam + operator hard-stops + digest emission. | all of the above |

**The creative seam.** `loop.py` calls an injectable `AvenueGenerator` Protocol (same pattern
as `epw.runner.EPWRunner`, so tests stub it with a fixed avenue list). In production the
generator is the `orme-lab-scientist` subagent, prompted with the ledger + open hypotheses to
propose K new `Avenue` specs in divergent-invention mode. It proposes; it does not judge.

**Tier-3 wall.** A tier-3 avenue is *not run*. `loop.py` emits it as a `MechanismProposal`
to the quarantine queue (`status="pending operator + red-team review"`), never into the finding
ledger. The executor that would actually prototype code in a worktree is a reserved,
unimplemented seam.

## 4. The objective and the honesty guards

### 4.1 Tautology gate (before any scoring)

`closure.py` yields `off_gate_closure`. Each `Avenue` declares `predictor_invariants`. The
rule:

```
independence_ok := predictor_invariants ∩ off_gate_closure ≠ ∅
```

An avenue failing this claims a "finding" definitionally re-derivable from the AND-gate's own
inputs. It is dropped **before** the objective sees it — a hard filter, not a penalty. The loop
therefore structurally cannot spend its budget agreeing with itself.

**Honest limitation, stated not hidden:** today the only genuinely off-gate signal is the EPW
`sc_*` block (`sc_tc_kelvin`, `sc_lambda`, `sc_omega_log_k`, `sc_gap_mev`); coupling, carrier,
field-suppression, structural-stability, and observable-signal all fold back into the gate. And
the live EPW path has never run against real binaries. So v1's independent-*discovery* surface
is narrow — its early value is ruthless triage and decisive-experiment design. Widening the
off-gate invariant set is precisely what tiers 2–3 are *for*.

### 4.2 Composite objective (only ranks avenues that passed the gate and the falsifiability check)

```
A(avenue | ledger) = w_d · decisiveness + w_c · coverage
```

- **decisiveness** — deterministic information-gain over the hypothesis partition: does running
  this change the killed/survived status of any open hypothesis, or flip the ruled-out
  partition, relative to what the ledger already knows? Reproducing known state → ~0; killing or
  flipping → high. *A null result is a win.*
- **coverage** — distance in the (element × geometry × field × spin × mechanism) action space
  from the nearest already-run avenue. Exploration/tiebreak term.
- **candidate-strength is deliberately absent from the sum.** Recorded as a descriptive tag
  only; it can never raise an avenue's priority. This is the structural refusal of
  "chase survivors."

`w_d ≫ w_c` (decisiveness-dominant); weights live in `LabConfig`, inspectable and deterministic.

### 4.3 Must-be-able-to-fail (enforced twice)

1. **Static falsifiability check at proposal time.** `F` must be able to fire — there must exist
   a point in the avenue's declared action space where `F` is true and one where it is false. An
   avenue whose `F` can never fire (a "validation" that cannot fail) is rejected before it runs.
2. **Kill-as-success in triage.** `KILLED_HYPOTHESIS` advances the objective's realized value
   and retires the hypothesis from the open set.

### 4.4 Honesty guards (belt-and-suspenders over the existing `LAB_CEILING`)

- **Closed verdict vocabulary.** `Verdict = {KILLED_HYPOTHESIS, SURVIVED, TAUTOLOGICAL,
  INCONCLUSIVE}`. There is no `VALIDATED`/`CONFIRMED`/`SUPERCONDUCTING` member — honesty enforced
  by the type. A meta-test asserts no such member is ever added.
- **Evidence clamp reused.** Surviving-lead output runs through the existing
  `min(level, LAB_CEILING)` → Level ≤ 2. "Decisive real measurement" lines are Level-3
  *predictions of what to measure* and assert nothing at Level 4+.
- **Tier-3 quarantine.** `MechanismProposal` carries a pending-review status, never a verdict,
  never in the finding ledger.
- **Operator hard-stops** (from the operator's CLAUDE.md boundary). The loop halts and surfaces
  — never auto-acts — on anything touching evidence-classification changes, external
  claims/publication, repo/code changes, or crossing `LAB_CEILING`. Within-sim it is free.
- **Citation discipline inherited.** The generator subagent already carries "no fabricated
  citations or unread sources"; any digest line citing a number or paper routes through that, or
  speaks in textbook terms without attribution.

## 5. The ledger and how the loop acts

**`experiments/ledger/`** (in-repo, versionable, reviewable):

- **Append-only JSONL**, one record per avenue run: full `Avenue` spec, verdict,
  decisiveness/coverage scores, candidate-strength tag. Ordering by a **monotonic sequence
  index, never a clock** (determinism in the critical path). Any date is passed in from outside
  and stamped after the fact.
- **Open-hypotheses table** (status per H1–H7, H12, H14–H20), **seen-set** for dedup/convergence,
  and a **separate quarantine file** for tier-3 `MechanismProposal`s. Findings and quarantine
  never mix.
- **Digest** (markdown, written at budget end by the subagent from the deterministic ledger):
  ranked surviving leads at Level ≤ 2; retired hypotheses *with the avenue that killed them*; the
  decisive real-world measurement per surviving lead; the quarantined tier-3 proposals. This is
  the operator's review surface.

**How it acts, precisely.** *Within a run:* retires killed hypotheses (reshaping future
decisiveness scoring), dedups, selects and runs the next avenue, triggers EPW/EM computations —
all in-sim, zero external effect. *At a boundary:* emits digest + quarantine and stops. *Entry
points:* `python -m orme_lab.lab_loop --max-avenues N`, or conversational invocation that wires
the subagent in as generator.

## 6. Action space (tiers)

- **Tier 1** — vary existing model inputs: element, geometry (type/size/compactness), spin
  state, applied field, temperature, thresholds; trigger EPW `sc_*` and the EM-coherence
  (H12/H16) channel. Deterministic, fully testable, no code generation.
- **Tier 2** — additionally select among the charter's sanctioned coupling channels (nanocluster
  / granular Josephson network / oxide-hydroxide-salt phase / light–matter) as structured avenue
  types. Some of these need modeling work before they are runnable; the plan sequences that.
- **Tier 3** (reserved, walled) — invent and (in an isolated worktree) prototype a *new* model
  mechanism. Quarantined per §4.4; executor deferred.

## 7. Determinism boundary

The deterministic core is byte-reproducible *given a fixed avenue stream*. The loop as a whole
is not, because the LLM generator is non-deterministic — the same status the `sc_*` columns
already carry (external-solver / model nondeterminism). Tests pin the core by injecting a fixed
avenue list through the generator Protocol.

## 8. Test strategy (TDD, failing test first)

1. **Closure golden test** — off-gate set is exactly the EPW block; `coupling`/`carrier`/`field`/
   `stability`/`observable` are in-closure. Pinned, so a future model change that widens the gate
   breaks loudly.
2. **Tautology guard** — predictors ⊆ in-closure → `TAUTOLOGICAL`, never scored, never selected.
3. **Falsifiability static check** — un-fireable `F` rejected at proposal; fireable `F` accepted.
4. **Objective invariance to candidate-strength** — two avenues identical but for the strength
   tag → identical `A`.
5. **Null-result-is-progress** — an avenue whose `F` fires → `KILLED_HYPOTHESIS`, objective
   realized value increments, hypothesis leaves the open set.
6. **Ledger determinism + dedup** — repeat avenue deduped via seen-set; sequence-index ordering
   stable; no wall-clock.
7. **Loop termination** — bounded budget terminates; digest emitted; retirements reflected.
8. **Tier-3 quarantine** — tier-3 avenue → `MechanismProposal` in quarantine, absent from finding
   ledger, pending review.
9. **Verdict-vocabulary meta-test** — enum has no `validated`/`confirmed`/`superconducting`
   member.
10. **Operator hard-stop** — avenue flagged as touching a reserved boundary → loop halts and
    surfaces, does not auto-run.
11. **Adversarial whole-loop null** — a generator proposing *only* tautological avenues → zero
    findings, ~no budget wasted, digest honestly reports "no independent avenue found." Proves the
    loop can fail *as a whole*.

The generator is cleanly stubbable, so the core is fully unit-testable. With ~7 focused modules,
subagent-driven-development is the likely execution path (as with the EPW backend) — a plan-time
decision.

## 9. Open questions for the plan

- Exact weights `w_d`, `w_c` and the convergence/stop criterion (budget vs. "K rounds no new
  kill").
- Whether the digest lives in `experiments/` or is also mirrored to `research-wiki`.
- Tier-2 modeling gaps: which sanctioned coupling channels are runnable against current modules
  and which need new toy models first.
