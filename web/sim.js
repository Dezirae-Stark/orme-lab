/*
 * sim.js -- faithful client-side port of the orme_lab toy models.
 *
 * This mirrors src/orme_lab/*.py so the 3D lab can recompute every score live
 * in the browser with no backend. The formulas are kept 1:1 with the Python;
 * where the UI needs a value the pipeline supplies indirectly (carrier density
 * for the EM module), the derivation is marked "UI-only" and documented.
 *
 * Same commitments as the Python: bounded scores, an AND-gate that can only say
 * NOT RULED OUT, and electromagnetic coherence kept separate from
 * superconductivity (a coherent quantum material is not a superconductor).
 */

export const CONST = {
  BOHR_MAGNETON: 9.2740100783e-24,
  BOLTZMANN: 1.380649e-23,
  ELEMENTARY_CHARGE: 1.602176634e-19,
  HBAR: 1.054571817e-34,
  VACUUM_PERMEABILITY: 1.25663706212e-6,
  VACUUM_PERMITTIVITY: 8.8541878128e-12,
  ELECTRON_MASS: 9.1093837015e-31,
  EV_IN_JOULES: 1.602176634e-19,
};

export const THRESHOLDS = {
  min_coupling_for_bulk: 0.20,
  min_carrier_proxy: 0.15,
  min_field_tolerance: 0.10,
  min_structural_stability: 0.25,
  min_observable_signal: 0.10,
  anisotropy_ricebean_low: 0.30,
  anisotropy_ricebean_high: 0.75,
  coupling_distance_scale_ang: 3.0,
  ultrastrong_coupling_ratio: 0.10,
  min_cooperativity_for_coherence: 1.0,
};

// ---- elements (mirror elements.py) ---------------------------------------
export const ELEMENTS = {
  Ru: { symbol: "Ru", name: "Ruthenium", Z: 44, d: 7, s: 1, r: 1.46, config: "[Kr] 4d7 5s1" },
  Rh: { symbol: "Rh", name: "Rhodium",   Z: 45, d: 8, s: 1, r: 1.42, config: "[Kr] 4d8 5s1" },
  Pd: { symbol: "Pd", name: "Palladium", Z: 46, d: 10, s: 0, r: 1.39, config: "[Kr] 4d10" },
  Ag: { symbol: "Ag", name: "Silver",    Z: 47, d: 10, s: 1, r: 1.45, config: "[Kr] 4d10 5s1" },
  Os: { symbol: "Os", name: "Osmium",    Z: 76, d: 6, s: 2, r: 1.44, config: "[Xe] 4f14 5d6 6s2" },
  Ir: { symbol: "Ir", name: "Iridium",   Z: 77, d: 7, s: 2, r: 1.41, config: "[Xe] 4f14 5d7 6s2" },
  Pt: { symbol: "Pt", name: "Platinum",  Z: 78, d: 9, s: 1, r: 1.36, config: "[Xe] 4f14 5d9 6s1" },
  Au: { symbol: "Au", name: "Gold",      Z: 79, d: 10, s: 1, r: 1.36, config: "[Xe] 4f14 5d10 6s1" },
};
export const CORE_SCREEN = ["Au", "Pt", "Pd", "Ir", "Rh", "Os"];

const clamp01 = (x) => Math.min(1, Math.max(0, x));

// ---- spin (mirror spin_states.py) ----------------------------------------
export function maxUnpaired(el) {
  const k = el.d;
  return k <= 5 ? k : 10 - k;
}
export function spinState(el, kind) {
  const unpaired = kind === "high" ? maxUnpaired(el) : el.d % 2;
  return { el, unpaired, isHigh: kind === "high" };
}
export const spinPolarizationScore = (st) => Math.min(st.unpaired / 5.0, 1.0);
export const spinOnlyMomentBohr = (st) => Math.sqrt(st.unpaired * (st.unpaired + 2));

