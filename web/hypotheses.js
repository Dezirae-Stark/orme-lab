/*
 * hypotheses.js -- the Hypothesis Registry ("scientific notebook").
 *
 * The canonical, honest record of every hypothesis the lab tracks: what it
 * claims, where (if anywhere) it is modeled, its standing on the 0-6 evidence
 * ladder, and the decisive experiment that would advance or falsify it. Grounded
 * in docs/hypothesis_matrix.md and docs/terminology_translation.md.
 *
 * Nothing here is above Level 2 (simulation candidate): a modeled hypothesis has
 * been *rendered testable*, not confirmed. Experimental evidence is "none —
 * simulation only" across the board until a real lab weighs in.
 */

// Formalized evidence ladder (matches src/orme_lab/evidence.py).
const EVIDENCE_LABEL = [
  "concept",
  "mathematical consistency",
  "simulation candidate",
  "laboratory prediction",
  "initial observation",
  "independent replication",
  "established phenomenon",
];
export const evidenceBadge = (lvl) => `Level ${lvl}/6 — ${EVIDENCE_LABEL[lvl]}`;

// status ∈ modeled | partial | premise | roadmap
export const HYPOTHESES = [
  // ---- Core hypotheses (H1–H7, from the project spec) --------------------
  {
    id: "H-01", group: "core", level: 2, status: "modeled",
    statement: "PGM atoms or clusters may enter unusual metastable electronic configurations.",
    modeled: "spin_states.py",
    test: "DFT configuration search for metastable states; EPR/ESR + SQUID for the resulting moment.",
  },
  {
    id: "H-02", group: "core", level: 2, status: "modeled",
    statement: "High-spin states may deform the electron density into anisotropic shapes.",
    modeled: "electron_density.py",
    test: "Charge-density anisotropy from a DFT cube; XAS linear dichroism for orbital polarization.",
  },
  {
    id: "H-03", group: "core", level: 2, status: "modeled",
    statement: "The 'rice-bean' shape corresponds to electron-density anisotropy, a molecular-orbital density, or cluster geometry.",
    modeled: "electron_density.py · geometry.py",
    test: "Second-moment tensor of a DFT charge density; compare prolate ellipsoid vs MO density vs cluster shape.",
  },
  {
    id: "H-04", group: "core", level: 1, status: "premise",
    statement: "Bulk superconductivity requires an inter-unit coupling channel.",
    modeled: "coupling.py · superconductivity.py (encoded as a necessary gate)",
    test: "Structural premise, not a candidate — verified by theory (collective phase coherence needs a channel). Its bite is tested through H5.",
  },
  {
    id: "H-05", group: "core", level: 2, status: "modeled",
    statement: "If units are truly electronically isolated, superconductivity should fail.",
    modeled: "coupling.py (monomer → coupling 0 → ruled out)",
    test: "Transport + SQUID on an isolated-vs-connected series; a monomer must show no bulk Meissner screening.",
  },
  {
    id: "H-06", group: "core", level: 2, status: "modeled",
    statement: "Alternatives must be ruled out: nanoclusters, granular Josephson networks, plasmonic/polaritonic coherence, oxide/hydroxide/salt phases, or measurement artifacts.",
    modeled: "observables.py (routes to the discriminating experiment)",
    test: "Per-alternative: grain-size dependence, Shapiro steps, optical vs DC, XRD/XPS/EDS composition, blind replication.",
  },
  {
    id: "H-07", group: "core", level: 2, status: "modeled",
    statement: "Magnetic fields may stabilize, perturb, suppress, or destroy candidate states depending on the phase.",
    modeled: "magnetic_field.py",
    test: "Magnetization vs field: H_c/H_c2 for a superconductor; Zeeman stabilization for a high-spin magnetic state.",
  },
  // ---- Extended hypotheses (H12–H20, from the source conversation) -------
  {
    id: "H-12", group: "extended", level: 2, status: "modeled",
    statement: "Electromagnetic-coherence misidentification — Hudson's 'light flows through it' is EM/quantum coherence (polaritons/plasmons), not superconductivity.",
    modeled: "electromagnetic_coherence.py",
    test: "Optical/THz spectroscopy for polariton branches and coherence lifetime — NOT DC transport.",
  },
  {
    id: "H-13", group: "extended", level: 1, status: "partial",
    statement: "Collective spin polarization — 'high spin' means collective electronic/nuclear spin order, not literal identical-spin alignment of every particle.",
    modeled: "spin_states.py (electronic only; nuclear/collective is roadmap)",
    test: "ESR/EPR, NMR, SQUID magnetometry, synchrotron X-ray spectroscopy.",
  },
  {
    id: "H-14", group: "extended", level: 2, status: "modeled",
    statement: "An unusual, metastable electron-density anisotropy increases inter-unit coupling and coherence, favoring superconducting-like behavior.",
    modeled: "electron_density.py → carrier_coherence_proxy",
    test: "DFT: does the anisotropic state raise the transfer integrals / bandwidth vs the isotropic state?",
  },
  {
    id: "H-15", group: "extended", level: 2, status: "modeled",
    statement: "The active unit is a nanocluster, not a monatomic species.",
    modeled: "geometry.py (compact clusters)",
    test: "TEM/XRD for cluster size distribution; grain-size dependence of any transition.",
  },
  {
    id: "H-16", group: "extended", level: 2, status: "modeled",
    statement: "The claimed superconductivity is actually polaritonic / plasmonic coherence.",
    modeled: "electromagnetic_coherence.py",
    test: "EELS / optical reflectivity for plasmon energy + L/T split; rule out before crediting SC.",
  },
  {
    id: "H-17", group: "extended", level: 1, status: "partial",
    statement: "The material is a granular Josephson network.",
    modeled: "observables.py (resistance regime); explicit network model is roadmap",
    test: "Microwave response, Shapiro steps under RF, broad resistive transition with excess noise.",
  },
  {
    id: "H-18", group: "extended", level: 1, status: "partial",
    statement: "The preparation creates metastable charge/spin states.",
    modeled: "spin_states.py (spin); charge states are roadmap",
    test: "XPS/XANES oxidation state; time-resolved relaxation of the metastable population.",
  },
  {
    id: "H-19", group: "extended", level: 2, status: "modeled",
    statement: "Magnetic fields may stabilize OR destroy the state depending on the phase.",
    modeled: "magnetic_field.py (both directions)",
    test: "Field-dependent susceptibility: suppression (SC) vs Zeeman stabilization (magnetic).",
  },
  {
    id: "H-20", group: "extended", level: 1, status: "partial",
    statement: "The 'rice-bean' geometry is a molecular-orbital shape, not an atomic-shell shape.",
    modeled: "geometry.py (cluster geometry); MO density from DFT is roadmap",
    test: "Compute the MO density of a coupled cluster; compare its shape to the single-atom shell.",
  },
  // ---- Patent-claim tests (Hudson DE3920144A1, tested on its own terms) ----
  {
    id: "P-IR", group: "patent", level: 1, status: "modeled",
    statement: "Patent: OUMEs show an IR doublet at 1400–1600 cm⁻¹ (Rh 1429.53/1490.99; Ir 1432.09/1495.17) as the OUME identity marker.",
    modeled: "ir_signature.py",
    test: "Harmonic ν̃=1302.8√(k/μ): which bond family reaches 1400–1600 cm⁻¹ within physical force constants? Raman/IR on a real sample, controlled for adsorbate/organic bands.",
  },
  {
    id: "P-THERM", group: "patent", level: 1, status: "modeled",
    statement: "Patent: OUMEs do not sinter at 800 °C and stay amorphous to 1200 °C.",
    modeled: "thermal_stability.py",
    test: "Compare claimed stability to Hüttig/Tammann sintering onsets from the bulk melting point; TGA/DSC + XRD on a real sample.",
  },
  {
    id: "P-MEISS", group: "patent", level: 1, status: "modeled",
    statement: "Patent: a lower critical field Hc1 below Earth's field (~50 µT) for Ir/Au S-OUME.",
    modeled: "meissner_field.py",
    test: "Back out λ and nₛ from Hc1; check physical bounds and the isolation premise. SQUID magnetometry (zero-field-cooled Meissner fraction).",
  },
  {
    id: "P-JJ", group: "patent", level: 0, status: "roadmap",
    statement: "Patent: an ac-Josephson-type response above Hc2.",
    modeled: "documented — see coupling-channel prior-art",
    test: "Not independently falsifiable in this framework; would need a real junction I–V with Shapiro steps under microwave drive.",
  },
  {
    id: "P-ASSAY", group: "patent", level: 0, status: "premise",
    statement: "Patent: OUMEs evade conventional instrumental analysis (ore 'assays to <100%').",
    modeled: "documented — flagged unfalsifiable-by-construction",
    test: "A claim that fails all detection methods is not testable as stated; requires an independent quantitative recovery (ICP-MS mass balance) to even define.",
  },
];

