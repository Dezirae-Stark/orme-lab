"""Parity: web/vibration.js isotope data/math must mirror control_experiment.py.

The 3D viewer's isotope shift is a JS mirror of the Python authority. This test pins the
JS mass tables to the Python ones and confirms the intended shift values (−33 / −36 / 0)
match what control_experiment computes. The live JS formula is exercised by the Node smoke
test; here we lock the data source-of-truth and the reference outputs.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from orme_lab.control_experiment import _ISO, _LABEL, _shift_for_bond

_JS = Path(__file__).resolve().parents[1] / "web" / "vibration.js"


def _js_iso():
    block = re.search(r"export const ISO\s*=\s*\{([^}]*)\}", _JS.read_text()).group(1)
    return {k: float(v) for k, v in re.findall(r"(\w+):\s*([\d.]+)", block)}


def _js_label():
    block = re.search(r"export const LABEL\s*=\s*\{(.*?)\};", _JS.read_text(), re.S).group(1)
    return {k: (el, float(m)) for k, el, m in
            re.findall(r'"(\w+)":\s*\["(\w)",\s*([\d.]+)\]', block)}


def test_js_iso_masses_match_python():
    js = _js_iso()
    for sym, mass in _ISO.items():
        assert js[sym] == pytest.approx(mass), f"{sym} mass drift"


def test_js_label_masses_match_python():
    js = _js_label()
    for label, (el, mass) in _LABEL.items():
        assert js[label][0] == el
        assert js[label][1] == pytest.approx(mass), f"{label} mass drift"


def test_reference_shift_values_match_authority():
    # the JS is documented to reproduce these; confirm the Python authority agrees
    assert _shift_for_bond(1490.99, ("C", "O"), "13C") == pytest.approx(-33.0, abs=0.5)
    assert _shift_for_bond(1490.99, ("C", "O"), "18O") == pytest.approx(-36.0, abs=0.5)
    assert _shift_for_bond(1490.99, ("Rh", "Rh"), "13C") == 0.0
    assert _shift_for_bond(1490.99, ("C", "O"), "15N") == 0.0
