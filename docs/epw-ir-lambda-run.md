# Ir per-element EPW λ — persistent run log

**Deployed:** 2026-07-04, as systemd system service `orme-ir-epw.service` (root).
**Plan:** `docs/superpowers/plans/2026-07-04-ir-per-element-epw-lambda.md`.
**Branch:** `feat/ir-epw-run`.

## What is running

An idempotent, checkpoint-driven supervisor (`scripts/ir_epw_supervisor.sh`) that
provisions QE 7.3.1 + EPW 5.8.1 from source and runs the three-tier Ir pipeline:

- **Tier 0 — non-magnetic Ir** (artificial unpaired=0): first d-electron validation
  of the pipeline; locks the Ir:d+s Wannier recipe; yields a non-magnetic λ.
- **Tier 1 — capability gate** (reads EPW source): does EPW 5.8.1 support collinear
  spin-polarized (`nspin=2`) electron-phonon coupling? If not → honest negative,
  Tier 2 skipped, Tier-0 λ is the ceiling.
- **Tier 2 — high-spin ORME Ir** (d⁷, 3 unpaired, `nspin=2`): the decision-relevant
  number for `H1-open-shell`. Only runs if Tier 1 clears.

Reference lattice **a = 3.988 Å** (cluster-NN counterfactual, NOT experimental Ir
3.839 Å). Every λ here is a **Level-2 phonon-channel counterfactual**, not a
superconductivity claim, and has **no external literature check** (see plan).

## Persistence + safeguards

- **Survives session/SSH/reboot:** systemd system service, `enable`d. A crash
  restarts and resumes from the last checkpoint; a clean park/stop stays put.
- **Kernel-enforced ceiling (cgroup v2):** `CPUQuota=1600%` (16 cores),
  `MemoryMax=32G`, `MemorySwapMax=0`, `Nice=15`, `IOWeight=10`. Cannot be exceeded
  by any bug; an OOM stays inside this cgroup and never targets operator services.
- **Soft back-off monitor:** SIGSTOPs *only our QE process group* if system
  MemAvailable < 15 G, scratch free < 30 G, or 1-min load > 60; SIGCONT when clear;
  parks if throttled > 40 min continuously.
- **PARK-not-burn:** any non-convergence / ambiguous gate stops cleanly (exit 0)
  with a reason in `/opt/orme-epw/state/PARKED`, instead of grinding resources.
- **Kill switch:** `scripts/ir_epw_ctl.sh stop`.

Control-plane behaviours (resume, partial-resume, kill-switch teardown, no orphans)
were validated in `DRY_RUN` before the real service launched.

## Observe / control

```
scripts/ir_epw_ctl.sh status     # stage, resources, checkpoints, results, park reason
scripts/ir_epw_ctl.sh tail       # follow the live journal
scripts/ir_epw_ctl.sh stop       # graceful stop (checkpointed; resumable)
scripts/ir_epw_ctl.sh resume     # clear stop/park, continue from checkpoint
```

State dir: `/opt/orme-epw/state/` — `status.json`, `done.<stage>` checkpoints,
`result_tier0.json` / `result_tier2.json`, `tier1_verdict.txt`, `*.log`.

## Honesty note on the automated gates

The supervisor auto-checks the gates it can decide deterministically (dynamical
stability from phonon frequencies, Tc from λ, and a Wannier-*convergence* proxy).
Two gates still want a human eye before any λ is trusted: the full **Wannier band
match** (proxy only in autonomous mode) and **λ grid-refinement** (single-grid in
v1, flagged `lambda-delta 0.0` with a note). A run reaching DONE is a *survived
triage*, not a validated result — fold the numbers in here and confirm those two
by hand before citing any λ.

## First live run (2026-07-04) — infra validated end-to-end; parked at the semicore Wannier gate

The service ran clean through **provision (QE+EPW built in ~2.5 min), SCF, DFPT
phonons, dvscf collection, and NSCF** for non-magnetic Ir, then reached the EPW
stage. Two real issues surfaced (both the "PGM Wannier defaults need tuning" caveat
made concrete); the first is fixed, the second is a human gate.

**Surprise:** the 1-atom primitive cell runs the whole SCF→ph→nscf chain in ~3
minutes, not the ½–1 day estimated (over-anchored to Pb). This is a minutes-scale
run, which is why the tuning was done live rather than via the scheduled check-in.

**Sanity (all real):** SCF converged in 8 iters, total energy −181.77 Ry, 29 k-pts,
Methfessel-Paxton smearing. NSCF Fermi energy **E_F = 21.545 eV**.

