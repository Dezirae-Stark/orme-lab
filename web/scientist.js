/*
 * scientist.js -- the in-browser "Lab Scientist".
 *
 * Two modes, both honest about the project's triage-not-proof framing:
 *
 *  1. Deterministic analyst (always on, no key). Reads the ACTUAL computed
 *     scores for the current candidate and produces grounded commentary: a
 *     plain-language reading, ranked next-experiment suggestions (it knows
 *     exactly which gate failed and why), and caveats. It cannot hallucinate
 *     the physics because it only ever restates the real pipeline output.
 *
 *  2. Optional real-Claude upgrade (bring your own Anthropic API key). Calls
 *     the Messages API directly from the browser with
 *     `anthropic-dangerous-direct-browser-access: true`. The key lives only in
 *     this browser's localStorage and is never committed or sent anywhere but
 *     api.anthropic.com. A Claude Max subscription does NOT work here -- that's
 *     a first-party-app credential, not an API key; use a Console API key.
 */

// ---------------------------------------------------------------------------
// 1. Deterministic analyst
// ---------------------------------------------------------------------------

const GATE_LABEL = {
  coupling: "inter-unit coupling",
  carriers: "carrier / coherence",
  field_tolerance: "field tolerance",
  structural_stability: "structural stability",
  observable_signal: "measurable observable",
};

// Physical remediation for each failed necessary-condition gate.
const GATE_FIX = {
  coupling: (r) =>
    r.geom.label === "monomer"
      ? "This is a monomer — the electronically isolated limit. It can never host a bulk condensate (H5). Pick a connected geometry (dimer → chain → compact cluster)."
      : "Coupling is below the bulk floor. Choose a more compact cluster (compact13/compact19) or reduce interatomic spacing so orbital overlap rises.",
  carriers: (r) =>
    r.scores.aniso > 0.75
      ? "Carrier proxy is starved by extreme anisotropy — a needle-like density localizes carriers (Peierls-like). Move toward a rounder ('rice-bean', not needle) state or a lower-spin configuration."
      : "Carrier proxy is low because coupling is weak. Raise coordination first; carriers track delocalization.",
  field_tolerance:
    () =>
      "The applied field exceeds this candidate's toy critical field. Lower the field, or read this as a field-fragile phase (H7) that isn't a robust superconductor.",
  structural_stability: () =>
    "The geometry is too fragile (low mean coordination) — chains and dimers relax away. Use a compact cluster to clear the stability floor.",
  observable_signal: () =>
    "No predicted observable clears the noise floor, so the claim is unfalsifiable as configured. Increase coupling/carriers so a Meissner-screening signal appears, or raise the moment (spin).",
};

/**
 * Produce deterministic commentary for one evaluated candidate result
 * (the object returned by SIM.evaluateCandidate).
 */