// ---- electron density (mirror electron_density.py) ------------------------
export function estimateEllipsoid(st) {
  const n = st.unpaired;
  const axes = [1.0 + 0.35 * n, 1.0 + 0.05 * n, 1.0].sort((a, b) => b - a);
  return { a: axes[0], b: axes[1], c: axes[2] };
}
export function anisotropyScore(e) {
  const { a, b, c } = e;
  const mean = (a + b + c) / 3;
  if (mean === 0) return 0;
  const num = Math.sqrt((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2);
  const den = Math.sqrt(a * a + b * b + c * c);
  if (den === 0) return 0;
  return clamp01(Math.sqrt(1.5) * num / den);
}
export const isRicebean = (s) =>
  s >= THRESHOLDS.anisotropy_ricebean_low && s <= THRESHOLDS.anisotropy_ricebean_high;

// ---- geometry (mirror geometry.py) ---------------------------------------
export function makeGeometry(el, kind) {
  const d = 2.0 * el.r;
  let pts, label;
  if (kind === "monomer") { pts = [[0, 0, 0]]; label = "monomer"; }
  else if (kind === "dimer") { pts = [[0, 0, 0], [d, 0, 0]]; label = "dimer"; }
  else if (kind.startsWith("chain")) {
    const n = parseInt(kind.slice(5), 10);
    pts = Array.from({ length: n }, (_, i) => [i * d, 0, 0]);
    label = kind;
  } else { // compactN
    const n = parseInt(kind.slice(7), 10);
    let reach = 1, grid = [];
    while (grid.length < n) {
      grid = [];
      for (let i = -reach; i <= reach; i++)
        for (let j = -reach; j <= reach; j++)
          for (let k = -reach; k <= reach; k++)
            grid.push([i * d, j * d, k * d]);
      reach++;
    }
    grid.sort((p, q) => (p[0]**2+p[1]**2+p[2]**2) - (q[0]**2+q[1]**2+q[2]**2)
      || p[0]-q[0] || p[1]-q[1] || p[2]-q[2]);
    pts = grid.slice(0, n);
    label = kind;
  }
  return { el, positions: pts, label, spacing: d };
}
function dist(a, b) { return Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]); }
export function nearestNeighbor(g) {
  const p = g.positions;
  if (p.length < 2) return Infinity;
  let m = Infinity;
  for (let i = 0; i < p.length; i++)
    for (let j = i + 1; j < p.length; j++) m = Math.min(m, dist(p[i], p[j]));
  return m;
}
export function meanCoordination(g) {
  const p = g.positions;
  if (p.length < 2) return 0;
  const cutoff = 1.25 * nearestNeighbor(g);
  let total = 0;
  for (let i = 0; i < p.length; i++)
    for (let j = 0; j < p.length; j++)
      if (i !== j && dist(p[i], p[j]) <= cutoff) total++;
  return total / p.length;
}

// ---- coupling (mirror coupling.py) ---------------------------------------
export function orbitalOverlapProxy(nn) {
  if (!isFinite(nn)) return 0;
  const lam = THRESHOLDS.coupling_distance_scale_ang;
  return clamp01(Math.exp(-(nn - lam) / lam));
}
export function couplingScore(g) {
  if (g.positions.length < 2) return 0;
  const overlap = orbitalOverlapProxy(nearestNeighbor(g));
  const connectivity = Math.tanh(meanCoordination(g) / 6.0);
  return Math.sqrt(overlap * connectivity);
}
export const isIsolated = (c) => c < THRESHOLDS.min_coupling_for_bulk;

// ---- carrier / field / stability -----------------------------------------
export function carrierCoherenceProxy(coupling, aniso) {
  const penalty = Math.max(0, aniso - 0.75);
  return Math.max(0, coupling * (1 - penalty));
}
export const criticalFieldProxy = (spin, coupling) => 5.0 * coupling * (0.5 + 0.5 * spin);
export function fieldSuppression(field, Hc) {
  if (Hc <= 0) return 0;
  if (field <= 0) return 1;
  if (field >= Hc) return 0;
  const r = field / Hc;
  return 1 - r * r;
}
export const structuralStability = (g) => Math.tanh(meanCoordination(g) / 8.0);

// ---- observables (mirror observables.py) ---------------------------------
export function curieSusceptibility(st, T, n = 6.0e28) {
  if (T <= 0) return 0;
  const mu = spinOnlyMomentBohr(st) * CONST.BOHR_MAGNETON;
  return (n * CONST.VACUUM_PERMEABILITY * mu * mu) / (3 * CONST.BOLTZMANN * T);
}
export function resistanceRegime(coupling, carrier) {
  if (coupling >= 0.5 && carrier >= 0.4) return "candidate-sc";
  if (coupling >= 0.3) return "metallic";
  return "activated";
}
export const meissnerScreening = (coupling, carrier, supp) => coupling * carrier * supp;

// ---- superconductivity gate (mirror superconductivity.py) -----------------
function gate(name, value, threshold) {
  const passed = value >= threshold;
  const span = 1 - threshold;
  const margin = !passed ? 0 : (span <= 0 ? 1 : Math.min((value - threshold) / span, 1));
  return { name, value, threshold, passed, margin };
}
export function plausibility(coupling, carrier, supp, stability, obsSignal) {
  const T = THRESHOLDS;
  const gates = [
    gate("coupling", coupling, T.min_coupling_for_bulk),
    gate("carriers", carrier, T.min_carrier_proxy),
    gate("field_tolerance", supp, T.min_field_tolerance),
    gate("structural_stability", stability, T.min_structural_stability),
    gate("observable_signal", obsSignal, T.min_observable_signal),
  ];
  const allPassed = gates.every((g) => g.passed);
  let score = 0;
  if (allPassed) { score = 1; for (const g of gates) score *= g.margin; }
  return { gates, allPassed, score, ruledOut: !allPassed };
}

