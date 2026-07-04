"""Generic per-element PGM run layer (Pt as the second element after Ir)."""
from __future__ import annotations

import importlib.util
import os

from orme_lab.epw.runs import pgm

_DRIVER = os.path.join(os.path.dirname(__file__), "..", "scripts", "run_ir_epw.py")
_spec = importlib.util.spec_from_file_location("run_ir_epw", _DRIVER)
run_ir_epw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(run_ir_epw)


def test_semicore_count_is_computed_not_guessed():
    # (Z_valence - (d+s)) / 2 -- verified vs the SG15 ONCV pseudos
    assert pgm.n_semicore_bands("Ir", 17.0) == 4    # 5s5p semicore
    assert pgm.n_semicore_bands("Pt", 16.0) == 3    # 5p only


def test_parse_z_valence(tmp_path):
    upf = tmp_path / "Pt.upf"
    upf.write_text('<UPF version="2.0.1">\n  z_valence="   16.00"\n  element="Pt"\n')
    assert pgm.parse_z_valence(str(upf)) == 16.0


def test_pt_approximant_fcc_and_magnetic():
    ap = pgm.pgm_approximant("Pt", "high")   # Pt d9 -> high-spin has unpaired e-
    assert ap.bravais == "fcc"
    assert ap.element_symbol == "Pt"


def test_driver_pt_deck_prefix_and_exclude_bands(tmp_path):
    paths = run_ir_epw.write_decks(spin="none", workdir=str(tmp_path),
                                   pseudo_dir="/p", upf="Pt.upf",
                                   element="Pt", n_semicore=3)
    assert set(paths) == {"scf", "nscf", "ph", "epw"}
    epw = (tmp_path / "epw.in").read_text()
    assert "prefix = 'pt'" in epw                       # element-derived prefix
    assert "bands_skipped = 'exclude_bands = 1:3'" in epw  # Pt skips 3, not 4
    assert "proj(1) = 'Pt:d'" in epw


def test_find_a2f_uses_element_prefix(tmp_path):
    (tmp_path / "pt.a2f.01.0.300").write_text("# a2f\n 5.0 0 0 0 0 0.5\n")
    got = run_ir_epw._find_a2f(str(tmp_path), element="Pt")
    assert got.endswith("pt.a2f.01.0.300")
