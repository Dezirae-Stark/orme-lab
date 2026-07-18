"""Parity: web/hypotheses.js + web/sim.js match the new pairing-symmetry hypotheses/proxy."""
import json
import re
import shutil
import subprocess

import pytest

from pathlib import Path
from orme_lab.lab_loop.hypotheses import HYPOTHESES
from orme_lab.magnetic_field import PairingSymmetry
from orme_lab.electromagnetic_coherence import magnetic_drive_response

_WEB = Path(__file__).resolve().parents[1] / "web"


def test_new_hypotheses_present_in_web_registry():
    js = (_WEB / "hypotheses.js").read_text()
    # web uses dashed ids; the split + drive hypotheses must each appear as a card id
    for token in ("H7-singlet", "H7-triplet", "H16-drive-triplet"):
        assert token in js, f"{token} missing from web/hypotheses.js"


def test_sim_js_has_drive_response_mirror():
    js = (_WEB / "sim.js").read_text()
    assert "magneticDriveResponse" in js
    # triplet-only gating mirrored (singlet -> 0)
    assert re.search(r'symmetry\s*===\s*"triplet"', js)


def _node(js):
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    out = subprocess.run([node, "--input-type=module", "-e", js],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def test_magnetic_drive_response_matches_js():
    sim_js = (_WEB / "sim.js").as_posix()
    py = magnetic_drive_response(0.8, 0.6, PairingSymmetry.TRIPLET)
    js_code = (f'import {{ magneticDriveResponse }} from "{sim_js}";'
               f'console.log(JSON.stringify(magneticDriveResponse(0.8,0.6,"triplet")));')
    js = _node(js_code)
    assert js == pytest.approx(py, abs=1e-9)