### Bug 1 (FIXED + codified): disentanglement window sat below the bands
The default dis windows were absolute `[-8, 20]` eV, but QE reports **absolute**
eigenvalues and Ir's E_F = 21.5 eV — so the window was entirely below the bands and
Wannier90 failed *"Energy window contains fewer states than number of target WFs."*
Fix: the EPW deck windows are now **Fermi-referenced** — `epw_input(..., fermi_ev=E_F)`
adds E_F to the cfg offsets (outer `[-12,+20]`, frozen `[-2,+1]` around E_F). The
supervisor parses E_F from `nscf.out` and regenerates `epw.in` before the EPW stage.
Confirmed live: this got EPW past Wannierization into the elph interpolation.

### Bug 2 (RESOLVED): semicore electron count vs the d+s manifold

**Resolved via the pseudo decision + explicit band exclusion.** Verified honest
finding: **no trustworthy 9-valence Ir pseudo exists** — SG15/PseudoDojo deliberately
include the 5s5p semicore for 5d metals to avoid ghost states (SG15 Ir file confirmed
Z_valence=17). So the semicore exclusion is unavoidable; switched to the SG15 ONCV
**norm-conserving** scalar-relativistic Ir pseudo (Hamann v3.3.0), which EPW's
Wannier/elph path prefers over the ultrasoft one anyway. Then EPW's own warning gave
the fix: *"dis_win_min is ignored … use `bands_skipped = 'exclude_bands = ...'`"* — it
does **not** exclude bands by energy window; you must name them. The 17-valence pseudo
has 4 semicore bands (5s+5p), so `bands_skipped = 'exclude_bands = 1:4'` leaves the
9 electrons (5d⁷6s²) the 6-band d+s manifold can hold. **Verified live:** *"Number of
excluded bands is (4)"*, *"Fermi level will be determined with 9.00000 electrons"*,
efermig succeeds, EPW computes the coupling (mass-enhancement λ accumulating ~0.5–0.9
over the 8000-point fine q-grid). Codified: `EPWConfig.n_semicore_bands` → the deck;
Ir sets it to 4. The three-fix chain that got Ir through real EPW:
**(1) Fermi-referenced windows → (2) norm-conserving pseudo → (3) explicit
`exclude_bands=1:4`.**

### (superseded) Bug 2 original framing
The SSSP pseudo `Ir_pbe_v1.2.uspp.F.UPF` carries **Z_valence = 15** (5p⁶ semicore +
5d⁷6s²), but the `nbndsub = 6` (d+s) Wannier manifold holds only 12 electrons. EPW's
fine-grid `efermig` then fails *"cannot bracket Ef"* — it did not exclude the 3 deep
5p semicore bands (it warned *"dis_win_min is ignored"* → `ibndstart=1` →
`nbndskip=0` → tried to place 15 e⁻ in 6 bands). In EPW 7.3.1 `nbndskip` is
**auto-derived** from `ibndstart` (not a settable namelist var), so the exclusion has
to be driven correctly, or the pseudo changed. Three resolution paths (a **decision**,
because a mis-set Wannier subspace yields a confidently-wrong λ):

1. **9-valence Ir pseudo** (5d⁷6s², no 5p semicore) → 6 bands hold 9 e⁻, EPW's happy
   path, no exclusion needed. Cleanest; EPW also prefers norm-conserving over this
   ultrasoft pseudo. Needs sourcing + verifying a trustworthy NC/9-val Ir UPF.
2. **Force the semicore exclusion** so EPW sets `ibndstart=4` (skip 3 bands, −6 e⁻):
   tune the nscf band count + dis window so the 5p bands are excluded and detected.
3. **Widen the active space** to `nbndsub=9` (Ir:p,d,s) — physically muddies the
   d+s-superconductivity picture; not preferred.

The supervisor now parks with a precise reason at this exact gate (efermig/semicore
and window-too-narrow are distinct, named park messages).

## Results

_(filled when the semicore gate is resolved — read `/opt/orme-epw/state/result_*.json`)_

- Tier 0 (non-magnetic) λ: **EPW running to completion (cgroup-capped service) — computing the α²F over the 8000-pt fine q-grid (~40 min); mass-enhancement λ accumulating ~0.5–0.9. Final λ / ω_log / Allen-Dynes Tc pending JOB DONE.**
- Tier 1 capability verdict: _pending (after Tier 0 converges)_
- Tier 2 (high-spin) λ: _pending / skipped_

**Reproducibility note:** the fix was proven on a hand-launched EPW run, then the
resource-capped systemd service was restarted to run the final EPW from the codified
`bands_skipped` deck — so the number, when it lands, comes from the managed pipeline,
not a manual edit. A scheduled check-in (CronCreate, every 30 min) pings on stage
transitions / DONE / PARK; it is session-only (the run's persistence is independent).

**Timeline correction:** SCF→ph→NSCF is ~3 min, but the EPW phonon-self-energy over
the 20³ fine q-grid is ~40 min — that stage, not DFPT, is the real per-element cost.
