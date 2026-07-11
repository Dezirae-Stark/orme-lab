"""Task 5 Step 4 smoke test: renderLedger's DOM output carries no literal
"HUDSON CLAIM VALIDATED" string and web/ledger.js never assigns innerHTML for
researcher/derived text. Runs renderLedger against a minimal Node DOM shim
(no jsdom dependency) rather than a browser.
"""
from __future__ import annotations
import re
import shutil
import subprocess
from pathlib import Path

import pytest

_JS = Path(__file__).resolve().parents[1] / "web" / "ledger.js"

_DOM_SHIM = r"""
class FakeStyle {}
class FakeElement {
  constructor(tag) {
    this.tagName = tag;
    this._className = "";
    this.children = [];
    this._text = "";
    this.title = "";
    this.style = new FakeStyle();
  }
  set className(v) { this._className = v; }
  get className() { return this._className; }
  appendChild(child) {
    this.children.push(child);
    this._text = "";
    return child;
  }
  set textContent(v) {
    this.children = [];
    this._text = v == null ? "" : String(v);
  }
  get textContent() {
    if (this.children.length === 0) return this._text;
    return this.children.map((c) => c.textContent).join("");
  }
}
global.document = {
  createElement: (tag) => new FakeElement(tag),
};
"""


def _node(js: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    script = _DOM_SHIM + js
    out = subprocess.run([node, "--input-type=module", "-e", script],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout


def test_no_innerhtml_assignment_in_ledger_js():
    src = _JS.read_text()
    assert not re.search(r"\.innerHTML\s*=", src), "web/ledger.js must never assign innerHTML (researcher text goes via textContent/createElement)"


def test_render_ledger_output_has_no_validated_string():
    js = (
        f'import {{ renderLedger }} from "{_JS.as_posix()}";'
        'const root = document.createElement("div");'
        "renderLedger(root);"
        "process.stdout.write(root.textContent);"
    )
    rendered = _node(js)
    assert rendered.strip(), "renderLedger produced no text content"
    assert "HUDSON CLAIM VALIDATED" not in rendered
