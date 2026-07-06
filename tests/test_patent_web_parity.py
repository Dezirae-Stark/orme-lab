# tests/test_patent_web_parity.py
"""Pins the web widgets' physical constants to the authoritative Python screens,
so web/patent_tests.js cannot silently drift from src/orme_lab/."""
import pathlib
import re

from orme_lab import ir_signature, meissner_field, thermal_stability

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
