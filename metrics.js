/*
 * metrics.js -- the "tap a metric to inspect it" drill-down registry.
 *
 * Each score in the right rail opens an inspector: Definition, Calculation
 * (the ACTUAL toy formula from sim.js / the Python package), Experimental
 * analogue (what instrument would measure it), Confidence (honest: everything
 * here is a Level-2 toy proxy), and Future validation (the ab-initio backend
 * that would replace it). Turns the instrument into a teacher without
 * overstating anything.
 */

// Each entry: get(result) -> displayed value string; fields are plain text
// (Unicode math, no MathJax). `source` points at the file that computes it.
export const METRICS = {
  spin: {
    title: "Spin polarization",
    eyebrow: "Deformation",
    get: (r) => r.scores.spin.toFixed(3),
    definition:
      "How high-spin the state is — the degree to which valence d-electrons are unpaired and spin-aligned (Hund's-rule maximization).",
    calculation:
      "spin = min(unpaired_electrons / 5, 1). Unpaired count = k for a d^k shell with k ≤ 5, else 10 − k. Spin-only moment μ = √(n(n+2)) μ_B.",
    experimental: "EPR / ESR · SQUID magnetic susceptibility (Curie moment) · XMCD.",
    confidence: "Toy (Level 2). Combinatorial unpaired-electron count — no energetics.",
    future: "Unrestricted / broken-symmetry DFT spin density (PySCF / ORCA).",
    source: "src/orme_lab/spin_states.py",
  },
  anisotropy: {
    title: "Density anisotropy",
    eyebrow: "Deformation",
    get: (r) => r.scores.aniso.toFixed(3) + (r.scores.bean ? "  (rice-bean band)" : ""),
    definition:
      "How non-spherical the valence electron density is — the 'rice-bean' claim made quantitative. 0 = sphere, →1 = a thin needle; the rice-bean band is prolate, in between.",
    calculation:
      "Fractional anisotropy of the density ellipsoid's semi-axes a ≥ b ≥ c: FA = √(3/2)·‖axis − mean‖ / ‖axes‖ ∈ [0,1]. The toy ellipsoid elongates its long axis with unpaired-spin count.",
    experimental:
      "X-ray / electron charge-density (multipole refinement) · quadrupole moment · orbital polarization from XAS linear dichroism.",
    confidence: "Toy (Level 2). Heuristic ellipsoid derived from spin, not a real density.",
    future: "Eigenvalues of the second-moment tensor of a DFT charge density (cube file) — the same cube that would drive a real isosurface render.",
    source: "src/orme_lab/electron_density.py",
  },
  coupling: {
    title: "Inter-unit coupling",
    eyebrow: "Deformation",
    get: (r) => r.scores.coupling.toFixed(3) + (r.scores.isolated ? "  (isolated)" : "  (coupled)"),
    definition:
      "Strength of the electronic channel between units — the make-or-break for bulk behavior. A macroscopic phase-coherent state needs somewhere for the phase to propagate; an isolated atom has none (hypotheses 4–5).",
    calculation:
      "coupling = √(overlap · connectivity). overlap = exp(−(d_nn − λ)/λ) clamped to [0,1], λ ≈ 3 Å; connectivity = tanh(mean_coordination / 6). A monomer has d_nn = ∞ → coupling = 0.",
    experimental:
      "Transfer integrals / bandwidth (ARPES) · tunneling (STS) · exchange coupling J (magnetometry, inelastic neutron scattering).",
    confidence: "Toy (Level 2). Geometric overlap proxy — no wavefunctions.",
    future: "Tight-binding transfer integrals t_ij fit to a DFT band structure (Quantum ESPRESSO + Wannier).",
    source: "src/orme_lab/coupling.py",
  },
  carrier: {
    title: "Carrier / coherence proxy",
    eyebrow: "Deformation",
    get: (r) => r.scores.carrier.toFixed(3),
    definition:
      "A stand-in for mobile, potentially paired carriers available to form a coherent state. Delocalization helps; a 1D needle localizes carriers (Peierls-like) and hurts.",
    calculation:
      "carrier = max(0, coupling · (1 − penalty)), penalty = max(0, anisotropy − 0.75). Only needle-like density (aniso > 0.75) is penalized.",
    experimental:
      "Carrier density (Hall effect) · Drude weight (optical conductivity) · density of states at E_F.",
    confidence: "Toy (Level 2). Derived from coupling and anisotropy, not a computed carrier count.",
    future: "N(E_F) and effective mass from a DFT band structure.",
    source: "src/orme_lab/superconductivity.py",
  },
  supp: {
    title: "Field suppression",
    eyebrow: "Magnetic field",
    get: (r) => r.scores.supp.toFixed(3),
    definition:
      "How much of the candidate order parameter survives the applied magnetic field. 1 = untouched at zero field; 0 = destroyed at/above the critical field (hypothesis 7).",
    calculation:
      "survival = 1 − (H / H_c)² for H < H_c, else 0 (the parabolic type-I critical-field form). Toy H_c = 5 · coupling · (0.5 + 0.5·spin) tesla.",
    experimental:
      "Critical field H_c / H_c2 from magnetization vs field · the Meissner transition.",
    confidence: "Toy (Level 2). One factor conflating orbital and paramagnetic pair-breaking.",
    future: "Separate orbital (H_c2) and Chandrasekhar–Clogston (paramagnetic) limits from a computed gap.",
    source: "src/orme_lab/magnetic_field.py",
  },
  stability: {
    title: "Structural stability",
    eyebrow: "Geometry",
    get: (r) => r.scores.stability.toFixed(3),
    definition:
      "How robust the geometry is — does it persist, or relax away? Fragile 1D chains and dimers score low; compact clusters score high.",
    calculation:
      "stability = tanh(mean_coordination / 8). More neighbours ⇒ more bulk-like. A monomer (coordination 0) scores 0.",
    experimental:
      "Cohesive / formation energy · phonon spectrum (no imaginary modes) · thermal stability.",
    confidence: "Toy (Level 2). Coordination proxy, not an energy calculation.",
    future: "Relaxed DFT energetics + phonon calculation (ASE + a calculator).",
    source: "src/orme_lab/pipeline.py",
  },
  regime: {
    title: "Resistance regime",
    eyebrow: "Observable",
    get: (r) => r.scores.regime,
    definition:
      "A routing label for which transport experiment to run — not a transport calculation. One of candidate-sc / metallic / activated.",
    calculation:
      "candidate-sc if coupling ≥ 0.5 and carrier ≥ 0.4; metallic if coupling ≥ 0.3; else activated (hopping / insulating-like).",
    experimental:
      "4-probe resistivity ρ(T). Note: zero DC resistance alone is NOT superconductivity — bulk Meissner screening is required.",
    confidence: "Toy (Level 2). Coarse label to pick the next measurement.",
    future: "Boltzmann transport / Kubo conductivity from a DFT band structure.",
    source: "src/orme_lab/observables.py",
  },
  emRegime: {
    title: "Light–matter coupling regime",
    eyebrow: "EM coherence (H12/H16)",
    get: (r) => r.em.regime,
    definition:
      "Regime of coupling between the collective electron oscillation (plasmon) and light — weak / strong / ultrastrong. The charitable reading of 'light flows through it': polaritonic coherence, NOT superconductivity.",
    calculation:
      "strong when the Rabi splitting Ω_R = 2g exceeds the mean loss (κ+γ)/2 and cooperativity C = 4g²/(κγ) ≥ 1; ultrastrong when Ω_R / ħω_p ≥ 0.1.",
    experimental:
      "Rabi splitting in reflectivity / transmission (two polariton branches) · cavity / near-field spectroscopy.",
    confidence: "Toy (Level 2). Free-electron plasmon + assumed coupling.",
    future: "Computed dielectric function ε(q, ω) (RPA / TDDFT, GPAW).",
    source: "src/orme_lab/electromagnetic_coherence.py",
  },
  plasmon: {
    title: "Plasmon energy",
    eyebrow: "EM coherence (H12/H16)",
    get: (r) => r.em.plasmon.toFixed(2) + " eV  (L " + r.em.split.longitudinal.toFixed(1) + " / T " + r.em.split.transverse.toFixed(1) + ")",
    definition:
      "Energy of the bulk collective electron-density oscillation. An anisotropic ('rice-bean') particle splits it into longitudinal and transverse branches — a real nanoplasmonic effect (gold nanorods).",
    calculation:
      "ħω_p = ħ·√(n·e² / (ε₀·m*)). Anisotropy splits it: longitudinal red-shifts, transverse blue-shifts, proportional to the density anisotropy.",
    experimental:
      "EELS · optical reflectivity edge · the L/T split in absorption spectra.",
    confidence: "Toy (Level 2). Free-electron (Drude) estimate; carrier density scales with coupling.",
    future: "ε(q, ω) from RPA / TDDFT (GPAW) instead of the free-electron formula.",
    source: "src/orme_lab/electromagnetic_coherence.py",
  },
  coherence: {
    title: "EM coherence score",
    eyebrow: "EM coherence (H12/H16)",
    get: (r) => r.em.score.toFixed(3),
    definition:
      "Quality of polaritonic / plasmonic coherence — a candidate 'coherent quantum material'. This is a DIFFERENT axis from superconductivity: a high value with a failing SC gate is a possible H12 misidentification, not evidence of superconductivity.",
    calculation:
      "coherence = √(C/(1+C) · tanh(Q/100)), credited only in strong / ultrastrong coupling. C = cooperativity, Q = ω_p / κ (quality factor).",
    experimental:
      "Optical / THz spectroscopy · coherence lifetime τ = ħ/γ. NOT DC transport.",
    confidence: "Toy (Level 2). A separate channel kept explicitly distinct from the SC gate.",
    future: "Cavity / near-field mode overlap + computed ε(q, ω).",
    source: "src/orme_lab/electromagnetic_coherence.py",
  },
  // gate cascade rows map to the metric that drives them
  gate_coupling: null,          // -> coupling (aliased below)
  gate_carriers: null,          // -> carrier
  gate_field_tolerance: null,   // -> supp
  gate_structural_stability: null, // -> stability
  screening: {
    title: "Screening score",
    eyebrow: "Verdict",
    get: (r) => r.sc.score.toFixed(3) + (r.sc.ruledOut ? "  (ruled out)" : "  (not ruled out)"),
    definition:
      "A triage / ranking value in [0,1] — where to look next, NOT a probability of superconductivity. It only ever says 'not ruled out', never 'proven'.",
    calculation:
      "AND-gate of five necessary conditions (coupling, carriers, field tolerance, structural stability, measurable observable). Fail any one → 0. If all pass, score = product of each gate's normalized margin (the weakest link dominates).",
    experimental:
      "None directly — it decides which of the above experiments to run. Confirmation needs zero-R AND Meissner AND a specific-heat jump AND the H_c dependence.",
    confidence: "Toy (Level 2 → 3). A survivor is a laboratory prediction, never an experimental fact.",
    future: "Electron-phonon coupling + Eliashberg gap (Quantum ESPRESSO + EPW) — the only defensible superconductivity estimate.",
    source: "src/orme_lab/superconductivity.py",
  },
};

// gate-row aliases → underlying metric
METRICS.gate_coupling = METRICS.coupling;
METRICS.gate_carriers = METRICS.carrier;
METRICS.gate_field_tolerance = METRICS.supp;
METRICS.gate_structural_stability = METRICS.stability;
METRICS.gate_observable_signal = {
  title: "Measurable observable",
  eyebrow: "Falsifiability gate",
  get: (r) => r.scores.obsSignal.toFixed(3),
  definition:
    "Magnitude of the strongest predicted lab signature. If nothing is measurable, the claim is unfalsifiable — so this is a necessary gate.",
  calculation:
    "observable = min(1, max(Meissner_screening, tanh|χ|)). Meissner screening = coupling · carrier · field-survival; χ = Curie-law susceptibility proxy.",
  experimental:
    "SQUID Meissner screening (χ → −1 in bulk) · specific-heat jump at T_c · magnetic susceptibility.",
  confidence: "Toy (Level 2). Product proxy — any missing ingredient collapses it to ~0.",
  future: "Computed susceptibility and an EPW-derived gap.",
  source: "src/orme_lab/observables.py",
};
