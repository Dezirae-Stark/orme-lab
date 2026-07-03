"""Subprocess orchestration for a live EPW run (pw -> ph -> nscf -> epw).

The pure helpers (deterministic scratch naming, positive completion
validation) are unit-tested. LiveEPWRunner.run needs the QE+EPW binaries and is
exercised only when they are present. Failures raise EPWError; the backend maps
them to EPWResult.failed so one candidate's failure never aborts a screen.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from typing import Protocol

from .approximant import PeriodicApproximant
from .config import EPWConfig


class EPWError(Exception):
    """A live EPW run failed (missing binary/pseudo, non-convergence, crash,
    timeout, or truncated output)."""


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


class LiveEPWRunner:
    """Real subprocess runner. available() gates on the three binaries; run()
    drives scf/ph/nscf/epw in a fresh per-candidate scratch dir under a new
    process group (so a timeout kills the whole MPI tree) and validates each
    stage positively before parsing."""

    @staticmethod
    def available(cfg: EPWConfig) -> bool:
        return all(shutil.which(b) for b in (cfg.pw_x, cfg.ph_x, cfg.epw_x))

    def run(self, approx: PeriodicApproximant, cfg: EPWConfig) -> str:
        from . import qe_input   # lazy import: Task 8

        if not self.available(cfg):
            raise EPWError("pw.x/ph.x/epw.x not all on PATH")
        prefix = scratch_name(approx)
        workdir = os.path.join(cfg.scratch_root, prefix)
        if os.path.exists(workdir):
            shutil.rmtree(workdir)
        os.makedirs(workdir, exist_ok=True)

        def _run(binary: str, deck: str, *, converge: bool) -> str:
            proc = subprocess.run(
                [binary], input=deck, cwd=workdir, text=True,
                capture_output=True, timeout=cfg.timeout_s, start_new_session=True,
            )
            assert_stage_complete(proc.stdout, require_convergence=converge)
            return proc.stdout

        _run(cfg.pw_x, qe_input.scf_input(approx, cfg), converge=True)
        _run(cfg.ph_x, qe_input.ph_input(approx, cfg, prefix), converge=False)
        _run(cfg.pw_x, qe_input.nscf_input(approx, cfg), converge=True)
        _run(cfg.epw_x, qe_input.epw_input(approx, cfg, prefix), converge=False)

        a2f_path = os.path.join(workdir, f"{prefix}.a2f")
        if not os.path.exists(a2f_path):
            raise EPWError(f"EPW produced no .a2f at {a2f_path}")
        return open(a2f_path, encoding="utf-8").read()