// Provenance of the claim space these hypotheses formalize. Recorded as ORIGIN,
// not endorsement: the H-series renders testable a set of claims that originate
// OUTSIDE science, so the notebook names where they come from and their true
// standing (Level 0, unfalsifiable as stated). The lab's job is translation into
// falsifiable tests — never crediting the source.
export const PROVENANCE = {
  claim: "High-spin monatomic platinum-group-metal / gold → superconductivity (“ORME”).",
  origin:
    "David Radius Hudson's “Orbitally Rearranged Monatomic Elements” claims " +
    "(1995 lecture), recompiled in esoteric secondary sources — e.g. halexandria.org " +
    "(D. S. Ward, 2003), which frames it via consciousness and biblical “Manna.”",
  standing:
    "Level 0 — concept, unfalsifiable as originally stated; mixed with non-scientific " +
    "framing. The “nuclear superconductivity” variant is out of this lab's " +
    "electron-phonon model. Logged as provenance, moves no candidate on the ladder.",
};

// Each hypothesis links to the live metric that most directly bears on it
// (a key in metrics.js). Drives the registry ↔ lab cross-link.
const METRIC_FOR = {
  "H-01": "spin", "H-02": "anisotropy", "H-03": "anisotropy", "H-04": "coupling",
  "H-05": "coupling", "H-06": "regime", "H-07": "supp", "H-12": "coherence",
  "H-13": "spin", "H-14": "carrier", "H-15": "coupling", "H-16": "coherence",
  "H-17": "regime", "H-18": "spin", "H-19": "supp", "H-20": "anisotropy",
};
HYPOTHESES.forEach((h) => { h.metric = METRIC_FOR[h.id] || null; });

