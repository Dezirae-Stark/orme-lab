# ORME Lab — local Claude proxy

`orme-claude-proxy.py` lets the ORME Lab web page use **Claude as the Lab
Scientist with your own credentials, gated to you**. It binds to `127.0.0.1`
(loopback), so only your machine can reach it — an outside party viewing the
public site cannot use your Claude.

## Run it

```bash
# Option A — your Max / Pro plan via Claude Code (gray-area for the raw API; see below)
ant auth login            # once, if not already logged in with Claude Code
python tools/orme-claude-proxy.py

# Option B — Anthropic Console API key (reliable)
ANTHROPIC_API_KEY=sk-ant-... python tools/orme-claude-proxy.py
```

It prints the active auth mode and listens on `http://127.0.0.1:8787`.

## Point the page at it

Open the lab (deployed, or `python -m http.server` in `web/`), expand
**Lab Scientist → Live Claude analysis → Local proxy**, click **check**. When it
shows `connected`, the "ask" box talks to Claude through your proxy. When the
proxy isn't running, the page falls back to the deterministic analyst (or a
direct Console API key if you saved one).

## Options

| Env var | Default | Meaning |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Console API key. Takes priority over the Max/OAuth path. |
| `ORME_PROXY_PORT` | `8787` | Listen port. |
| `ORME_PROXY_MODEL` | `claude-opus-4-8` | Default model (page can override per request). |
| `ORME_ALLOWED_ORIGINS` | `https://dezirae-stark.github.io` | Comma-separated extra page origins allowed to call the proxy. Any `localhost`/`127.0.0.1` port is always allowed. |
| `ORME_PROXY_TOKEN` | — | If set, the page must send a matching `x-orme-token` (set it in the proxy settings). Guards against other local processes. Recommended. |

## Honest caveats

- **Max/OAuth against the raw Messages API is a gray area.** It may be
  rate-limited differently, unsupported, or stop working. If the OAuth path is
  rejected (401), set `ANTHROPIC_API_KEY` to a Console key — that's the reliable
  path. The proxy tells you which mode it's using and surfaces a hint on 401.
- **Loopback only.** Do not change `HOST` to `0.0.0.0` — that would expose your
  credentials-backed endpoint to your whole network.
- **Origin-allowlisted.** Loopback alone does not stop other *web origins* open in
  your browser from calling the proxy, so the proxy grants CORS/Private-Network
  access only to the ORME Lab page's own origins (the GitHub Pages origin +
  localhost) and returns `403` to any other origin on `POST /claude`. A site you
  visit cannot drive your credentials. For an additional guard against other
  processes on your own machine, set `ORME_PROXY_TOKEN`.
- The proxy is a **local dev tool**; it is not part of the deployed static site
  and is never uploaded anywhere.