export function analyzeCandidate(r) {
  const s = r.scores;
  const reading = [];
  const suggestions = [];
  const caveats = [];

  const name = `${r.el.name} ${r.geom.label} (${r.st.isHigh ? "high" : "low"}-spin, ${r.st.unpaired} unpaired e⁻)`;

  // --- spin / shell sanity -------------------------------------------------
  if (r.st.unpaired === 0) {
    reading.push(
      `${name}: closed-shell / no unpaired electrons — the high-spin premise has nothing to act on here. Expect a diamagnetic, non-magnetic centre.`
    );
    suggestions.push("Switch to an element with a partially filled d-shell (Os, Ir, Rh) where a high-spin state actually exists.");
  } else {
    reading.push(
      `${name}: spin polarization ${s.spin.toFixed(2)}, density anisotropy ${s.aniso.toFixed(2)} (${s.bean ? "in the rice-bean band" : "outside the rice-bean band"}).`
    );
  }

  // --- the SC gate cascade -------------------------------------------------
  if (r.sc.ruledOut) {
    const failed = r.sc.gates.filter((g) => !g.passed);
    reading.push(
      `RULED OUT as a bulk-SC lead — fails ${failed.map((g) => GATE_LABEL[g.name]).join(", ")}.`
    );
    // rank fixes by gate order of necessity (coupling first)
    for (const g of failed) suggestions.push(GATE_FIX[g.name](r));
  } else {
    reading.push(
      `NOT RULED OUT — clears all five necessary gates, plausibility ${r.sc.score.toFixed(3)}. This is a screening lead, not evidence of superconductivity.`
    );
    suggestions.push("Escalate this candidate to a real calculation (ASE + PySCF/GPAW for the density, EPW for electron–phonon) — the toy score can't establish pairing.");
    suggestions.push("Decisive measurement: SQUID magnetometry for bulk Meissner screening. Zero resistance alone is not enough.");
    caveats.push("Even a positive plausibility is a triage signal. The gate can only ever say 'not ruled out'.");
  }

  // --- EM-coherence (H12/H16) cross-check ----------------------------------
  if (r.em.regime !== "weak") {
    const line = `Electromagnetic-coherence channel is ${r.em.regime} (plasmon ${r.em.plasmon.toFixed(1)} eV, split ${r.em.split.longitudinal.toFixed(1)}/${r.em.split.transverse.toFixed(1)} eV).`;
    reading.push(line);
    if (r.sc.ruledOut) {
      caveats.push(
        "H12 alert: strong plasmonic/polaritonic coherence with no SC gate passing is exactly the 'light flows through it' misidentification — measure optical/THz response, not just DC transport, to tell them apart."
      );
    } else {
      caveats.push(
        "This candidate is coherent in BOTH channels. Don't conflate them: rule out a plasmonic/polaritonic explanation (H16) before crediting superconductivity."
      );
    }
  }

  // --- field context -------------------------------------------------------
  if (s.supp === 0 && r.sc.gates.find((g) => g.name === "field_tolerance" && !g.passed)) {
    caveats.push("At the current applied field the order parameter is fully suppressed. Drop the field to test the zero-field phase.");
  }

  return { title: name, reading, suggestions, caveats };
}

// ---------------------------------------------------------------------------
// 2. Optional real-Claude upgrade (BYO Anthropic API key)
// ---------------------------------------------------------------------------

const KEY_STORE = "orme_lab_anthropic_key";
const MODEL_STORE = "orme_lab_claude_model";
const PROXY_URL_STORE = "orme_lab_proxy_url";
const PROXY_TOKEN_STORE = "orme_lab_proxy_token";

export const keyStore = {
  get: () => localStorage.getItem(KEY_STORE) || "",
  set: (k) => localStorage.setItem(KEY_STORE, k.trim()),
  clear: () => localStorage.removeItem(KEY_STORE),
  model: () => localStorage.getItem(MODEL_STORE) || "claude-opus-4-8",
  setModel: (m) => localStorage.setItem(MODEL_STORE, m),
};

// Local proxy (Claude Code / Max). Reachable only on this machine (loopback).
export const proxyStore = {
  url: () => (localStorage.getItem(PROXY_URL_STORE) || "http://127.0.0.1:8787").replace(/\/+$/, ""),
  setUrl: (u) => localStorage.setItem(PROXY_URL_STORE, u.trim()),
  token: () => localStorage.getItem(PROXY_TOKEN_STORE) || "",
  setToken: (t) => localStorage.setItem(PROXY_TOKEN_STORE, t.trim()),
  clearToken: () => localStorage.removeItem(PROXY_TOKEN_STORE),
};

// Shared context payload for both the proxy and the direct-key path.
function buildContext(result) {
  return {
    element: result.el.symbol,
    geometry: result.geom.label,
    spin: result.st.isHigh ? "high" : "low",
    unpaired_electrons: result.st.unpaired,
    scores: result.scores,
    superconductivity: {
      ruled_out: result.sc.ruledOut,
      plausibility: result.sc.score,
      gates: result.sc.gates.map((g) => ({ name: g.name, value: g.value, threshold: g.threshold, passed: g.passed })),
    },
    em_coherence: { regime: result.em.regime, plasmon_ev: result.em.plasmon, split: result.em.split, score: result.em.score },
  };
}

/**
 * Ping the local proxy's /health. Returns {auth, model_default, token_required}
 * on success, or null if it isn't running / unreachable.
 */
