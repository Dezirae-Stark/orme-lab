# EPW (Quantum ESPRESSO + EPW) backend seam — design spec

**Status:** draft for operator review · **Date:** 2026-07-03 · **Repo:** `Dezirae-Stark/orme-lab`

This spec was hardened by a five-agent verification pass (prior-art / citation
verification, skeptic, red-team, formalist, synthesis). Its findings are folded
in throughout; the full run is summarized in
[`research-wiki/prior-art/epw-allen-dynes-tc-citation-verification.md`](../../../research-wiki/prior-art/epw-allen-dynes-tc-citation-verification.md).

---

## 1. What this is, and the framing that is non-negotiable

The EPW backend wires the one path in the ORME Lab architecture that computes a
real electron–phonon superconducting Tc: `α²F(ω) → λ, ω_log, ω̄₂ → Allen–Dynes
Tc`. It is the "endgame" seam behind `Capability.SC_GAP` on the `DFTBackend`
interface, which is currently **declared but never consumed** by the pipeline.

**Two framings are load-bearing and appear verbatim in the package docstring,
the `backends.py` SC_GAP docstring, the spec, and anywhere the number surfaces:**

1. **This is a phonon-channel screening counterfactual, not a superconductivity
   estimate for the ORME claim.** EPW computes the phonon-mediated, **spin-singlet**
   Tc of an **imposed periodic reference lattice** inferred from a cluster's
   nearest-neighbour distance and forced into the high-spin state. It is *not* the
   finite cluster, *not* the ORME motif, and *not* any observed phase. For a
   high-spin magnetic system the physically relevant pairing channel is
   spin-fluctuation / triplet (a different Eliashberg kernel built on χ(q,ω), not
   α²F); Migdal's theorem is likely violated; and the Allen–Dynes formula contains
   **no magnetic pair-breaking term**, so it will return a finite, healthy-looking
   Tc in exactly the regime where the asserted magnetism would suppress singlet
   pairing. **A returned Tc is not evidence the material superconducts.** At most
   this seam can support *phonon-mechanism ruling-out*, never a positive ORME Tc.

2. **Evidence stays capped at Level 2** (`SIMULATION_CANDIDATE`) whether or not
   EPW ran. A wired, live-binary run does **not** raise the evidence level.

These are the skeptic's categorical findings, not error bars. If the design ever
drifts toward presenting the Tc as "the ORME superconductivity estimate," it has
failed.

## 2. Locked design decisions (from brainstorming)

1. **Full live pipeline**, binaries required for the end-to-end Tc run
   (`pw.x → ph.x → nscf → epw.x`, parsing real α²F). The deterministic components
   (deck writer, `.a2f` parser, moment math, Allen–Dynes Tc) are unit-tested with
   fixtures — the verification floor holds without a supercomputer in CI.
2. **Structure = a periodic approximant** of the cluster/ORME high-spin motif
   (Bravais lattice from the nearest-neighbour distance; spin-polarized from the
   high-spin state). Explicitly counterfactual (§1).
3. **Report Tc alongside** the five-gate triage "screening score," which is
   unchanged. New record fields; evidence capped at Level 2.

## 3. The physics (verified)

**Verification status.** All eight numeric constants and the three moment
definitions below match Allen & Dynes 1975 (*Phys. Rev. B* **12**, 905) as
drafted from memory — confirmed via **secondary sources** (strongest:
arXiv:1905.06780 quoting the full Tc line with explicit A&D-1975 citation, plus
independent cross-checks of the Λ₁/Λ₂/f₁/f₂ forms), and the closed form
reproduces the EPW reference code's own Tc (§7). **The primary PRB papers
(Allen–Dynes 1975; McMillan 1968, *Phys. Rev.* **167**, 331) are paywalled and
were not obtained in hand** — see open decision O1. The BCS gap ratio 1.764 is
from BCS 1957, also secondary-confirmed. Module docstrings must carry this
caveat.

**Moments** (integrals of the Eliashberg spectral function α²F(ω)):

```
λ      = 2 ∫ α²F(ω)/ω dω
ω_log  = exp[ (2/λ) ∫ (α²F(ω)/ω) ln ω dω ]
ω̄₂     = [ (2/λ) ∫ α²F(ω) ω dω ]^(1/2)
```

**Tc — McMillan–Allen–Dynes:**

```
Tc = f₁ f₂ (ω_log / 1.20) · exp[ −1.04(1+λ) / ( λ − μ*(1 + 0.62λ) ) ]
f₁ = [ 1 + (λ/Λ₁)^(3/2) ]^(1/3),         Λ₁ = 2.46 (1 + 3.8 μ*)
f₂ = 1 + (ω̄₂/ω_log − 1) λ² / (λ² + Λ₂²),  Λ₂ = 1.82 (1 + 6.3 μ*)(ω̄₂/ω_log)
```

