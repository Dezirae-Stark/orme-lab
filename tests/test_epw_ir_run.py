"""Tests for the Ir per-element run config, spin states, gates, and deck driver.
No live QE -- deck-only + pure-logic paths only."""
from __future__ import annotations

import importlib.util
import os

from orme_lab.epw.convergence import ConvergenceReport
from orme_lab.epw.runs import ir

_DRIVER = os.path.join(os.path.dirname(__file__), "..", "scripts", "run_ir_epw.py")
_spec = importlib.util.spec_from_file_location("run_ir_epw", _DRIVER)
run_ir_epw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_ir_epw)


# --- runs/ir.py ---

def test_ir_high_spin_is_spin_polarized():
    ap = ir.ir_approximant("high")
    assert ap.spin_polarized is True
    assert ap.starting_magnetization == 0.3
    assert round(ap.a_angstrom, 3) == 3.988
    assert ap.bravais == "fcc"


def test_ir_low_spin_still_magnetic():
    ap = ir.ir_approximant("low")
    assert ap.spin_polarized is True          # d7 low-spin still has 1 unpaired


def test_ir_none_spin_is_nonmagnetic_reference():
    ap = ir.ir_approximant("none")
    assert ap.spin_polarized is False         # artificial unpaired=0 calibration


def test_ir_config_pins_grids_and_windows():
    cfg = ir.ir_config(pseudo_dir="/pseudo", upf="Ir.upf")
    assert cfg.pseudo_for("Ir") == "Ir.upf"
    assert cfg.q_coarse == (4, 4, 4)
    assert cfg.nbndsub == 6


# --- convergence.py ---

def test_all_gates_pass_for_good_run():
    r = ConvergenceReport(wannier_band_max_dev_mev=3.0, lambda_grid_delta_frac=0.03,
                          min_phonon_freq_cm=12.0, lambda_value=0.41, tc_kelvin=0.2)
    assert r.gates() == {"wannier_match": True, "lambda_converged": True,
                         "dynamically_stable": True, "tc_computed": True}
    assert r.trustworthy() is True
    assert r.failing_gates() == []


def test_imaginary_phonon_fails_stability_gate():
    r = ConvergenceReport(wannier_band_max_dev_mev=3.0, lambda_grid_delta_frac=0.03,
                          min_phonon_freq_cm=-40.0, lambda_value=0.41, tc_kelvin=0.2)
    assert r.gates()["dynamically_stable"] is False
    assert r.trustworthy() is False
    assert "dynamically_stable" in r.failing_gates()


# --- driver deck-only ---

def test_driver_deck_only_writes_four_magnetic_decks(tmp_path):
    paths = run_ir_epw.write_decks(spin="high", workdir=str(tmp_path),
                                   pseudo_dir="/pseudo", upf="Ir.upf")
    assert set(paths) == {"scf", "nscf", "ph", "epw"}
    scf = (tmp_path / "scf.in").read_text()
    assert "nspin = 2" in scf
    assert "starting_magnetization(1) = 0.3" in scf
    epw = (tmp_path / "epw.in").read_text()
    assert "nbndsub = 6" in epw
    assert "proj(1) = 'Ir:d'" in epw


def test_driver_deck_only_none_spin_is_nonmagnetic(tmp_path):
    run_ir_epw.write_decks(spin="none", workdir=str(tmp_path),
                           pseudo_dir="/pseudo", upf="Ir.upf")
    assert "nspin = 2" not in (tmp_path / "scf.in").read_text()
