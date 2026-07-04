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
                         "dynamically_stable": True, "coupling_present": True,
                         "tc_computed": True}
    assert r.trustworthy() is True
    assert r.failing_gates() == []


def test_collapsed_coupling_fails_gate():
    # Pt Tier-0: phonons clean + Fermi surface full, but lambda~1e-5 -> the a2f is
    # empty; the coupling has collapsed and must NOT be certified trustworthy.
    r = ConvergenceReport(wannier_band_max_dev_mev=3.0, lambda_grid_delta_frac=0.0,
                          min_phonon_freq_cm=66.5, lambda_value=1.14e-05, tc_kelvin=0.0)
    assert r.gates()["coupling_present"] is False
    assert r.trustworthy() is False
    assert "coupling_present" in r.failing_gates()


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
    assert set(paths) == {"scf", "nscf", "ph", "q2r", "epw"}
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


def test_epw_windows_are_fermi_referenced(tmp_path):
    # QE reports absolute eigenvalues; the deck must add E_F so the disentanglement
    # window brackets the bands (the first live-run bug: [-8,20] sat below E_F=21.5).
    run_ir_epw.write_epw_deck(spin="none", workdir=str(tmp_path),
                              pseudo_dir="/p", upf="Ir.upf", fermi_ev=21.5)
    epw = (tmp_path / "epw.in").read_text()
    assert "bands_skipped = 'exclude_bands = 1:4'" in epw   # skip 5s+5p semicore
    assert "dis_win_min = 9.5" in epw      # -12.0 + 21.5
    assert "dis_win_max = 41.5" in epw     # +20.0 + 21.5
    assert "dis_froz_min = 19.5" in epw    #  -2.0 + 21.5
    assert "dis_froz_max = 22.5" in epw    #  +1.0 + 21.5


def test_parse_lambda_finds_suffixed_a2f(tmp_path):
    # EPW writes ir.a2f.<smear>.<temp>, NOT bare ir.a2f -- the parser must find it,
    # and must not pick the transport ir.a2f_tr.* file.
    (tmp_path / "ir.a2f_tr.01.0.300").write_text("# transport - must be ignored\n")
    (tmp_path / "ir.a2f.01.0.300").write_text(
        "# w  c1 c2 c3 c4 a2f\n 5.0 0 0 0 0 0.5\n 10.0 0 0 0 0 0.8\n 15.0 0 0 0 0 0.3\n")
    got = run_ir_epw._find_a2f(str(tmp_path))
    assert got.endswith("ir.a2f.01.0.300")


def test_epw_deck_enforces_crystal_asr_by_default(tmp_path):
    # lifc on by default (the q2r stage now generates save/ifc.q2r): the deck enforces
    # the crystal ASR so the Gamma acoustic modes are 0 (else the a2f/lambda collapse).
    run_ir_epw.write_epw_deck(spin="none", workdir=str(tmp_path),
                              pseudo_dir="/p", upf="Ir.upf", fermi_ev=21.5)
    epw = (tmp_path / "epw.in").read_text()
    assert "lifc = .true." in epw
    assert "asr_typ = 'crystal'" in epw


def test_q2r_deck_writes_ifc_to_dvscf_dir_with_crystal_asr(tmp_path):
    # q2r.x -> <dvscf_dir>/ifc.q2r, the exact path EPW's read_ifc_epw reads (lifc).
    run_ir_epw.write_decks(spin="none", workdir=str(tmp_path),
                           pseudo_dir="/p", upf="Ir.upf")
    q2r = (tmp_path / "q2r.in").read_text()
    assert "fildyn = 'ir.dyn'" in q2r
    assert "flfrc = './save/ifc.q2r'" in q2r
    assert "zasr = 'crystal'" in q2r


def test_epw_windows_absolute_without_fermi(tmp_path):
    # legacy path (no fermi) keeps absolute cfg values -- must not silently shift.
    run_ir_epw.write_decks(spin="none", workdir=str(tmp_path),
                           pseudo_dir="/p", upf="Ir.upf")
    epw = (tmp_path / "epw.in").read_text()
    assert "dis_win_min = -12.0" in epw
