# Orbital-order descriptor — live QE run log

**Task:** `docs/superpowers/plans/2026-07-23-orbital-order-descriptor.md`, Task 9
(acceptance contract + LIVE end-to-end validation). QE 7.3.1 binaries at
`/opt/qe/q-e-qe-7.3.1/bin`; ONCV pseudo `Ir_ONCV_PBE_sr.upf` at `/opt/orme-epw/pseudo`.

**Precondition:** MET. `pw.x` and `projwfc.x` are live and produce real Löwdin
d-occupations for the Ir compact-cluster periodic approximant; the computed path is
validated end-to-end through `evaluate_candidate`, not shipped inert.

## Run configuration

Candidate: `Ir`, `compact_cluster` (13-atom counterfactual cluster) → the
`build_approximant` periodic reference (fcc, single-atom cell, cell parameter from
the cluster nearest-neighbour distance), `high_spin` state.

`EPWConfig` built via `orme_lab.epw.runs.pgm.pgm_config("Ir", pseudo_dir, "Ir_ONCV_PBE_sr.upf",
n_semicore_per_atom=semicore_for_pseudo(...), n_atoms=1)` — the same recipe validated in
`docs/epw-ir-lambda-run.md` (SG15 ONCV norm-conserving pseudo, `n_semicore_bands=4`
skipping the Ir 5s/5p semicore so the 6-band d+s Wannier manifold — irrelevant here,
only SCF+projwfc run — holds the 9 valence electrons cleanly). `ecutwfc=60 Ry`,
`ecutrho=480 Ry`, `k_coarse=(8,8,8)`, `nspin=2`, `starting_magnetization=0.3`
(imposed high-spin start, per `unpaired_electrons/10` in `build_approximant`).

`ORBITAL_ORDER` runs only `pw.x` SCF → `projwfc.x` (`LiveEPWRunner.run_orbital_order`)
— no `ph.x`/`epw.x` stages; Löwdin d-occupations need only the converged SCF density.

## SCF (pw.x) — real output

```
convergence has been achieved in  11 iterations
!    total energy              =    -230.30536826 Ry
     the Fermi energy is    22.4295 ev
     total magnetization       =     0.00 Bohr mag/cell
     absolute magnetization    =     0.00 Bohr mag/cell
```

`JOB DONE` reached; `assert_stage_complete(..., require_convergence=True)` passed inside
the pipeline run (no exception). As in `docs/epw-ir-lambda-run.md`'s Tier-2 bulk result,
the imposed `starting_magnetization=0.3` self-consistently collapses to zero — the
periodic-bulk approximant is an itinerant metal and cannot hold the finite-cluster
high-spin local moment. This is a known, already-documented limitation of the *bulk
periodic approximant* (not of the orbital-order machinery): it means this run's
Löwdin d-occupations characterize the non-magnetic electronic structure at the Ir fcc
counterfactual lattice, not a genuinely spin-polarized state — consistent with, and no
worse than, the existing EPW λ run's own honesty note.

## projwfc.x — real Löwdin charges (Atom 1, only metal atom in the cell)

```
Atom #   1: total charge =  16.8000, s =  2.9767, p =  5.9979, d =  7.8254,
            spin up      =   8.4002, d =  3.9128, dz2=0.8446, dxz=0.7412, dyz=0.7412, dx2-y2=0.8446, dxy=0.7412,
            spin down    =   8.3999, d =  3.9125, dz2=0.8446, dxz=0.7411, dyz=0.7411, dx2-y2=0.8446, dxy=0.7411,
            polarization =   0.0003, d = 0.0003,
Spilling Parameter:   0.0118
```
`JOB DONE` reached; spin-summed per-orbital d-occupations (as parsed by
`parse_projwfc`, m-ordered `(dz2, dxz, dyz, dxy, dx2y2)`):

```
(1.6892, 1.4823, 1.4823, 1.4823, 1.6892)
```

Spilling parameter 0.0118 (small — the Löwdin projection basis captures the SCF
wavefunctions well).

## Computed descriptor (via `evaluate_candidate(..., compute_orbital_order=True, backend=QuantumEspressoBackend(config=epw_cfg))`)

```
source computed  P 0.03965982134870231  anisotropy 0.0
LIVE ORBITAL-ORDER VALIDATION PASSED
```

- `r.orbital_order_source == "computed"` — the ORBITAL_ORDER seam ran, was not absent/failed.
- `r.orbital_order_param = 0.03966` (off-gate polarization, `d_polarization`), `r.anisotropy = 0.0`
  (gate-facing `quadrupole_anisotropy`, overriding the toy value) — both finite, both in `[0,1]`.

**Independent hand cross-check** (not just trusting the pipeline's own arithmetic):
with `occ = (1.6892, 1.4823, 1.4823, 1.4823, 1.6892)`, mean `= 1.56506`,
`dev = sum|x-mean| = 0.49656`, `dev_max = 2*mean*4 = 12.52048` → `P = dev/dev_max =
0.03966` — matches the pipeline output to the printed precision.
`quadrupole_anisotropy`: weighted sum `w·occ` with `_QZZ = {dz2:+2, dxz:+1, dyz:+1,
dxy:-2, dx2y2:-2}` → `2·1.6892 + 1.4823 + 1.4823 − 2·1.4823 − 2·1.6892 = 0.0` exactly
→ `anisotropy = 0.0`. This zero is a real physical consequence of the fcc site's cubic
(`Oh`) point symmetry (the `eg` pair `{dz2, dx2−y2}` and the `t2g` triplet `{dxz, dyz,
dxy}` each fill symmetrically, and the specific `_QZZ` weights cancel across the two
sets under that symmetry) — not a degenerate/fabricated value.

## Separability note

The descriptor is computed at **fixed geometry + fixed magnetic (SCF `nspin=2`,
`starting_magnetization=0.3`) configuration** in one converged SCF run. This is
**computational isolation of cross-channel feedback** — the orbital, spin, and lattice
channels are not iterated against each other inside this run — and explicitly **NOT
physical separability**: orbital, magnetic, and lattice order are symmetry-locked
degrees of freedom in the real material and cannot be independently switched on/off.
(As observed above, the imposed magnetic starting point itself relaxed away
self-consistently, underscoring that this is one snapshot of one SCF minimum, not a
controlled separation of physical order parameters.)

## Verdict

Precondition MET; the ORBITAL_ORDER capability is live, not a stub. Evidence level is
unchanged (Level 2 — a computed descriptor is not a raised evidence level). No
fabricated numbers: every value in this log traces to a real `pw.x`/`projwfc.x` run
captured the same session, cross-checked by hand against `orbital_order.py`'s pure
functions.