**Gap:** `Δ = 1.764 k_B Tc` (weak-coupling BCS; see must-fix G-GAP and open
decision O3 for the strong-coupling inconsistency).

**μ\*:** input, default `0.10`. Not computed — a fitted default; for magnetic
systems the effective μ* can be far larger or ill-defined for the singlet
channel. Never presented as derived.

**Unit contract:** Tc comes out in the same unit as ω_log. `spectral.py` returns
ω_log/ω̄₂ in the unit of the input ω grid; the caller converts to Kelvin before
`allen_dynes`. `k_B = 8.617333262e-2 meV/K`, so `1.764 k_B = 0.15200975874 meV/K`.

## 4. Architecture — the `src/orme_lab/epw/` subpackage

```
epw/
  approximant.py   ClusterGeometry + SpinState + Element → PeriodicApproximant
                   (Bravais lattice from nn-distance; fcc/hcp per element;
                    magnetization from the high-spin state). Raises
                    ApproximantUndefined for degenerate geometries (monomer).   [pure, tested]
  spectral.py      EliashbergFunction(ω grid, α²F): .lam, .omega_log, .omega_2.
                   Moment-integrand guards (§5 G-SPEC).                          [pure, tested]
  allen_dynes.py   allen_dynes_tc(λ, ω_log, ω̄₂, μ*) → Tc; bcs_gap(Tc).
                   Denominator guard (§5 G-DENOM).                               [pure, tested]
  qe_input.py      scf / nscf / ph / epw input-deck writers.                    [pure, tested]
  parse.py         parse the 11-column EPW `.a2f` → EliashbergFunction.         [pure, fixture-tested]
  runner.py        subprocess pw→ph→nscf→epw; positive completion validation;
                   deterministic per-candidate scratch; process-group timeout.  [integration, skipif]
  result.py        EPWResult(tc_kelvin, lam, omega_log_k, omega_2_k, gap_mev,
                   mu_star, source, unstable, provenance).                       [pure]
```

Everything above `runner.py` is deterministic and unit-tested now. `runner.py`
is the only piece needing QE+EPW installed, isolated behind `available()` and an
injectable runner so the backend→pipeline wiring is fully testable with a fake.

**`EPWBackend` (in `backends.py`):** `@implemented(Capability.SC_GAP)` **only**.
EPW's λ is electron–phonon coupling — conceptually distinct from the pipeline's
inter-unit orbital-overlap gate — so EPW does **not** implement
`INTER_UNIT_COUPLING`; λ is reported inside `EPWResult`. Constructor takes an
optional injected runner (default = the real one).

## 5. The five must-fix guards (all confirmed against the current code)

These are correctness gates, not niceties. Each ships with the regression test
named in §8.

- **G-DENOM (critical) — Allen–Dynes denominator.** `D = λ − μ*(1 + 0.62λ)`
  changes sign at `λ_crit = μ*/(1 − 0.62μ*)` (= 0.10660980810 for μ*=0.10). Below
  it the raw formula returns a spurious huge positive Tc (λ=0.05 → ~4×10¹¹ K), and
  a PGM approximant is exactly this weak-coupling case. **Before evaluating exp:
  if `D ≤ 0` or `λ ≤ 0` or `ω_log ≤ 0`, return Tc=0 and gap=0.** The physical
  "λ→0 ⇒ Tc→0" limit is `D→0⁺`, not literal λ→0.
- **G-SPEC (critical) — moment-integrand guards.** The 1/ω factor diverges at the
  ω≈0 first row and `0·ln 0` poisons the trapezoid with NaN. Skip/zero rows with
  `ω ≤ ω_min`; clip α²F to ≥0. If negative-frequency (unstable-mode) mass exceeds
  a tolerance, **mark the approximant dynamically unstable and return Tc=None** —
  never integrate over imaginary modes. (Forced high-spin FM order on a
  close-packed lattice is frequently dynamically unstable; λ is 1/ω-weighted and
  hypersensitive to soft modes.)
- **G-CAP (critical) — remove `INTER_UNIT_COUPLING` from
  `EPWBackend.declared_capabilities`.** `pipeline.py:150` already consumes that
  capability as gate #1 of the five-gate triage, so leaving it declared invites a
  future `@implemented` override to silently mutate the triage the charter says is
  unchanged. Add a test asserting `EPWBackend().provides()` is **exactly** {SC_GAP}.
