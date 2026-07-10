"""Phase 3: exercise web/recorder.js via node (round-trip, defensive import, determinism).

recorder.js is pure/DOM-free, so we run it in node with an in-memory localStorage shim and
assert its data model + serializers behave. Skips if node is unavailable.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

_JS = Path(__file__).resolve().parents[1] / "web" / "recorder.js"


def _node(body: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node not available")
    script = (
        "const store = {};\n"
        "globalThis.localStorage = {\n"
        "  getItem: (k) => (k in store ? store[k] : null),\n"
        "  setItem: (k, v) => { store[k] = String(v); },\n"
        "  removeItem: (k) => { delete store[k]; },\n"
        "};\n"
        f'const R = await import("{_JS.as_posix()}");\n'
        f"{body}\n"
    )
    out = subprocess.run([node, "--input-type=module", "-e", script],
                         capture_output=True, text=True, timeout=30)
    assert out.returncode == 0, out.stderr
    return out.stdout.strip().splitlines()[-1]


def test_entry_roundtrip_and_markdown():
    d = json.loads(_node('''
const e = R.makeEntry({ id:"1", created:"2026-07-10T00:00:00Z", label:"my test",
  hypothesis:"H1", notes:"note body",
  snapshot:{state:{elSym:"Ir"}, vib:{on:true,species:"carboxylate"}, patent:{pwIrLine:1490.99}},
  outputs:{irOut:"metal-metal excluded"} });
R.addEntry(e);
const loaded = R.loadEntries();
const md = R.toMarkdown(e);
console.log(JSON.stringify({ n: loaded.length, id: loaded[0].id, el: loaded[0].snapshot.state.elSym,
  mdHasLabel: md.includes("my test"), mdHasHyp: md.includes("H1"), mdHasNote: md.includes("note body"),
  mdHasOut: md.includes("metal-metal excluded") }));
'''))
    assert d["n"] == 1 and d["id"] == "1" and d["el"] == "Ir"
    assert d["mdHasLabel"] and d["mdHasHyp"] and d["mdHasNote"] and d["mdHasOut"]


def test_validate_snapshot_is_defensive():
    res = json.loads(_node('''
const bad = [null, "str", 42, {}, {state:{elSym:{},evil:1,fieldT:0.5}, junk:{x:1}},
  {state:{elSym:"<script>alert(1)</script>"}}];
console.log(JSON.stringify(bad.map(b => R.validateSnapshot(b))));
'''))
    assert res[0] is None and res[1] is None and res[2] is None          # null/str/num -> null
    assert res[3] == {"state": {}, "vib": {}, "eigen": {}, "patent": {}, "loadedResearchId": ""}
    assert res[4]["state"] == {"fieldT": 0.5}                            # object + non-whitelist dropped
    assert res[5]["state"]["elSym"] == "<script>alert(1)</script>"       # kept as inert DATA (textContent'd downstream)


def test_markdown_deterministic():
    out = _node('''
const e = { id:"x", created:"C", label:"L", hypothesis:"H", notes:"N",
  snapshot:{state:{elSym:"Os"}}, outputs:{a:"1"} };
console.log(String(R.toMarkdown(e) === R.toMarkdown(e)));
''')
    assert out == "true"


def test_no_innerhtml_in_recorder():
    # recorder.js is DOM-free; ".innerHTML" (usage) must not appear. (A comment mentions the
    # word "innerHTML" without the leading dot, so match the code pattern, not the bare word.)
    assert ".innerHTML" not in _JS.read_text()
