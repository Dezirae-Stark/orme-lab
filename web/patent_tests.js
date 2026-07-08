// web/patent_tests.js
/*
 * patent_tests.js -- live-input widgets for the three computable Hudson-patent
 * claim screens (IR doublet, thermal stability, Meissner Hc1). Each widget is a
 * one-line-formula JS mirror of the authoritative Python screen in src/orme_lab/;
 * the shared constants below are pinned to the Python modules by
 * tests/test_patent_web_parity.py. Triage only -- evidence Level <= 2.
 */

// ---- shared physical constants (pinned to Python by parity test) ----------
export const WAVENUMBER_CONST = 1302.8;       // ir_signature.py
export const HUTTIG_FRACTION = 0.3;           // thermal_stability.py
export const TAMMANN_FRACTION = 0.5;          // thermal_stability.py
export const PHI0 = 2.067833848e-15;          // meissner_field.py
export const MU0 = 1.25663706212e-6;
export const M_E = 9.1093837015e-31;
export const E_CHARGE = 1.602176634e-19;

// numbers copied verbatim from _CONTAMINANTS (Python authoritative; parity test pins this)
const CONTAMINANTS = [
  { name: "nitrate NO3-", cat: "route_derived", lo: [1324, 1345], hi: [1353, 1374], d: [12, 43] },
  { name: "carbonate CO3(2-) monodentate", cat: "route_derived", lo: [1360, 1373], hi: [1449, 1495], d: [80, 125] },
  { name: "carbonate CO3(2-) bidentate", cat: "route_derived", lo: [1265, 1292], hi: [1593, 1643], d: [301, 378] },
  { name: "carboxylate/acetate COO- (ionic/bridging/monodentate)", cat: "route_derived", lo: [1280, 1400], hi: [1510, 1650], d: [100, 285] },
  { name: "carboxylate/acetate COO- (chelating)", cat: "route_derived", lo: [1456, 1472], hi: [1537, 1550], d: [65, 94] },
  { name: "water bend d(H2O)", cat: "route_derived", lo: [1644, 1670], hi: [1644, 1670], d: [0, 0] },
  { name: "alkyl C-H scissor/bend", cat: "standard", lo: [1370, 1390], hi: [1450, 1467], d: [60, 97] },
  { name: "ammonium NH4+", cat: "standard", lo: [1400, 1440], hi: [1400, 1440], d: [0, 0] },
  { name: "silicone/PDMS Si-CH3", cat: "standard", lo: [1254, 1265], hi: [1400, 1415], d: [135, 161] },
];
const CAT_RANK = { route_derived: 0, standard: 1 };
const bandResidual = (x, [lo, hi]) => (x >= lo && x <= hi) ? 0 : (x < lo ? (lo - x) / ((hi - lo) || 1) : (x - hi) / ((hi - lo) || 1));
function contaminantMatch(lo, hi) {
  const split = hi - lo;
  const scored = CONTAMINANTS
    .map((b) => [b, bandResidual(lo, b.lo) + bandResidual(hi, b.hi) + bandResidual(split, b.d)])
    .sort((a, z) => a[1] - z[1] || CAT_RANK[a[0].cat] - CAT_RANK[z[0].cat] || a[0].name.localeCompare(z[0].name));
  const [top, s] = scored[0];
  const tight = bandResidual(lo, top.lo) === 0 && bandResidual(hi, top.hi) === 0 && bandResidual(split, top.d) === 0;
  const v = tight ? "tight match" : (s <= 1.0 ? "plausible match" : "unmatched");
  return `closest contaminant: ${top.name} (${v}, residual ${s.toFixed(2)}).`;
}

const MASS = { Rh: 102.905, Ir: 192.217, C: 12.011, N: 14.007, O: 15.999 };
const MELT_C = { Rh: 1964, Ir: 2446, Pt: 1768, Pd: 1555, Os: 3033, Ru: 2334, Au: 1064, Ag: 962, Cu: 1085 };
const reduced = (a, b) => (a * b) / (a + b);
const wavenumber = (k, mu) => WAVENUMBER_CONST * Math.sqrt(k / mu);
const requiredK = (nu, mu) => mu * (nu / WAVENUMBER_CONST) ** 2;

