# tests/test_patent_web_parity.py
"""Pins the web widgets' physical constants to the authoritative Python screens,
so web/patent_tests.js cannot silently drift from src/orme_lab/."""
import pathlib
import re

import pytest

from orme_lab import ir_signature, meissner_field, thermal_stability
from orme_lab.ir_contaminant import _CONTAMINANTS

_JS = pathlib.Path(__file__).resolve().parents[1] / "web" / "patent_tests.js"


def _js_const(name: str) -> float:
    m = re.search(rf"export const {name}\s*=\s*([0-9eE.+\-]+)\s*;", _JS.read_text())
    assert m, f"{name} not found in patent_tests.js"
    return float(m.group(1))


def test_ir_constant_parity():
    assert _js_const("WAVENUMBER_CONST") == ir_signature.WAVENUMBER_CONST


def test_thermal_fraction_parity():
    assert _js_const("HUTTIG_FRACTION") == thermal_stability.HUTTIG_FRACTION
    assert _js_const("TAMMANN_FRACTION") == thermal_stability.TAMMANN_FRACTION


def test_meissner_constant_parity():
    assert _js_const("PHI0") == meissner_field.PHI0
    assert _js_const("MU0") == meissner_field.MU0
    assert _js_const("M_E") == meissner_field.M_E
    assert _js_const("E_CHARGE") == meissner_field.E_CHARGE


def _parse_js_contaminants(text: str):
    block = re.search(r"const CONTAMINANTS\s*=\s*\[(.*?)\];", text, re.S).group(1)
    rows = re.findall(r"\{[^}]*\}", block)
    out = {}
    for row in rows:
        name = re.search(r'name:\s*"([^"]+)"', row).group(1)
        # extract ONLY the lo/hi/d array contents (in that document order) so a
        # digit inside a species name like "NO3-" cannot leak into the numbers
        arrs = re.findall(r"(?:lo|hi|d):\s*\[([^\]]*)\]", row)
        nums = [float(x) for arr in arrs for x in arr.split(",") if x.strip()]
        out[name] = nums
    return out


def test_js_contaminant_table_matches_python():
    js = _parse_js_contaminants(_JS.read_text())
    assert len(js) == len(_CONTAMINANTS)
    for b in _CONTAMINANTS:
        assert b.name in js, f"{b.name} missing from JS mirror"
        py_nums = [b.lo_band[0], b.lo_band[1], b.hi_band[0], b.hi_band[1],
                   b.split_band[0], b.split_band[1]]
        assert js[b.name] == pytest.approx(py_nums), f"{b.name} band mismatch"
