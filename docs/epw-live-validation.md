# EPW live-path validation status (2026-07-04)

First execution of the EPW backend's live path against **real** Quantum ESPRESSO / EPW,
recorded honestly: what is validated, one bug fixed, and the precise remaining gaps.
Nothing here is a validated *physical* result (no reference comparison yet — see §5).

## 1. Binaries — built from source (the distro build is broken)

The Debian `quantum-espresso` 6.7 package installs `pw.x`/`ph.x`/`epw.x` but its hardened
build **buffer-overflows (glibc FORTIFY `SIGABRT`) reading its own SSSP pseudopotentials** —
reproduced across ONCV (Pd) and USPP (Pt) pseudos, input-independent. Unusable.

Built upstream **QE 7.3.1 + EPW 5.8.1** from source (`gfortran 13.3`, OpenMPI, FFTW) at
`/opt/qe/q-e-qe-7.3.1/bin/`. This build runs correctly (no FORTIFY hardening). This is a
**host artifact, not committed** — it lives outside the repo.

Reproduce the config the live path uses:

```python
EPWConfig(
    pw_x="/opt/qe/q-e-qe-7.3.1/bin/pw.x",
    ph_x="/opt/qe/q-e-qe-7.3.1/bin/ph.x",
    epw_x="/opt/qe/q-e-qe-7.3.1/bin/epw.x",
    pseudo_dir="/usr/share/espresso/pseudo",         # quantum-espresso-data-sssp
    pseudopotentials=(("Pd", "Pd_ONCV_PBE-1.0.oncvpsp.upf"), ...),
)
```

## 2. Seams validated against real QE

Driving the repo's own deck writers (`qe_input.*`) through the real binaries, on fcc Pd
(minimal grids — a **plumbing** test, not converged physics):

- **SCF** (`scf_input` → `pw.x`): converges. Pt reference run: `total energy = -210.696 Ry`,
  converged in 9 iterations, `JOB DONE`. The SCF deck writer is correct.
- **Phonons** (`ph_input` → `ph.x`): runs and produces dynamical matrices (`dyn0..dyn3`,
  populated `_ph0/phsave`). The DFPT deck writer works.
- **NSCF** (`nscf_input` → `pw.x`): reaches `JOB DONE` (after the fix in §3).

## 3. Bug fixed — NSCF stage required SCF convergence

`epw/runner.py` ran the NSCF stage with `converge=True`, so `assert_stage_complete` required
the string `"convergence has been achieved"`. But NSCF is **non-self-consistent** — it reaches
`JOB DONE` and never prints that string — so every valid NSCF failed with the misleading
`"SCF did not report 'convergence has been achieved'"`. Fixed: NSCF now uses `converge=False`
(only `JOB DONE` / no-`CRASH` is the correct completion check). Verified: the live run now
clears the NSCF seam.

## 3b. REFERENCE VALIDATION PASSED — fcc Pb (2026-07-04)

The full chain was run end-to-end on the EPW **fcc-Pb** reference example against the source-built
binaries (reduced 3×3×3 q-grid, 16 cores): SCF → DFPT → **dvscf collection** → EPW-scf → EPW-nscf →
EPW Wannier interpolation → α²F → λ → Tc. Result:

- **λ (total) = 1.192** — matches the published Pb (woSOC) value ≈ 1.1–1.2.
- **Allen–Dynes Tc = 6.52 K** at μ\*=0.10 (experimental Pb Tc = 7.2 K; the ~0.7 K shortfall is the
  known spin-orbit contribution this without-SOC run omits).

This is the charter validation gate: the pipeline reproduces a **known superconductor's** electron-
phonon coupling and Tc. It validates the source build, the full workflow, the dvscf collection, and
that EPW's α²F output feeds `parse_a2f` correctly. (One flag gotcha found: `epw.x` requires
`nprocs = npool × nimage`, so launch it as `mpirun -np N epw.x -npool N`.)

## 4. EPW deck completion — DONE (structure validated), PGM Wannier params flagged

`qe_input.epw_input` now writes the full `&inputepw` matching the validated Pb structure, and the
runner has a `collect_dvscf` stage (mirrors EPW's `pp.py`, parallel/no-XML/no-PAW branch — the exact
path the Pb run used). Fixes landed and tested (`tests/test_epw_deck_complete.py`):

1. **`phonselfen = .true.`** added (`a2f` needs it; the QE error message's "phonoselfen" is a typo —
   the namelist variable is `phonselfen`).
2. **Wannierization block** added: `wannierize`, `nbndsub` (d+s = 6 default for PGMs), `proj('<El>:d')`
   + `proj('<El>:s')`, `dis_win/froz` windows.
3. **`dvscf_dir` + the collection stage** added — `collect_dvscf()` gathers `_ph0` potentials + dyn
   matrices into `save/`, exactly the missing `pp.py` step.
4. **Two more real bugs fixed in the same pass:** (a) `_atomic_blocks` wrote mass `1.0` for every
   element — a **critical** phonon bug (ω ∝ 1/√mass); now uses real amu (`ATOMIC_MASS_AMU`). (b)
   `nscf_input` used `K_POINTS automatic` (symmetry-reduced); EPW needs the **full uniform grid**,
   now emitted via `_uniform_kpoints`.

**STILL UNVALIDATED (honest):** the PGM-specific Wannier inputs (`nbndsub`, `proj`, `dis_win/froz`
windows) are *grounded defaults*, NOT converged per element. The Pb STRUCTURE is validated; a given
ORME PGM approximant's computed λ is **not** to be trusted until its Wannierization is tuned and
converged against real `epw.x` (transition-metal d-band disentanglement is finicky). Legacy §4 gap
detail retained below for provenance.

<details><summary>Original §4 gap (pre-completion, retained)</summary>

- `phonselfen` typo, Wannier block, and `dvscf_dir` + a phonon-collection stage were all missing.
  EPW needs the phonon perturbation potentials gathered into a `save/` dir (the standard `pp.py` step);
  the runner had no such stage between `ph.x` and `epw.x`.

</details>

## 5. Physical validation — reference DONE (Pb), per-ORME-candidate NOT

The reference gate is **cleared** (§3b: Pb λ=1.19, Tc=6.5 K reproduced). But **no `sc_*` value for
an ORME PGM approximant is validated** — each needs its Wannierization converged AND, ideally, a
sanity-check against literature for that element before its λ is trusted. Live EPW is also
non-deterministic (MPI/BLAS) — the `sc_*` columns are not byte-reproducible (noted in `pipeline.py`).

## 6. Test-suite impact (env-robust)

Installing real QE flips `EPWBackend.available()` / `available_backends()` to non-empty, which
broke three tests that hard-coded "no ab-initio tools installed." Fixed to test the availability
*mechanism* (deps-absent backends excluded; an explicit `UnavailableEPWBackend` for the
unavailable path) rather than the ambient environment — so they pass with or without QE installed.