- **G-GATE (critical) — gate on `provides(SC_GAP) ∧ available()`, per-candidate
  isolation.** The current idiom (`pipeline.py:137-158`) uses only the static
  `provides()`; on a box without QE it still enters the branch and, under
  "no silent fallback," would raise and **abort the whole 48-candidate screen** on
  the first candidate. Gate on `provides ∧ available`; wrap each per-candidate EPW
  call in try/except that records `sc_source="epw:failed"`, `sc_tc_kelvin=None`
  and **continues**. Add `pw.x` and `ph.x` to `EPWBackend.binary_requires`
  (currently only `epw.x`, so `available()` can be True while pw/ph are absent).
- **G-LEVEL (critical) — enforce the Level-2 cap in code.** `evidence.py`
  `LAB_CEILING = SIMULATION_CANDIDATE(2)` but `candidate_evidence_level` returns
  `LABORATORY_PREDICTION(3)` for not-ruled-out candidates and `pipeline.py:204`
  assigns it with **no clamp**. Wrap as `min(candidate_evidence_level(...),
  LAB_CEILING)`; test that no record (EPW present or absent) ever exceeds
  `LAB_CEILING`. This also surfaces a pre-existing Level-3-vs-charter-Level-2
  inconsistency — see open decision O4 (operator-reserved).

## 6. The other design corrections (from red-team)

- **G-COMPLETE (high)** — `runner.py` keys success on **positive** markers, not
  subprocess returncode (QE exits 0 on soft failures and writes truncated α²F):
  require `JOB DONE` per stage, `convergence has been achieved` for pw.x, the
  expected count of q-point dynmat files, treat any `CRASH` file as failure. Fail
  closed.