function irVerdict(sym, hi, lo) {
  const mu = MASS[sym] / 2;
  const metalHi = wavenumber(5, mu);
  const co = [wavenumber(5, reduced(MASS.C, MASS.O)), wavenumber(13, reduced(MASS.C, MASS.O))];
  const kReq = requiredK(hi, mu);
  let v;
  if (hi <= metalHi) v = `${sym}–${sym} reachable — metal–metal not excluded`;
  else if (hi >= co[0] && hi <= co[1]) v = `metal–metal excluded (needs k~${kReq.toFixed(0)} mdyne/Å >> 5); light-atom (C/N/O) consistent`;
  else v = `metal–metal excluded (k~${kReq.toFixed(0)}); no clean light-atom fit`;
  let out = `ν̃=${hi.toFixed(0)} cm⁻¹ → ${sym}–${sym} band tops out at ${metalHi.toFixed(0)} cm⁻¹. ${v}.`;
  if (typeof lo === "number" && !Number.isNaN(lo)) {
    out += `\n${contaminantMatch(Math.min(lo, hi), Math.max(lo, hi))}`;
  }
  return out;
}

function thermalVerdict(sym, tClaim) {
  const tmK = MELT_C[sym] + 273.15;
  const huttig = HUTTIG_FRACTION * tmK - 273.15;
  const tammann = TAMMANN_FRACTION * tmK - 273.15;
  let v;
  if (tClaim < huttig) v = "within refractory envelope (not diagnostic)";
  else if (tClaim < tammann) v = "marginal (ordinary sintering window)";
  else v = "exceeds Tammann onset (anomalous for this metal)";
  return `${sym}: Hüttig ${huttig.toFixed(0)} °C, Tammann ${tammann.toFixed(0)} °C → claim at ${tClaim.toFixed(0)} °C is ${v}.`;
}

function meissnerVerdict(bc1uT) {
  const bc1 = bc1uT * 1e-6;
  const lam = Math.sqrt(PHI0 / (4 * Math.PI * bc1));
  const ns = M_E / (MU0 * lam * lam * E_CHARGE * E_CHARGE);
  return `Hc1=${bc1uT.toFixed(0)} µT → λ≈${(lam * 1e6).toFixed(2)} µm, nₛ≈${ns.toExponential(1)} m⁻³ (${(ns / 1e29).toExponential(1)}× a normal metal). Meissner screening needs coherence the isolated-monomer premise lacks — in tension with its own premise.`;
}

const _elements = Object.keys(MELT_C);

export function renderPatentTests(el) {
  if (!el) return;
  el.innerHTML = `
    <div class="patent-widget">
      <div class="pw-title">IR doublet — bond assignment</div>
      <label>lower line (cm⁻¹) <input id="pwIrLineLo" class="field" type="number" value="1429.53" step="0.01"></label>
      <label>upper line (cm⁻¹) <input id="pwIrLine" class="field" type="number" value="1490.99" step="0.01"></label>
      <label>metal <select id="pwIrSym" class="field">${["Rh", "Ir"].map((s) => `<option>${s}</option>`).join("")}</select></label>
      <p class="pw-out" id="pwIrOut"></p>
    </div>
    <div class="patent-widget">
      <div class="pw-title">Thermal stability — sintering onset</div>
      <label>metal <select id="pwThSym" class="field">${_elements.map((s) => `<option${s === "Ir" ? " selected" : ""}>${s}</option>`).join("")}</select></label>
      <label>claimed stable to (°C) <input id="pwThT" class="field" type="number" value="1200" step="10"></label>
      <p class="pw-out" id="pwThOut"></p>
    </div>
    <div class="patent-widget">
      <div class="pw-title">Meissner Hc1 — implied λ / nₛ</div>
      <label>Hc1 (µT) <input id="pwMeB" class="field" type="number" value="50" step="1"></label>
      <p class="pw-out" id="pwMeOut"></p>
    </div>`;

  const $ = (id) => el.querySelector("#" + id);
  const updIr = () => { $("pwIrOut").textContent = irVerdict($("pwIrSym").value, parseFloat($("pwIrLine").value) || 0, parseFloat($("pwIrLineLo").value)); };
  const updTh = () => { $("pwThOut").textContent = thermalVerdict($("pwThSym").value, parseFloat($("pwThT").value) || 0); };
  const updMe = () => { $("pwMeOut").textContent = meissnerVerdict(parseFloat($("pwMeB").value) || 0); };
  $("pwIrLine").addEventListener("input", updIr); $("pwIrSym").addEventListener("change", updIr);
  $("pwIrLineLo").addEventListener("input", updIr);
  $("pwThSym").addEventListener("change", updTh); $("pwThT").addEventListener("input", updTh);
  $("pwMeB").addEventListener("input", updMe);
  updIr(); updTh(); updMe();
}
