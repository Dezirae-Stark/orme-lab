"""Subprocess orchestration for a live EPW run (pw -> ph -> nscf -> epw).

The pure helpers (deterministic scratch naming, positive completion
validation) are unit-tested. LiveEPWRunner.run needs the QE+EPW binaries and is
exercised only when they are present. Failures raise EPWError; the backend maps
them to EPWResult.failed so one candidate's failure never aborts a screen.
"""

from __future__ import annotations

import glob
import hashlib
import os
import shutil
import signal
import subprocess
from typing import Protocol

from .approximant import PeriodicApproximant
from .config import EPWConfig


class EPWError(Exception):
    """A live EPW run failed (missing binary/pseudo, non-convergence, crash,
    timeout, or truncated output)."""


def _read_nqpt(control_ph_xml: str) -> int:
    """Number of irreducible q-points from ph.x's control_ph.xml (mirrors EPW's
    pp.py get_nqpt: the count is on the line after the NUMBER_OF_Q_POINTS tag)."""
    with open(control_ph_xml, encoding="utf-8") as fh:
        lines = fh.readlines()
    for i, ln in enumerate(lines):
        if "NUMBER_OF_Q_POINTS" in ln:
            return int(lines[i + 1])
    raise EPWError(f"no NUMBER_OF_Q_POINTS in {control_ph_xml}")


def collect_dvscf(workdir: str, prefix: str, cfg: EPWConfig) -> None:
    """Gather ph.x's phonon perturbation potentials + dynamical matrices into the
    EPW dvscf_dir (mirrors EPW's pp.py, parallel / no-XML / no-PAW branch). epw.x
    reads dvscf_dir='./save' for the elph interpolation; without this stage it has
    no phonon potentials. Validated on the fcc-Pb reference (docs/epw-live-...)."""
    ph0 = os.path.join(workdir, "_ph0")
    save = os.path.join(workdir, cfg.dvscf_dir)
    os.makedirs(save, exist_ok=True)
    nqpt = _read_nqpt(os.path.join(ph0, f"{prefix}.phsave", "control_ph.xml"))
    for iq in range(1, nqpt + 1):
        shutil.copy(os.path.join(workdir, f"{prefix}.dyn{iq}"),
                    os.path.join(save, f"{prefix}.dyn_q{iq}"))
        if iq == 1:
            src = sorted(glob.glob(os.path.join(ph0, f"{prefix}.dvscf*")))
            if not src:
                raise EPWError(f"no dvscf potentials in {ph0} (did ph.x set fildvscf?)")
            shutil.copy(src[0], os.path.join(save, f"{prefix}.dvscf_q1"))
            dst = os.path.join(save, f"{prefix}.phsave")
            if not os.path.exists(dst):
                shutil.copytree(os.path.join(ph0, f"{prefix}.phsave"), dst)
        else:
            src = sorted(glob.glob(os.path.join(ph0, f"{prefix}.q_{iq}", f"{prefix}.dvscf*")))
            if not src:
                raise EPWError(f"no dvscf potentials for q{iq} in {ph0}")
            shutil.copy(src[0], os.path.join(save, f"{prefix}.dvscf_q{iq}"))