- **G-SCRATCH (high)** — deterministic per-candidate outdir/prefix keyed on
  `(element, geometry.label, spin_label)`, created fresh and torn down each run,
  `.save` asserted empty before scf. Prevents cross-contamination (candidate N+1
  reading N's stale `prefix.save`) and nondeterministic paths in logs.
- **G-DETERM (high)** — scope the determinism claim. `pipeline.py`'s "byte-identical
  output" promise applies to the **toy path (`backend=None`) only**; live EPW is
  not byte-reproducible (MPI/BLAS reduction order). Mark `sc_*` columns
  non-deterministic — see open decision O5.
- **G-UNIT (high)** — `k_B` in eV/K (`BOLTZMANN/EV_IN_JOULES`), `Δ_meV =
  1.764·k_B_eV·Tc·1000` (a naive `1.764·BOLTZMANN·Tc` is off by ~10¹⁹). Pin/assert
  the α²F frequency unit from the `.a2f` header in `parse.py`.
- **G-A2F (high)** — the raw `PREFIX.a2f` is **11 columns** (col 1 = ω in meV,
  cols 2–11 = α²F at 10 phonon-smearing `degaussq` values swept 0.05→0.50 meV).
  Select a mid-range smearing column (or expose the sweep for convergence). The
  human-readable 3-column variant (ω, α²F, cumulative λ(ω)) is a separate code
  path. **Re-verify exact column semantics against the installed EPW version's
  `a2f.f90`** — this came from EPW docs/forum, not the CPC-2016 text.
- **G-LSP (medium)** — widen the **abstract base** `DFTBackend.superconducting_gap`
  to `(element, geometry, spin_state)` in the same change as the override, so base
  and subclass agree (`provides()` is name-based and won't flag a mismatch). Keep
  the override named exactly `superconducting_gap` and `@implemented`. Contract
  test: `provides(SC_GAP)` True and the method accepts the triple.
- **G-DI (medium)** — make the injectable runner reachable through the registry:
  `get_backend(name, **kwargs)` (or a `set_runner`) so tests exercise the
  registry-constructed instance via `get_backend('epw', runner=fake)`.
- **G-MONO (medium)** — `approximant.py` raises typed `ApproximantUndefined` for
  geometries with no well-defined NN distance (monomer, arguably dimer); pipeline
  treats it as `sc_source="n/a"`, `sc_tc_kelvin=None`, toy gate untouched —
  explicitly, not by crashing. (`make_monomer` is first in `default_geometries`.)
- **G-CSV (medium)** — explicit sentinel policy: `sc_source` always present
  (`"toy"` / `"epw"` / `"epw:failed"` / `"n/a"`); absent floats written as `""`;
  add a golden **header** fixture so the six-column addition is a reviewed change.
- **G-KILL (medium)** — launch the runner with `start_new_session=True`; on
  `TimeoutExpired`, `os.killpg` the whole group (else `mpirun` grandchildren
  orphan and exhaust PIDs/FDs over 48 candidates).

## 7. Pipeline / record wiring + config

**Call site** (`pipeline.py::evaluate_candidate`, after the plausibility block):
```python
if backend is not None and backend.provides(Capability.SC_GAP) and backend.available():
    try:
        epw = backend.superconducting_gap(element, geometry, state)   # widened seam
    except ApproximantUndefined:
        epw = EPWResult.not_applicable()          # sc_source="n/a"
    except EPWError as e:
        epw = EPWResult.failed(str(e))            # sc_source="epw:failed"
else:
    epw = EPWResult.toy_absent()                  # sc_source="toy", all None
```
The five-gate score, `carrier_proxy`, `structural_stability`, etc. are computed
exactly as today, independent of `epw`.

**New `CandidateRecord` fields** (appended; `Optional`): `sc_tc_kelvin`,
`sc_lambda`, `sc_omega_log_k`, `sc_gap_mev`, `sc_mu_star`, and always-present
`sc_source`. `evidence_level = min(candidate_evidence_level(ruled_out),
LAB_CEILING)` (G-LEVEL).

**Config — `EPWConfig` dataclass owned by the backend at construction**
(keeps `LabConfig` clean): `mu_star=0.10`, plane-wave cutoffs, coarse/fine k&q
meshes, EPW smearing sweep + chosen column, `omega_min` cutoff, unstable-mode
tolerance, `pseudo_dir` (or `$ESPRESSO_PSEUDO`) + per-element UPF map, binary
paths, scratch root, Wannier projections, `spin_polarized`. All deterministic.
`available()` = `pw.x ∧ ph.x ∧ epw.x` on PATH ∧ pseudo dir ∧ element's pseudo
present.

## 8. Testing plan (formalist oracles — exact expected values)

**Deterministic core (`spectral.py`, `allen_dynes.py`) — write first, TDD:**

| Test | Input | Expected |
|---|---|---|
| `moments_spike_S1` | ω=[0,1,2,3,4], α²F=[0,0,1,0,0] | λ=1.0, ω_log=2.0, ω̄₂=2.0 (atol 1e-12) |
| `moments_spike_S2` | ω=[0..10], α²F[5]=2 | λ=0.8, ω_log=5.0, ω̄₂=5.0 (catches hardcoded-λ) |
| `moments_two_spike_S3` | ω=[0..5], α²F=[0,1,0,0,2,0] | λ=3.0, ω_log=4^(1/3)=1.58740105…, ω̄₂=√6=2.44948974… (ω_log≠ω̄₂ ⇒ swap bug fails) |
| `moments_box_S4` | α²F=0.5 on [1,4], 600001 pts | λ=1.3862944, ω_log=√(ab)=2.0, ω̄₂=2.3259644 (rtol 1e-4; log-vs-arith mean) |
| `moments_omega_zero_guards` | ω=[0,0.5,1], α²F=[0,0.3,0] | all finite (G-SPEC) |
| `moments_null_spectrum` | α²F all 0 | λ=0.0; defined sentinel; downstream Tc=0; never NaN |
| `ad_einstein_A1` **(golden)** | λ=1.0, ω_log=ω̄₂=300 K, μ*=0.10 | f1=1.0506796285, f2=1.0, Tc=**21.95067514 K** (rtol 1e-6) |
| `ad_mu_monotone_A2A3` | λ=1.0, ω_log=ω̄₂=300 K, μ*∈{.10,.13,.16} | Tc={21.95067514, 18.74239370, 15.69857840}, strictly ↓ |
| `ad_weak_A4` | λ=0.5, ω_log=ω̄₂=400 K, μ*=0.10 | Tc=4.95218473 K |
| `ad_strong_f2_A5` | λ=2.0, ω_log=250, ω̄₂=300 K, μ*=0.10 | f2=1.04798168, Tc=42.67473048 K (f2≠1 branch) |
| `ad_subcritical_zero_A6A7` **(G-DENOM regression)** | λ∈{0.10,0.05}, μ*=0.10 | Tc==0.0 exactly (else ~4e11 K) |
| `ad_just_above_crit` | λ∈{0.107,0.11} | 0.0 ≤ Tc < 1e-30, finite (clean underflow) |
| `ad_mu_zero_A8` | λ=1.0, ω_log=ω̄₂=300 K, μ*=0.0 | Tc=33.72638610 K |
| `bcs_gap_linear` | Tc=21.95067514 K; Tc=0 | Δ=3.33672 meV; Δ=0.0 |
| `end_to_end_spike` | ω=[0,150,300,450,600] K, α²F=[0,0,1,0,0] → spectral → allen_dynes | Tc=21.95067514 K, gap=3.33672 meV (pins Kelvin unit contract) |
| `unstable_mode_none` | a2f with neg-ω mass > tol | Tc=None (G-SPEC dynamically-unstable) |

**Parser / deck / wiring:** fixture 11-column `.a2f` → `EliashbergFunction`
round-trips λ; deck writer structural asserts (namelists, meshes, per-candidate
prefix); **backend↔pipeline via injected fake runner** returning a canned
`EliashbergFunction` → asserts record fields populate, `sc_source="epw"`, and
`evidence_level ≤ LAB_CEILING`; `provides()` == {SC_GAP}; `backend=None` screen
byte-identical to today in the pre-existing columns.

**Live runner:** `pytest.mark.skipif(not available())`; a single tiny smoke case
when binaries are present.

**Integration sanity (not a unit oracle):** EPW Tutorial-4 Pb tuple
(λ=1.1583616, ω_log=51.02 K, μ*=0.10 → EPW's own Tc=4.7481 K). ω̄₂ was not
tabulated, so feeding ω̄₂=ω_log gives 4.642 K — the 2.3% gap *is* the missing f₂.
Use only as a loose `4.5 < Tc < 5.0` end-to-end check; it is a coarse pedagogical
grid (converged/experimental Pb is λ≈1.5, Tc_exp=7.2 K), never a realism claim.

## 9. Determinism, honestly scoped

The moments, Allen–Dynes Tc, deck-writing, and parsing are byte-deterministic and
tested as such. The live QE/EPW run is **reproducible-to-convergence-tolerance**,
not byte-identical (MPI/BLAS reduction order perturbs the low digits of α²F). The
`pipeline.py` determinism guarantee is re-scoped to `backend=None`; `sc_*` columns
are documented non-deterministic. See open decision O5.

## 10. Prior-art / citations

Recorded in `research-wiki/prior-art/epw-allen-dynes-tc-citation-verification.md`
(in-repo). Verified: Allen & Dynes 1975 (PRB 12, 905); McMillan 1968 (PR 167,
331); Poncé, Margine, Verdi & Giustino 2016 (*Comput. Phys. Commun.* **209**, 116,
= arXiv:1604.03525, independently confirmed via ADS+arXiv); Margine & Giustino
2013 (PRB 87, 024505); BCS 1957 (PR 108, 1175). **Blocker to a "validated" label
(not to writing this spec or the deterministic core):** a recorded
EPW/Migdal-Eliashberg-in-magnetic-systems prior-art search must exist before the
seam is described as validated anywhere; the skeptic reasoned from canonical
theory and did not substitute for that search.

## 11. Open decisions reserved for the operator

- **O1 — primary-source bar.** Constants are secondary-source-confirmed and the
  form reproduces the EPW reference code, but the primary PRB pages (Allen–Dynes
  1975, McMillan 1968) were not obtained. Accept secondary + the recorded prior-art
  caveat, or require APS/library scans before finalizing?
- **O2 — geometry sensitivity band.** The NN→crystal map is under-determined
  (fcc vs hcp, hcp c/a). Proposed default: the element's actual ambient close-packed
  structure (fcc for Ir/Pt/Pd/Rh/Au/Ag, hcp for Os/Ru) with ideal c/a, optionally
  sweeping the alternative and reporting a band. Confirm the default convention.
- **O3 — strong-coupling gap.** Ship `Δ=1.764 k_B Tc` with a documented caveat, or
  suppress/flag the BCS gap above a λ threshold (≈1.5) where the true ratio exceeds
  1.764?
- **O4 — charter reconciliation (evidence classification; operator authority).**
  `candidate_evidence_level` emits Level 3 while the charter/`LAB_CEILING` caps at
  Level 2. The `min(level, LAB_CEILING)` clamp (G-LEVEL) enforces the cap
  conservatively, but *reconciling why Level 3 is emitted* is reserved to you.
- **O5 — live-run reproducibility policy.** Accept `sc_*` as explicitly
  non-deterministic, or require pinned MPI ranks/threads + Tc quantized to a
  documented precision to preserve a weakened determinism claim on the EPW path?

## 12. Out of scope

Anisotropic Migdal–Eliashberg (full gap-function solve), spin-fluctuation /
paramagnon kernels, geometry relaxation of the approximant, and any web-lab (JS)
surfacing of the Tc. The seam computes the isotropic Allen–Dynes Tc of the
approximant and reports it; nothing more.
