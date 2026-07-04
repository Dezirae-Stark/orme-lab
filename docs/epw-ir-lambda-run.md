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

## Results

_(filled when tiers complete — read `/opt/orme-epw/state/result_*.json`)_

- Tier 0 (non-magnetic) λ: _pending_
- Tier 1 capability verdict: _pending_
- Tier 2 (high-spin) λ: _pending / skipped_
