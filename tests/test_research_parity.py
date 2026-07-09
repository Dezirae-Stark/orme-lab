"""Parity: web/research.js dossier entries must reproduce the Python authority.

The Research dossier states results (residuals, verdicts, isotope shifts, evidence
levels). This test parses research.js and asserts each stated result equals what the
screens/predictor actually compute, so the on-site dossier can never drift from the code.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from orme_lab.ir_contaminant import screen_contaminants
from orme_lab.control_experiment import _shift_for_bond, design_control_experiment
from orme_lab.thermal_stability import screen_thermal
from orme_lab.meissner_field import screen_meissner

_JS = Path(__file__).resolve().parents[1] / "web" / "research.js"
_WIDGET_IDS = {"pwIrSym", "pwIrLineLo", "pwIrLine", "pwThSym", "pwThT", "pwMeB"}
PATENT_RH = (1429.53, 1490.99)


def _entries():
    text = _JS.read_text()
    out = {}
    for body in re.findall(r"Object\.freeze\(\{(.*?)\n\s*\}\),", text, re.S):
        eid = re.search(r'id:\s*"([^"]+)"', body).group(1)
        out[eid] = body
    return out


def _num(body, key):
    m = re.search(rf"{key}:\s*(-?\d+(?:\.\d+)?)", body)
    return float(m.group(1)) if m else None


def _str(body, key):
    m = re.search(rf'{key}:\s*"([^"]+)"', body)
    return m.group(1) if m else None


def _preset_ids(body):
    m = re.search(r"inputs:\s*\{([^}]*)\}", body)
    return set(re.findall(r"(\w+):", m.group(1))) if m else set()


def test_all_expected_entries_present():
    e = _entries()
    assert {"ir-negative", "contaminant", "control-exp", "thermal", "meissner"} <= set(e)


def test_contaminant_result_matches_python():
    body = _entries()["contaminant"]
    r = screen_contaminants(PATENT_RH)
    assert _num(body, "residual") == pytest.approx(r.ranked[0][1], abs=0.01)
    assert _str(body, "verdict") == r.verdict


def test_control_experiment_result_matches_python():
    body = _entries()["control-exp"]
    r = design_control_experiment(PATENT_RH, metal_symbol="Rh")
    assert _num(body, "c13_shift") == pytest.approx(_shift_for_bond(1490.99, ("C", "O"), "13C"), abs=1.0)
    assert _num(body, "o18_shift") == pytest.approx(_shift_for_bond(1490.99, ("C", "O"), "18O"), abs=1.0)
    assert _num(body, "decisive_count") == r.decisive_count


def test_thermal_and_meissner_verdicts_match_python():
    e = _entries()
    assert _str(e["thermal"], "verdict") == screen_thermal("Ir", 1200).verdict
    assert _str(e["meissner"], "verdict") == screen_meissner(50e-6).verdict


def test_evidence_levels_valid_and_prediction_is_level_3():
    e = _entries()
    for eid, body in e.items():
        lvl = _num(body, "evidence_level")
        assert lvl in (1, 2, 3), f"{eid} has evidence_level {lvl}"
    assert _num(e["control-exp"], "evidence_level") == 3  # laboratory prediction
    for eid in ("ir-negative", "contaminant", "thermal", "meissner"):
        assert _num(e[eid], "evidence_level") <= 2  # screens stay clamped


def test_presets_reference_real_widget_ids():
    for eid, body in _entries().items():
        ids = _preset_ids(body)
        assert ids <= _WIDGET_IDS, f"{eid} preset references unknown ids: {ids - _WIDGET_IDS}"