/** Hypotheses whose linked metric matches `metricKey` (with gate_ normalization). */
export function hypothesesForMetric(metricKey) {
  const GATE_TO_METRIC = {
    gate_coupling: "coupling", gate_carriers: "carrier", gate_field_tolerance: "supp",
    gate_structural_stability: "stability", gate_observable_signal: "observable",
  };
  const canon = GATE_TO_METRIC[metricKey] || metricKey;
  return HYPOTHESES.filter((h) => h.metric === canon);
}

const STATUS_LABEL = {
  modeled: "modeled", partial: "partial", premise: "premise", roadmap: "roadmap",
};

function card(h) {
  return `
    <article class="hyp" id="hyp-${h.id}" data-status="${h.status}">
      <div class="hyp-head">
        <span class="hyp-id">${h.id}</span>
        <span class="hyp-status hyp-status--${h.status}">${STATUS_LABEL[h.status]}</span>
        <span class="hyp-evidence">${evidenceBadge(h.level)}</span>
      </div>
      <p class="hyp-statement">${h.statement}</p>
      <dl class="hyp-fields">
        <dt>Modeled in</dt><dd><code>${h.modeled}</code></dd>
        <dt>Evidence</dt><dd>none — simulation only</dd>
        <dt>Decisive test</dt><dd>${h.test}</dd>
      </dl>
      ${h.metric ? `<button class="hyp-link" data-inspect="${h.metric}">inspect its live metric in the lab →</button>` : ""}
    </article>`;
}

/** Render the full registry into a container element. */
export function renderRegistry(el) {
  const core = HYPOTHESES.filter((h) => h.group === "core");
  const ext = HYPOTHESES.filter((h) => h.group === "extended");
  const patent = HYPOTHESES.filter((h) => h.group === "patent");
  el.innerHTML =
    `<div class="reg-section-label">Core hypotheses · H-01–H-07 <span>the project spec</span></div>` +
    `<div class="hyp-grid">${core.map(card).join("")}</div>` +
    `<div class="reg-section-label">Extended hypotheses · H-12–H-20 <span>from the source research thread</span></div>` +
    `<div class="hyp-grid">${ext.map(card).join("")}</div>` +
    `<div class="reg-section-label">Patent-claim tests · P-* <span>Hudson DE3920144A1, tested on its own terms</span></div>` +
    `<div class="hyp-grid">${patent.map(card).join("")}</div>` +
    `<div id="patentWidgets"></div>` +
    `<div class="reg-section-label">Provenance <span>where these claims originate</span></div>` +
    `<p class="reg-provenance"><strong>Claim:</strong> ${PROVENANCE.claim}<br>` +
    `<strong>Origin:</strong> ${PROVENANCE.origin}<br>` +
    `<strong>Standing:</strong> ${PROVENANCE.standing}</p>`;
}