// ---- electromagnetic coherence (mirror electromagnetic_coherence.py) ------
export function plasmonEnergyEv(n, mRatio = 1.0) {
  if (n <= 0 || mRatio <= 0) return 0;
  const m = mRatio * CONST.ELECTRON_MASS;
  const wp = Math.sqrt((n * CONST.ELEMENTARY_CHARGE ** 2) / (CONST.VACUUM_PERMITTIVITY * m));
  return (CONST.HBAR * wp) / CONST.EV_IN_JOULES;
}
export function anisotropicPlasmon(base, aniso) {
  const split = 0.5 * aniso * base;
  return { longitudinal: Math.max(0, base - split), transverse: base + 0.5 * split };
}
export function emMode(modeEv, g, kappa, gamma) {
  const rabi = 2 * g;
  const coop = kappa * gamma <= 0 ? (g > 0 ? Infinity : 0) : (4 * g * g) / (kappa * gamma);
  const Q = kappa <= 0 ? Infinity : modeEv / kappa;
  const lifetime = gamma <= 0 ? Infinity : (1 / (gamma * CONST.EV_IN_JOULES / CONST.HBAR)) * 1e15;
  return { modeEv, g, kappa, gamma, rabi, coop, Q, lifetime };
}
export function isStrongCoupling(m) { return m.rabi > 0.5 * (m.kappa + m.gamma); }
export function couplingRegime(m) {
  const T = THRESHOLDS;
  if (m.modeEv > 0) {
    const ratio = m.rabi / m.modeEv;
    if (ratio >= T.ultrastrong_coupling_ratio && isStrongCoupling(m)) return "ultrastrong";
  }
  if (isStrongCoupling(m) && m.coop >= T.min_cooperativity_for_coherence) return "strong";
  return "weak";
}
export function polaritonCoherenceScore(m) {
  if (couplingRegime(m) === "weak") return 0;
  const coopFactor = isFinite(m.coop) ? m.coop / (1 + m.coop) : 1;
  const qFactor = Math.tanh(m.Q / 100);
  return Math.sqrt(coopFactor * qFactor);
}

/*
 * evaluateCandidate -- the full pipeline for one (element, geometry, spin) at a
 * given field/temperature. Returns everything the 3D lab needs to render.
 */
export function evaluateCandidate({ elSym, geomKind, spinKind, fieldT, tempK }) {
  const el = ELEMENTS[elSym];
  const st = spinState(el, spinKind);
  const geom = makeGeometry(el, geomKind);

  const spin = spinPolarizationScore(st);
  const ell = estimateEllipsoid(st);
  const aniso = anisotropyScore(ell);
  const bean = isRicebean(aniso);

  const coupling = couplingScore(geom);
  const isolated = isIsolated(coupling);
  const carrier = carrierCoherenceProxy(coupling, aniso);
  const Hc = criticalFieldProxy(spin, coupling);
  const supp = fieldSuppression(fieldT, Hc);
  const stability = structuralStability(geom);

  const chi = curieSusceptibility(st, tempK);
  const meissner = meissnerScreening(coupling, carrier, supp);
  const regime = resistanceRegime(coupling, carrier);
  const obsSignal = Math.min(1, Math.max(meissner, Math.tanh(Math.abs(chi))));

  const sc = plausibility(coupling, carrier, supp, stability, obsSignal);

  // EM coherence (UI-only derivations of the inputs the pipeline leaves open):
  //  - carrier density scales with coupling (more connected -> more delocalized)
  //  - light-matter coupling fraction scales with the carrier proxy
  const nDensity = 6.0e28 * (0.3 + 0.7 * coupling);
  const hwp = plasmonEnergyEv(nDensity);
  const split = anisotropicPlasmon(hwp, aniso);
  const gCoupling = (0.03 + 0.10 * carrier) * hwp;
  const mode = emMode(hwp, gCoupling, 0.10, 0.05);
  const emRegime = couplingRegime(mode);
  const emScore = polaritonCoherenceScore(mode);

  return {
    el, st, geom, ellipsoid: ell,
    scores: { spin, aniso, bean, coupling, isolated, carrier, Hc, supp, stability,
              chi, meissner, regime, obsSignal },
    sc,
    em: { nDensity, plasmon: hwp, split, mode, regime: emRegime, score: emScore },
  };
}

export const GEOMETRIES = [
  "monomer", "dimer", "chain4", "chain8", "compact6", "compact13", "compact19",
];

// Full screen over the six core elements x geometries x spin states, ranked.
export function runScreen(fieldT = 0, tempK = 298.15) {
  const rows = [];
  for (const sym of CORE_SCREEN)
    for (const gk of GEOMETRIES)
      for (const sk of ["high", "low"]) {
        const r = evaluateCandidate({ elSym: sym, geomKind: gk, spinKind: sk, fieldT, tempK });
        rows.push({
          element: sym, geometry: gk, spin: sk,
          coupling: r.scores.coupling, plausibility: r.sc.score,
          ruledOut: r.sc.ruledOut, emScore: r.em.score, regime: r.scores.regime,
        });
      }
  rows.sort((a, b) =>
    b.plausibility - a.plausibility || b.coupling - a.coupling ||
    a.element.localeCompare(b.element) || a.geometry.localeCompare(b.geometry) ||
    a.spin.localeCompare(b.spin));
  return rows;
}