export async function pingProxy() {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 1500);
  try {
    const resp = await fetch(proxyStore.url() + "/health", { signal: ctrl.signal });
    if (!resp.ok) return null;
    return await resp.json();
  } catch (_) {
    return null;
  } finally {
    clearTimeout(timer);
  }
}

async function askViaProxy(result, question) {
  const headers = { "content-type": "application/json" };
  if (proxyStore.token()) headers["x-orme-token"] = proxyStore.token();
  const resp = await fetch(proxyStore.url() + "/claude", {
    method: "POST",
    headers,
    body: JSON.stringify({ context: buildContext(result), question, model: keyStore.model() }),
  });
  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) throw new Error(data.error || `proxy error ${resp.status}`);
  return data.text || "(empty response)";
}

/**
 * Route a Lab-Scientist question to Claude: prefer the local proxy (your Max /
 * Claude Code login, loopback-only), else a direct browser call with a saved
 * Console API key, else fail with guidance. Returns {text, via}.
 */
export async function ask(result, question) {
  const health = await pingProxy();
  if (health && health.auth && health.auth !== "none") {
    return { text: await askViaProxy(result, question), via: `local proxy (${health.auth})` };
  }
  if (keyStore.get()) {
    return { text: await askClaude(result, question), via: "browser API key" };
  }
  if (health && health.auth === "none") {
    throw new Error("Local proxy is running but has no credentials. Set ANTHROPIC_API_KEY or run `ant auth login`, then restart the proxy.");
  }
  throw new Error("No Claude connection. Start the local proxy (python tools/orme-claude-proxy.py) for your Max login, or add a Console API key below.");
}

const SYSTEM_PROMPT = `You are the lab scientist embedded in "ORME Lab", a virtual lab that treats ORME/PGM high-spin ambient-superconductivity claims as falsifiable hypotheses to triage, never as settled fact.

Hard rules:
- Triage, not proof. The plausibility score can only say "not ruled out". Never call a candidate superconducting.
- The inter-unit coupling gate is decisive: an electronically isolated monatomic unit cannot host a bulk condensate (there is nowhere for the macroscopic phase to live). A surviving monomer would be a model bug.
- Zero resistance is NOT superconductivity — bulk Meissner flux expulsion is a separate requirement.
- If the electromagnetic-coherence channel is strong while the SC gate fails, raise H12: the effect may be plasmonic/polaritonic coherence ("light flows through it"), not superconductivity.
- Ground everything in the provided scores and in textbook condensed-matter physics. No fabricated citations.

Answer densely and directly: lead with the finding, then the reasoning, then the single most useful next experiment (and what would falsify the lead). Keep it under ~180 words unless asked for more.`;

/**
 * Ask Claude about the current candidate, using the user's own API key.
 * Returns the assistant text. Throws with a readable message on failure.
 */
export async function askClaude(result, question) {
  const key = keyStore.get();
  if (!key) throw new Error("No API key set. Add an Anthropic Console API key first (a Max subscription won't work here).");

  const context = buildContext(result);

  const userText =
    `Current candidate scores (toy models):\n${JSON.stringify(context, null, 2)}\n\n` +
    (question?.trim() ? `Question: ${question.trim()}` : "Analyze this candidate: what's happening, and what should I test next?");

  const resp = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: {
      "content-type": "application/json",
      "x-api-key": key,
      "anthropic-version": "2023-06-01",
      "anthropic-dangerous-direct-browser-access": "true",
    },
    body: JSON.stringify({
      model: keyStore.model(),
      max_tokens: 1024,
      system: SYSTEM_PROMPT,
      messages: [{ role: "user", content: userText }],
    }),
  });

  if (!resp.ok) {
    let detail = `${resp.status}`;
    try {
      const j = await resp.json();
      detail = j?.error?.message || detail;
    } catch (_) { /* ignore */ }
    if (resp.status === 401) detail = "401 — key rejected. Use an Anthropic Console API key (not a Max/Claude.ai login).";
    throw new Error(detail);
  }
  const data = await resp.json();
  const text = (data.content || []).filter((b) => b.type === "text").map((b) => b.text).join("\n").trim();
  return text || "(empty response)";
}
