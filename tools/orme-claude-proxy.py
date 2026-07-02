#!/usr/bin/env python3
"""ORME Lab -- local Claude proxy (loopback only).

Lets the ORME Lab web page talk to Claude as the *Lab Scientist* using YOUR
credentials, on YOUR machine, reachable only by you. It binds to 127.0.0.1, so
nothing outside your computer can reach it -- an outside party viewing the public
GitHub Pages site cannot use your Claude, because they cannot reach your loopback.

Auth resolution (first match wins):
  1. ANTHROPIC_API_KEY env var  -> Anthropic Console API key (RELIABLE path).
  2. Claude Code / `ant auth`   -> OAuth access token from your Max/Pro login.

  Honest caveat: using a Max/Pro OAuth token against the raw Messages API is a
  gray area -- it may be rate-limited differently, unsupported, or stop working.
  If the OAuth path misbehaves, set ANTHROPIC_API_KEY to a Console key instead.

Optional shared secret: set ORME_PROXY_TOKEN to require the page to send a
matching `x-orme-token` header (defense against other local processes). Configure
the same token in the page's proxy settings.

Run:
    python tools/orme-claude-proxy.py                 # default 127.0.0.1:8787
    ORME_PROXY_PORT=9000 python tools/orme-claude-proxy.py
    ANTHROPIC_API_KEY=sk-ant-... python tools/orme-claude-proxy.py   # console key

No third-party dependencies -- standard library only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"  # loopback ONLY -- do not change to 0.0.0.0
PORT = int(os.environ.get("ORME_PROXY_PORT", "8787"))
SHARED_TOKEN = os.environ.get("ORME_PROXY_TOKEN", "")
DEFAULT_MODEL = os.environ.get("ORME_PROXY_MODEL", "claude-opus-4-8")
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"

SYSTEM_PROMPT = """You are the lab scientist embedded in "ORME Lab", a virtual lab that treats ORME/PGM high-spin ambient-superconductivity claims as falsifiable hypotheses to triage, never as settled fact.

Hard rules:
- Triage, not proof. The plausibility score can only say "not ruled out". Never call a candidate superconducting.
- The inter-unit coupling gate is decisive: an electronically isolated monatomic unit cannot host a bulk condensate. A surviving monomer would be a model bug.
- Zero resistance is NOT superconductivity -- bulk Meissner flux expulsion is a separate requirement.
- If the electromagnetic-coherence channel is strong while the SC gate fails, raise H12: the effect may be plasmonic/polaritonic coherence ("light flows through it"), not superconductivity.
- Ground everything in the provided scores and textbook condensed-matter physics. No fabricated citations.

Answer densely and directly: lead with the finding, then the reasoning, then the single most useful next experiment (and what would falsify the lead). Keep it under ~180 words unless asked for more."""


def resolve_auth():
    """Return (headers_dict, mode_str). mode in {'api-key','max-oauth','none'}."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if key:
        return (
            {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            "api-key",
        )
    # Try an OAuth access token from Claude Code / ant (Max/Pro login).
    for cmd in (["ant", "auth", "print-credentials", "--access-token"],):
        try:
            out = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
        token = (out.stdout or "").strip()
        if out.returncode == 0 and token and token.startswith("sk-"):
            return (
                {
                    "authorization": f"Bearer {token}",
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta": "oauth-2025-04-20",
                    "content-type": "application/json",
                },
                "max-oauth",
            )
    return ({}, "none")


def build_body(payload: dict) -> dict:
    context = payload.get("context", {})
    question = (payload.get("question") or "").strip()
    model = payload.get("model") or DEFAULT_MODEL
    user_text = (
        "Current candidate scores (toy models):\n"
        + json.dumps(context, indent=2)
        + "\n\n"
        + (f"Question: {question}" if question
           else "Analyze this candidate: what's happening, and what should I test next?")
    )
    return {
        "model": model,
        "max_tokens": 1024,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": user_text}],
    }


class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        origin = self.headers.get("Origin", "*")
        self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Vary", "Origin")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "content-type, x-orme-token")
        # Chrome Private Network Access: allow HTTPS public page -> loopback
        self.send_header("Access-Control-Allow-Private-Network", "true")

    def _json(self, code: int, obj: dict):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self._cors()
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _token_ok(self) -> bool:
        return not SHARED_TOKEN or self.headers.get("x-orme-token", "") == SHARED_TOKEN

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") == "/health":
            _, mode = resolve_auth()
            self._json(200, {"ok": True, "auth": mode, "model_default": DEFAULT_MODEL,
                             "token_required": bool(SHARED_TOKEN)})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path.rstrip("/") != "/claude":
            self._json(404, {"error": "not found"})
            return
        if not self._token_ok():
            self._json(401, {"error": "bad or missing x-orme-token"})
            return
        try:
            length = int(self.headers.get("content-length", "0"))
            payload = json.loads(self.rfile.read(length) or b"{}")
        except (ValueError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON body"})
            return

        headers, mode = resolve_auth()
        if mode == "none":
            self._json(503, {"error": "No credentials. Set ANTHROPIC_API_KEY, or log in with Claude Code / `ant auth login`, then restart the proxy."})
            return

        req = urllib.request.Request(
            ANTHROPIC_URL, data=json.dumps(build_body(payload)).encode("utf-8"),
            headers=headers, method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")
            try:
                detail = json.loads(detail).get("error", {}).get("message", detail)
            except json.JSONDecodeError:
                pass
            hint = ""
            if e.code == 401 and mode == "max-oauth":
                hint = " (Max/OAuth token was rejected for the API — set ANTHROPIC_API_KEY to a Console key instead.)"
            self._json(e.code, {"error": f"Anthropic API error {e.code}: {detail}{hint}"})
            return
        except urllib.error.URLError as e:
            self._json(502, {"error": f"could not reach Anthropic API: {e.reason}"})
            return

        text = "\n".join(b.get("text", "") for b in data.get("content", []) if b.get("type") == "text").strip()
        self._json(200, {"text": text or "(empty response)", "model": data.get("model"), "auth": mode})

    def log_message(self, fmt, *args):  # quieter logs
        sys.stderr.write("[orme-proxy] " + (fmt % args) + "\n")


def main():
    _, mode = resolve_auth()
    print(f"ORME Lab Claude proxy → http://{HOST}:{PORT}  (auth mode: {mode})")
    if mode == "none":
        print("  ⚠ No credentials found. Set ANTHROPIC_API_KEY, or run `ant auth login` (Claude Code / Max), then restart.")
    elif mode == "max-oauth":
        print("  Using Claude Code / Max OAuth token. If the API rejects it, set ANTHROPIC_API_KEY to a Console key.")
    if SHARED_TOKEN:
        print("  Shared token required (x-orme-token). Configure the same token in the page's proxy settings.")
    print("  Loopback only — not reachable from other machines. Ctrl-C to stop.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nstopped.")