class EPWRunner(Protocol):
    def run(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        """Run the pipeline and return the raw PREFIX.a2f text, or raise EPWError."""
        ...


def scratch_name(approx: PeriodicApproximant) -> str:
    """Deterministic, filesystem-safe prefix keyed on the approximant identity
    (no wall-clock, no PID) so a screen's run directories are reproducible and
    never collide across candidates."""
    digest = hashlib.sha1(approx.label.encode("utf-8")).hexdigest()[:10]
    return f"orme_{approx.element_symbol}_{approx.bravais}_{digest}"


def assert_stage_complete(stdout: str, *, require_convergence: bool) -> None:
    """Fail closed unless the stage positively reports completion (QE exits 0 on
    soft failures, so returncode is not enough) -- G-COMPLETE."""
    if "CRASH" in stdout:
        raise EPWError("QE stage wrote a CRASH marker")
    if "JOB DONE" not in stdout:
        raise EPWError("QE stage did not reach 'JOB DONE' (truncated/killed run)")
    if require_convergence and "convergence has been achieved" not in stdout:
        raise EPWError("SCF did not report 'convergence has been achieved'")


def _spawn_qe(binary: str, deck: str, *, workdir: str, timeout_s: float, converge: bool) -> str:
    """Run one QE binary (deck fed via stdin) in ``workdir`` and return its stdout.

    Shared by LiveEPWRunner.run() and run_orbital_order(). Fail-closed as EPWError; on timeout,
    G-KILL the whole process group (mpirun + MPI ranks, not just the direct child) so one
    candidate's timeout never aborts the screen; then assert positive stage completion."""
    proc = subprocess.Popen(
        [binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, cwd=workdir, text=True, start_new_session=True,
    )
    try:
        stdout, _ = proc.communicate(input=deck, timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except ProcessLookupError:
            pass
        proc.wait()
        raise EPWError(f"{binary} timed out after {timeout_s}s") from exc
    assert_stage_complete(stdout, require_convergence=converge)
    return stdout


class LiveEPWRunner:
    """Real subprocess runner. available() gates on the three binaries; run()
    drives scf/ph/nscf/epw in a fresh per-candidate scratch dir under a new
    process group (so a timeout kills the whole MPI tree) and validates each
    stage positively before parsing."""

    @staticmethod
    def available(cfg: EPWConfig) -> bool:
        return all(shutil.which(b) for b in (cfg.pw_x, cfg.ph_x, cfg.epw_x))

    def run(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        if not self.available(cfg):
            raise EPWError("pw.x/ph.x/epw.x not all on PATH")
        from . import qe_input   # lazy import: Task 8

        prefix = scratch_name(approx)
        workdir = os.path.join(cfg.scratch_root, prefix)
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        def _run(binary: str, deck: str, *, converge: bool) -> str:
            return _spawn_qe(binary, deck, workdir=workdir, timeout_s=cfg.timeout_s, converge=converge)

        _run(cfg.pw_x, qe_input.scf_input(approx, cfg, prefix), converge=True)
        _run(cfg.ph_x, qe_input.ph_input(approx, cfg, prefix), converge=False)
        collect_dvscf(workdir, prefix, cfg)   # gather phonon potentials for epw.x
        # NSCF is non-self-consistent (calculation='nscf'): it reads the SCF
        # density and computes eigenvalues on the fine grid, reaching JOB DONE
        # but NEVER printing "convergence has been achieved". Requiring the SCF
        # convergence string here fails every valid NSCF run (found live vs real
        # QE 7.3.1). Only JOB DONE / no-CRASH is the correct completion check.
        _run(cfg.pw_x, qe_input.nscf_input(approx, cfg, prefix), converge=False)
        _run(cfg.epw_x, qe_input.epw_input(approx, cfg, prefix), converge=False)

        a2f_path = os.path.join(workdir, f"{prefix}.a2f")
        if not os.path.exists(a2f_path):
            raise EPWError(f"EPW produced no .a2f at {a2f_path}")
        with open(a2f_path, encoding="utf-8") as fh:
            return fh.read()

    def run_orbital_order(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        """Lightweight run for the ORBITAL_ORDER capability: pw.x SCF -> projwfc.x
        only (no ph/nscf/epw stages -- orbital occupations need just the converged
        SCF density). Returns projwfc.x's raw stdout (the "Lowdin Charges" block
        parse_projwfc reads); a fresh per-candidate scratch dir, same completion
        gating as :meth:`run`."""
        if not shutil.which(cfg.pw_x) or not shutil.which(cfg.projwfc_x):
            raise EPWError("pw.x/projwfc.x not both on PATH")
        from . import qe_input   # lazy import: Task 8

        prefix = scratch_name(approx)
        workdir = os.path.join(cfg.scratch_root, prefix)
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        def _run(binary: str, deck: str, *, converge: bool) -> str:
            return _spawn_qe(binary, deck, workdir=workdir, timeout_s=cfg.timeout_s, converge=converge)

        _run(cfg.pw_x, qe_input.scf_input(approx, cfg, prefix), converge=True)
        return _run(cfg.projwfc_x, qe_input.projwfc_input(approx, cfg, prefix), converge=False)
