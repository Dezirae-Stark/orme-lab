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

## 4. Remaining gap — the EPW final-stage deck is incomplete

`qe_input.epw_input` writes a minimal `&inputepw` (`elph`/`epwwrite`/`a2f` + grids) that a real
`epw.x` rejects. Grounded in the actual `epw.x` errors + EPW 5.8.1 source (`EPW/src/epw_readin.f90`):

1. **`phonselfen = .true.` is required** — `a2f` needs it (`epw_readin.f90:813`). Note QE's error
   message says "phonoselfen" but the namelist variable is **`phonselfen`** (message typo).
2. **Wannierization block missing** — without `wannierize = .true.` + `nbndsub` + projections
   (`proj(1)=...`) + `dis_win_max`/`dis_froz_max`, EPW fails at `loadbm (77): error opening ukk
   file` (it tries to read Wannier data that was never built). Projections are per-element
   (d + s orbitals for the PGMs).
3. **`dvscf_dir` + a phonon-collection stage missing** — EPW needs the phonon perturbation
   potentials gathered into a `save/` dir (the standard EPW `pp.py` step). The runner has no such
   stage between `ph.x` and `epw.x`.

Completing this is a scoped EPW-input-engineering task (per-element Wannier projections + the
dvscf-collection pipeline stage), best done iteratively against the real `epw.x` here.

## 5. Physical validation — not done, charter-gated

Even once the deck runs end-to-end, **no `sc_*` value is validated** until the pipeline
reproduces a published λ/Tc for a reference system (e.g. fcc Pb λ≈1.6 / Tc≈7 K, or Al). Per the
charter, no result may be called "validated" without that primary-source comparison. Live EPW is
also non-deterministic (MPI/BLAS) — the `sc_*` columns are not byte-reproducible (already noted
in `pipeline.py`).

## 6. Test-suite impact (env-robust)

Installing real QE flips `EPWBackend.available()` / `available_backends()` to non-empty, which
broke three tests that hard-coded "no ab-initio tools installed." Fixed to test the availability
*mechanism* (deps-absent backends excluded; an explicit `UnavailableEPWBackend` for the
unavailable path) rather than the ambient environment — so they pass with or without QE installed.
