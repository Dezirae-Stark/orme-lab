// web/ledger.js — Hudson Claim Ledger dashboard (Phase A/B/C). Parity-locked to hudson_ledger.py.
// Every assessor/gate below is a faithful port of src/orme_lab/hudson_ledger.py (read that file
// for the authoritative thresholds/branch order — this module must not compute anything the
// Python doesn't). Pure/deterministic: no Date, no Math.random, no network.
//
// Phase C: mountLedger3d/updateLedger3d (imported below) drive the guarded 3D material-state
// stage atop _renderDash; ledger3d.js imports gateRing/branchFlow back from this module (a
// deliberate, safe ES-module circular import — neither side calls the other's exports at
// top-level module-evaluation time, only from inside functions invoked after the graph is
// fully linked).
import { mountLedger3d, updateLedger3d } from "./ledger3d.js?v=__BUILD__";

// ---- Enums (mirror hudson_ledger.ClaimStatus / .Route / .HudsonClaimId) --------------------
export const CLAIM_STATUS = {
  CANDIDATE: 0,
  LEAD: 1,
  ANOMALOUS: 2,
  PROVISIONALLY_SUPPORTED: 3,
  SUPPORTED: 4,
  INDEPENDENTLY_REPLICATED: 5,
};

export const ROUTE = { CONVENTIONAL: "conventional", OPTICAL: "optical", NONE: "none" };

export const HC = ["HC-01", "HC-02", "HC-03", "HC-04", "HC-05", "HC-06", "HC-07", "HC-08"];

// Branch-B optical claim levels (mirror hudson_optical.HudsonClaim). Integer values match the
// Python IntEnum exactly — the parity tests pass these as bare integers in `opt.supported`.
export const HUDSON_CLAIM = {
  STRONG_COUPLING: 3,
  MACRO_COHERENCE: 4,
  LOW_LOSS_TRANSPORT: 5,
  ELECTRONIC_COUPLING: 6,
  MAGNETISM_COUPLED: 7,
  HUDSON_PHASE: 8,
};

// Hudson's claimed novel phase: elemental composition, zero oxidation, NOT the metallic lattice.
const NONMETALLIC_ELEMENTAL = "nonmetallic-elemental";
const OX_TOL = 0.5; // |oxidation| above this implies a compound, not an elemental phase

// ---- G_identity_established --------------------------------------------------------------
export function gIdentityEstablished(witness) {
  return (
    witness != null &&
    witness.composition != null &&
    witness.phase != null &&
    witness.morphology != null &&
    witness.oxidation != null
  );
}

// ---- HC-01: stable nonmetallic PGM form ----------------------------------------------------
export function assessHc01(witness, target, th) {
  if (!gIdentityEstablished(witness)) {
    return { id: "HC-01", status: CLAIM_STATUS.CANDIDATE, route: ROUTE.NONE, note: "identity not established" };
  }
  const isElemental = witness.composition === target && Math.abs(witness.oxidation) <= OX_TOL;
  if (witness.phase === NONMETALLIC_ELEMENTAL && isElemental) {
    return {
      id: "HC-01",
      status: CLAIM_STATUS.PROVISIONALLY_SUPPORTED,
      route: ROUTE.NONE,
      note: "witness: nonmetallic-elemental phase",
    };
  }
  return {
    id: "HC-01",
    status: CLAIM_STATUS.CANDIDATE,
    route: ROUTE.NONE,
    note: `phase '${witness.phase}' is not nonmetallic-elemental (mundane alternative: oxide / hydroxide / salt / ligand complex)`,
  };
}

// ---- HC-02: atomically dispersed ("monoatomic") — a POLICY, not a Boolean ------------------
// _hc02Metrics is shared by the assessor and the HC-02 detail render (renderLedger below) so
// the dashboard reads the identical numbers the parity-locked assessor computed — never a
// second, drifting computation.
function _hc02Metrics(distribution, th) {
  const fSingle = distribution.f1;
  const clusteredUb = Math.min(1.0, 1.0 - fSingle + th.hc02ClusterMargin);
  let coordinated = 0.0;
  for (const [dist, frac] of distribution.nnDistances) {
    if (isFinite(dist) && dist <= th.hc02BondLen) coordinated += frac;
  }
  return { fSingle, clusteredUb, coordinated };
}

export function assessHc02(distribution, th) {
  const { fSingle, clusteredUb, coordinated } = _hc02Metrics(distribution, th);
  const clears =
    fSingle >= th.hc02MinIsolated && clusteredUb <= th.hc02MaxClustered && coordinated <= th.hc02PgmPgmTol;
  if (clears) {
    return {
      id: "HC-02",
      status: CLAIM_STATUS.PROVISIONALLY_SUPPORTED,
      route: ROUTE.NONE,
      note: `f_single=${fSingle.toFixed(2)}, clustered_ub=${clusteredUb.toFixed(2)}, pgm-pgm=${coordinated.toFixed(2)}`,
    };
  }
  return {
    id: "HC-02",
    status: CLAIM_STATUS.CANDIDATE,
    route: ROUTE.NONE,
    note: `dispersion policy not met (f_single=${fSingle.toFixed(2)}, clustered_ub=${clusteredUb.toFixed(2)}, pgm-pgm=${coordinated.toFixed(2)})`,
  };
}

// ---- G_hudson_material_state = HC-01 AND HC-02 ---------------------------------------------
export function gHudsonMaterialState(witness, distribution, target, th) {
  if (!gIdentityEstablished(witness)) return false;
  const hc01 = assessHc01(witness, target, th).status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED;
  const hc02 = assessHc02(distribution, th).status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED;
  return hc01 && hc02;
}

// ---- G_conventional_superconductivity (Branch A, measured) --------------------------------
export function gConventionalSuperconductivity(measured) {
  if (measured == null) return false;
  return Boolean(
    measured.zeroResistance && measured.fluxExclusion && measured.criticalBehavior && measured.artifactExcluded
  );
}

// ---- G_candidate_optical (Branch B) --------------------------------------------------------
export function gCandidateOptical(opt) {
  if (opt == null) return false;
  const s = new Set(opt.supported || []);
  const coherentTransport = [
    HUDSON_CLAIM.STRONG_COUPLING,
    HUDSON_CLAIM.MACRO_COHERENCE,
    HUDSON_CLAIM.ELECTRONIC_COUPLING,
    HUDSON_CLAIM.LOW_LOSS_TRANSPORT,
  ].every((lvl) => s.has(lvl));
  return coherentTransport && opt.persistence === "persistent";
}

// ---- opticalMagneticCausality (Branch B level-7) -------------------------------------------
export function opticalMagneticCausality(opt) {
  if (opt == null) return false;
  return new Set(opt.supported || []).has(HUDSON_CLAIM.MAGNETISM_COUPLED);
}

// ---- replicationGate (default-blocked) -----------------------------------------------------
export function replicationGate(rep, th) {
  if (rep == null) return false;
  return Boolean(
    rep.nBatches >= th.replMinBatches &&
      rep.nLabs >= th.replMinLabs &&
      rep.preregistered &&
      rep.rawRetained &&
      rep.blindedOk
  );
}

// ---- branchFlow: per-material two-branch gate states for the Phase B flow render. Pure;
// mirrors evaluateLedger's per-lineage gate computation (rollupIntegrated's same-lineage bits)
// for a SINGLE material treated as its own one-material lineage — no new decision logic, only
// the already-parity-locked assessors/gates above. Deterministic; no Date/Math.random.
export function branchFlow(material, doublet, th) {
  const m = { ...(material.measured || {}), opticalResult: material.optical || null };
  const opt = material.optical || null;

  const hc01 = material.witness != null ? assessHc01(material.witness, material.element, th) : _bareRecord("HC-01");
  const hc01Status =
    m.hc01NonmetallicConfirmed && hc01.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED
      ? CLAIM_STATUS.SUPPORTED
      : hc01.status;
  const hc02 = material.distribution != null ? assessHc02(material.distribution, th) : _bareRecord("HC-02");
  const hc02Status =
    m.hc02DispersionConfirmed && hc02.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED
      ? CLAIM_STATUS.SUPPORTED
      : hc02.status;
  const materialState =
    hc01Status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED && hc02Status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED;

  const s = new Set((opt && opt.supported) || []);
  const coherentMode = s.has(HUDSON_CLAIM.STRONG_COUPLING) && s.has(HUDSON_CLAIM.MACRO_COHERENCE);
  const materialCoupling = s.has(HUDSON_CLAIM.ELECTRONIC_COUPLING);
  const energyTransport = gCandidateOptical(opt);
  const causalMagnetism = opticalMagneticCausality(opt);
  const replication = replicationGate(m.replication, th);

  return {
    conventional: {
      zeroR: Boolean(m.zeroResistance),
      flux: Boolean(m.fluxExclusion),
      critical: Boolean(m.criticalBehavior),
      artifact: Boolean(m.artifactExcluded),
      result: gConventionalSuperconductivity(m),
    },
    hudson: {
      coherentMode,
      materialCoupling,
      energyTransport,
      causalMagnetism,
      materialState,
      replication,
      result: materialState && energyTransport && causalMagnetism && replication,
    },
  };
}

// ---- gateRing: the six-gate ring states for the Phase C 3D stage (and its text-legend
// fallback). Reuses ONLY the parity-locked branchFlow(...)/gIdentityEstablished(...) above — no
// new decision logic. `identity` is read from gIdentityEstablished directly (branchFlow doesn't
// surface it) so the ring's first gate matches the same identity check the matrix/cards use.
export function gateRing(material, doublet, th) {
  const bf = branchFlow(material, doublet, th);
  return {
    identity: gIdentityEstablished(material.witness),
    materialState: bf.hudson.materialState,
    transport: bf.hudson.energyTransport,
    magnetism: bf.hudson.causalMagnetism,
    replication: bf.hudson.replication,
    mechanism: bf.hudson.result,
  };
}

// ---- Procedural claims (HC-03, HC-05, HC-08): a measured confirmation -> SUPPORTED --------
function procedural(id, confirmed) {
  return {
    id,
    status: confirmed ? CLAIM_STATUS.SUPPORTED : CLAIM_STATUS.CANDIDATE,
    route: ROUTE.NONE,
    note: confirmed ? "measured confirmation loaded" : "Level-3 decisive-experiment design; attack the mundane alternative first",
  };
}

export function assessHc03(measured) {
  return procedural("HC-03", Boolean(measured && measured.hc03OrbitalConfirmed));
}

export function assessHc05(measured) {
  return procedural("HC-05", Boolean(measured && measured.hc05RecoveryConfirmed));
}

export function assessHc08(measured) {
  return procedural("HC-08", Boolean(measured && measured.hc08MassConfirmed));
}

// ---- HC-04: 1400-1600 cm^-1 doublet — attacks the contaminant alternative first -----------
// A faithful (compact) port of ir_contaminant.py's cited-band scoring. Status is ALWAYS LEAD
// from this assessor (an intrinsic assignment needs measured isotope/atmosphere sensitivity,
// loaded separately) — the contaminant screen only informs the note.
const _CAT_RANK = { route_derived: 0, standard: 1 };
const _TOL_PLAUSIBLE = 1.0;

const _CONTAMINANTS = [
  { name: "nitrate NO3-", category: "route_derived", loBand: [1324.0, 1345.0], hiBand: [1353.0, 1374.0], splitBand: [12.0, 43.0] },
  { name: "carbonate CO3(2-) monodentate", category: "route_derived", loBand: [1360.0, 1373.0], hiBand: [1449.0, 1495.0], splitBand: [80.0, 125.0] },
  { name: "carbonate CO3(2-) bidentate", category: "route_derived", loBand: [1265.0, 1292.0], hiBand: [1593.0, 1643.0], splitBand: [301.0, 378.0] },
  { name: "carboxylate/acetate COO- (ionic/bridging/monodentate)", category: "route_derived", loBand: [1280.0, 1400.0], hiBand: [1510.0, 1650.0], splitBand: [100.0, 285.0] },
  { name: "carboxylate/acetate COO- (chelating)", category: "route_derived", loBand: [1456.0, 1472.0], hiBand: [1537.0, 1550.0], splitBand: [65.0, 94.0] },
  { name: "water bend d(H2O)", category: "route_derived", loBand: [1644.0, 1670.0], hiBand: [1644.0, 1670.0], splitBand: [0.0, 0.0] },
  { name: "alkyl C-H scissor/bend", category: "standard", loBand: [1370.0, 1390.0], hiBand: [1450.0, 1467.0], splitBand: [60.0, 97.0] },
  { name: "ammonium NH4+", category: "standard", loBand: [1400.0, 1440.0], hiBand: [1400.0, 1440.0], splitBand: [0.0, 0.0] },
  { name: "silicone/PDMS Si-CH3", category: "standard", loBand: [1254.0, 1265.0], hiBand: [1400.0, 1415.0], splitBand: [135.0, 161.0] },
];

function _bandResidual(x, [lo, hi]) {
  if (lo <= x && x <= hi) return 0.0;
  const width = hi > lo ? hi - lo : 1.0;
  return x < lo ? (lo - x) / width : (x - hi) / width;
}

function _matchScore(linesCm, band) {
  const loLine = Math.min(...linesCm);
  const hiLine = Math.max(...linesCm);
  const split = hiLine - loLine;
  return (
    _bandResidual(loLine, band.loBand) + _bandResidual(hiLine, band.hiBand) + _bandResidual(split, band.splitBand)
  );
}

function _screenContaminants(linesCm) {
  const lo = Math.min(...linesCm);
  const hi = Math.max(...linesCm);
  const scored = _CONTAMINANTS.map((b) => [b, _matchScore(linesCm, b)]);
  scored.sort((a, b) => {
    if (a[1] !== b[1]) return a[1] - b[1];
    if (_CAT_RANK[a[0].category] !== _CAT_RANK[b[0].category]) return _CAT_RANK[a[0].category] - _CAT_RANK[b[0].category];
    return a[0].name < b[0].name ? -1 : a[0].name > b[0].name ? 1 : 0;
  });
  const [topBand, topScore] = scored[0];
  const loR = _bandResidual(lo, topBand.loBand);
  const hiR = _bandResidual(hi, topBand.hiBand);
  const spR = _bandResidual(hi - lo, topBand.splitBand);
  let verdict;
  if (loR === 0.0 && hiR === 0.0 && spR === 0.0) verdict = "tight_match";
  else if (topScore <= _TOL_PLAUSIBLE) verdict = "plausible_match";
  else verdict = "unmatched";
  return { topName: topBand.name, topScore, verdict };
}

export function assessHc04(observedDoublet, th) {
  const screen = _screenContaminants(observedDoublet);
  return {
    id: "HC-04",
    status: CLAIM_STATUS.LEAD,
    route: ROUTE.NONE,
    note: `IR contaminant screen: ${screen.verdict} (closest ${screen.topName}, residual ${screen.topScore.toFixed(2)} band-widths)`,
  };
}

// ---- HC-06: flux exclusion > 200 K — Meissner screen (a port of meissner_field.py) ---------
const PHI0 = 2.067833848e-15; // magnetic flux quantum (Wb), CODATA 2018 / current SI
const MU0 = 1.25663706212e-6; // vacuum permeability (H/m)
const M_E = 9.1093837015e-31; // electron mass (kg)
const E_CHARGE = 1.602176634e-19; // elementary charge (C)
const EARTH_FIELD_T = 50e-6; // nominal Earth field (T)
const _NORMAL_METAL_N = 1e29;
const _N_PHYSICAL_MIN = 1e22;
const _N_PHYSICAL_MAX = 1e29;

function _penetrationDepth(bC1T, lnKappa = 1.0) {
  return Math.sqrt((PHI0 * lnKappa) / (4.0 * Math.PI * bC1T));
}

function _superfluidDensity(lambdaM) {
  return M_E / (MU0 * lambdaM * lambdaM * E_CHARGE * E_CHARGE);
}

function _screenMeissner(bC1T = EARTH_FIELD_T, isolatedPremise = true, lnKappa = 1.0) {
  const lam = _penetrationDepth(bC1T, lnKappa);
  const nS = _superfluidDensity(lam);
  let verdict;
  if (isolatedPremise) verdict = "in_tension_with_isolation";
  else if (nS >= _N_PHYSICAL_MIN && nS <= _N_PHYSICAL_MAX) verdict = "implied_density_physical";
  else verdict = "implied_density_unphysical";
  return verdict;
}

export function assessHc06(candidate, measured, th) {
  const m = measured || {};
  if (m.fluxExclusion) {
    return {
      id: "HC-06",
      status: CLAIM_STATUS.SUPPORTED,
      route: ROUTE.CONVENTIONAL,
      note: "measured diamagnetic flux exclusion",
    };
  }
  if (opticalMagneticCausality(m.opticalResult)) {
    return {
      id: "HC-06",
      status: CLAIM_STATUS.SUPPORTED,
      route: ROUTE.OPTICAL,
      note: "measured dM/dP tracks the optical resonance",
    };
  }
  const verdict = _screenMeissner(EARTH_FIELD_T, true, 1.0);
  return { id: "HC-06", status: CLAIM_STATUS.LEAD, route: ROUTE.CONVENTIONAL, note: `Meissner screen: ${verdict}` };
}

// ---- HC-07: superconductivity ---------------------------------------------------------------
export function assessHc07(candidate, measured, th) {
  const m = measured || {};
  if (gConventionalSuperconductivity(m)) {
    return {
      id: "HC-07",
      status: CLAIM_STATUS.SUPPORTED,
      route: ROUTE.CONVENTIONAL,
      note: "measured R->0 + magnetic + thermodynamic",
    };
  }
  if (gCandidateOptical(m.opticalResult)) {
    return {
      id: "HC-07",
      status: CLAIM_STATUS.SUPPORTED,
      route: ROUTE.OPTICAL,
      note: "measured persistent optical transport (Branch B)",
    };
  }
  if (candidate && candidate.creditedScLead) {
    return {
      id: "HC-07",
      status: CLAIM_STATUS.LEAD,
      route: ROUTE.NONE,
      note: "credited_sc_lead (simulation lead, not support)",
    };
  }
  return { id: "HC-07", status: CLAIM_STATUS.CANDIDATE, route: ROUTE.NONE, note: "no SC lead" };
}

// ---- Roll-ups + interim verdict + evaluateLedger (mirror hudson_ledger.evaluate_hudson_ledger
// §5.2 exactly). A "material" = one lineage's worth of evidence:
//   { lineage:{familyId,batchId,aliquotId,processing:[]}, element, witness, distribution,
//     creditedScLead, optical, measured, demo }
// lineage grouping key = familyId/batchId[/processing-joined-by-">"] (mirrors lineage.py's
// lineage_key: same processing_history = same material state; different processing = a new
// lineage node, never stitched to its precursor).

//: CORE claim set for the integrated weakest-link roll-up (mirror hudson_ledger._CORE).
export const CORE = ["HC-01", "HC-02", "HC-04", "HC-06", "HC-07"];

function _lineageKey(lin) {
  const base = `${lin.familyId}/${lin.batchId}`;
  if (lin.processing && lin.processing.length) return base + "/" + lin.processing.join(">");
  return base;
}

function _bareRecord(id) {
  return { id, status: CLAIM_STATUS.CANDIDATE, route: ROUTE.NONE, note: "" };
}

// All eight ClaimRecords for ONE material (mirror _candidate_claim_records exactly). `doublet`
// is the single GLOBAL observed IR doublet (mirrors evaluate_hudson_ledger's observed_doublet
// param — one instrument reading applied to every material, not per-material).
function _materialClaimRecords(material, doublet, th) {
  const m = { ...(material.measured || {}), opticalResult: material.optical || null };

  let hc01 = material.witness != null ? assessHc01(material.witness, material.element, th) : _bareRecord("HC-01");
  if (m.hc01NonmetallicConfirmed && hc01.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED) {
    hc01 = { id: "HC-01", status: CLAIM_STATUS.SUPPORTED, route: hc01.route, note: "measured nonmetallic confirmation" };
  }

  let hc02 = material.distribution != null ? assessHc02(material.distribution, th) : _bareRecord("HC-02");
  if (m.hc02DispersionConfirmed && hc02.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED) {
    hc02 = { id: "HC-02", status: CLAIM_STATUS.SUPPORTED, route: hc02.route, note: "measured dispersion confirmation" };
  }

  const hc03 = assessHc03(m);

  let hc04 = doublet != null ? assessHc04(doublet, th) : _bareRecord("HC-04");
  if (m.hc04IsotopeConfirmed) {
    hc04 = { id: "HC-04", status: CLAIM_STATUS.SUPPORTED, route: hc04.route, note: "measured isotope/atmosphere sensitivity" };
  }

  const hc05 = assessHc05(m);
  const candidate = { creditedScLead: material.creditedScLead };
  const hc06 = assessHc06(candidate, m, th);
  const hc07 = assessHc07(candidate, m, th);
  const hc08 = assessHc08(m);

  return [hc01, hc02, hc03, hc04, hc05, hc06, hc07, hc08];
}

function _groupByLineage(entries) {
  const groups = new Map();
  for (const e of entries) {
    if (!groups.has(e.key)) groups.set(e.key, []);
    groups.get(e.key).push(e);
  }
  return new Map([...groups.keys()].sort().map((k) => [k, groups.get(k)]));
}

// ---- Layer 1: portfolio best-of per claim (max status across materials) -------------------
// `perMaterialRecords` = one 8-length records array per material (fixed HC order).
export function rollupBestOf(perMaterialRecords) {
  const portfolio = [];
  for (let j = 0; j < HC.length; j++) {
    let best = perMaterialRecords[0][j];
    for (let i = 1; i < perMaterialRecords.length; i++) {
      const r = perMaterialRecords[i][j];
      if (r.status > best.status) best = r;
    }
    portfolio.push(best);
  }
  return portfolio;
}

// ---- Layer 2: integrated weakest-link WITHIN one lineage over CORE, then best ACROSS
// lineages (max_lineage(min_claim)) — NEVER min_claim(max_candidate). Existential mechanism/
// conventional gates are each evaluated SAME-LINEAGE, then unioned only at the boolean level
// (never by stitching claim records across lineages); component bits are reported from ONE
// representative lineage (mechanism lineage > conventional-SC lineage > CORE winner).
// `perLineage` = [[key, [{material, records}, ...]], ...] (sorted); `core` = CORE claim ids.
export function rollupIntegrated(perLineage, core, th) {
  const coreIdx = core.map((hc) => HC.indexOf(hc));
  const perLineageStatus = [];
  const lineageBits = new Map();
  let bestStatus = null;
  let bestKey = null;

  for (const [key, entries] of perLineage) {
    const combined = [];
    for (let j = 0; j < HC.length; j++) {
      let best = entries[0].records[j];
      for (let i = 1; i < entries.length; i++) {
        if (entries[i].records[j].status > best.status) best = entries[i].records[j];
      }
      combined.push(best);
    }
    const weakest = Math.min(...coreIdx.map((j) => combined[j].status));
    perLineageStatus.push([key, weakest]);
    if (bestStatus === null || weakest > bestStatus) {
      bestStatus = weakest;
      bestKey = key;
    }

    // Same-lineage gate bits — one representative material's measured/optical payload (aliquots
    // of the same batch carry the same measured evidence, mirroring evaluate_hudson_ledger's
    // measured.get(key) lookup, which is keyed by lineage, not by candidate).
    const rep = entries[0].material;
    const wm = rep.measured || {};
    const opt = rep.optical || null;
    const gId = entries.some((e) => gIdentityEstablished(e.material.witness));
    // G_hudson_material_state from the BATCH-COMBINED records (HC-01 from one aliquot + HC-02
    // from another aliquot of the SAME batch is legitimate same-batch integration).
    const gMat =
      combined[0].status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED &&
      combined[1].status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED;
    const gConv = gConventionalSuperconductivity(wm);
    const gOpt = gCandidateOptical(opt);
    const gCaus = opticalMagneticCausality(opt);
    const gRep = replicationGate(wm.replication, th);
    lineageBits.set(key, {
      gIdentityEstablished: gId,
      gHudsonMaterialState: gMat,
      gConventionalSuperconductivity: gConv,
      gCandidateOptical: gOpt,
      opticalMagneticCausality: gCaus,
      replication: gRep,
      gHudsonMechanism: gMat && gOpt && gCaus && gRep,
    });
  }

  const keysInOrder = [...lineageBits.keys()];
  const mechKeys = keysInOrder.filter((k) => lineageBits.get(k).gHudsonMechanism);
  const convKeys = keysInOrder.filter((k) => lineageBits.get(k).gConventionalSuperconductivity);
  const repKey = mechKeys.length ? mechKeys[0] : convKeys.length ? convKeys[0] : bestKey;
  const defaults = {
    gIdentityEstablished: false,
    gHudsonMaterialState: false,
    gConventionalSuperconductivity: false,
    gCandidateOptical: false,
    opticalMagneticCausality: false,
    replication: false,
    gHudsonMechanism: false,
  };
  const bits = { ...(lineageBits.get(repKey) || defaults) };
  bits.gHudsonMechanism = mechKeys.length > 0; // existential, same-lineage
  bits.gConventionalSuperconductivity = convKeys.length > 0; // existential, separate result

  return {
    integratedStatus: bestStatus === null ? CLAIM_STATUS.CANDIDATE : bestStatus,
    integratedLineageKey: bestKey,
    perLineage: perLineageStatus,
    gate: bits,
  };
}

// ---- interimVerdict: deterministic priority ladder. NEVER returns the forbidden affirmative
// "HUDSON CLAIM VALIDATED" string (the strongest terminal label is independent-replication).
export function interimVerdict(bits) {
  if (bits.gHudsonMechanism && bits.replication) {
    return "independent-replication-achieved (Hudson mechanism supported on one replicated lineage)";
  }
  if (bits.gConventionalSuperconductivity) {
    return "bulk-SC-supported (conventional route; distinct from the Hudson optical mechanism)";
  }
  if (bits.gCandidateOptical) {
    return "SC-like-response (optical coherent transport; mechanism not yet fully closed)";
  }
  if (bits.gHudsonMaterialState) {
    return "novel-phase-candidate (Hudson material state; no transport/magnetism established)";
  }
  if (bits.gIdentityEstablished) {
    return "identity-established (not Hudson-conformant)";
  }
  return "identity-unresolved";
}

// ---- evaluateLedger: the two-layer roll-up + gate assembly + interim verdict, from a list of
// materials (mirror evaluate_hudson_ledger). `opts.doublet` is the single global observed IR
// doublet (may be omitted, mirroring observed_doublet=None).
export function evaluateLedger(materials, { th, doublet } = {}) {
  const entries = materials.map((material) => ({
    key: _lineageKey(material.lineage),
    material,
    records: _materialClaimRecords(material, doublet, th),
  }));
  const portfolio = rollupBestOf(entries.map((e) => e.records));
  const grouped = _groupByLineage(entries);
  const integrated = rollupIntegrated([...grouped.entries()], CORE, th);
  const gate = { ...integrated.gate, interimVerdict: interimVerdict(integrated.gate) };
  return {
    claims: portfolio,
    gate,
    integratedStatus: integrated.integratedStatus,
    integratedLineageId: integrated.integratedLineageKey,
    perLineage: integrated.perLineage,
  };
}

// ---- DOSSIER: the seed material states for the Ledger tab ---------------------------------
// Two frozen groups, never mixed:
//   - conducted-research findings (demo:false) — our actual results, provenance + doc link,
//     exactly like research.js entries. A finding's status is whatever evaluateLedger computes
//     for it (parity-locked by tests/test_ledger_parity.py) — never hand-set here.
//   - illustrative demo states (demo:true) — synthetic lineages carrying partial measured
//     evidence so the interactive controls have something to move and the portfolio-vs-
//     integrated (anti-Frankenstein) divergence is visible. Always labelled "demonstration,
//     not a finding"; never presented as evidence.
const DOC = "https://github.com/Dezirae-Stark/orme-lab/blob/master/docs/";
const DEMO_NOTE = "demonstration, not a finding";

export const DOSSIER = [
  Object.freeze({
    id: "ir-doublet-finding",
    title: "IR doublet — contaminant screen (HC-04)",
    hc: "HC-04",
    demo: false,
    provenance: "ir_contaminant.py · Steill & Oomens 2009 · Deacon & Phillips 1980 · Grigorev 1963 (one-hop)",
    doc: DOC + "patent-claim-tests.md",
    note: "Conducted research: the top mundane match for the 1400-1600 cm^-1 doublet is a plausible " +
      "(not tight) carboxylate — the mundane alternative HC-04 must rule out.",
    lineage: { familyId: "ir-doublet", batchId: "run-1", aliquotId: "ir-doublet", processing: [] },
    element: "Rh",
    witness: null,
    distribution: null,
    creditedScLead: false,
    optical: null,
    measured: {},
  }),
  Object.freeze({
    id: "meissner-finding",
    title: "Meissner Hc1 screen (HC-06)",
    hc: "HC-06",
    demo: false,
    provenance: "meissner_field.py · Tinkham, Introduction to Superconductivity · CODATA 2018 Φ0",
    doc: DOC + "patent-claim-tests.md",
    note: "Conducted research: Hc1≈50µT implies λ/nₛ in tension with the isolated-monomer premise " +
      "(conventional route, screen only — not a measured flux exclusion).",
    lineage: { familyId: "meissner", batchId: "run-1", aliquotId: "meissner", processing: [] },
    element: "Ir",
    witness: null,
    distribution: null,
    creditedScLead: false,
    optical: null,
    measured: {},
  }),
  Object.freeze({
    id: "demo-batch-7",
    title: "demo/batch-7",
    hc: null,
    demo: true,
    provenance: null,
    doc: null,
    note: DEMO_NOTE + " — illustrative measured optical transport (clears HC-07, not HC-06).",
    lineage: { familyId: "demo", batchId: "batch-7", aliquotId: "demo", processing: [] },
    element: "Ir",
    witness: null,
    distribution: null,
    creditedScLead: false,
    optical: {
      supported: [
        HUDSON_CLAIM.STRONG_COUPLING,
        HUDSON_CLAIM.MACRO_COHERENCE,
        HUDSON_CLAIM.LOW_LOSS_TRANSPORT,
        HUDSON_CLAIM.ELECTRONIC_COUPLING,
      ],
      persistence: "persistent",
    },
    measured: {},
  }),
  Object.freeze({
    id: "demo-batch-7-anneal",
    title: "demo/batch-7▸anneal",
    hc: null,
    demo: true,
    provenance: null,
    doc: null,
    note: DEMO_NOTE + " — illustrative measured flux exclusion (clears HC-06, not HC-07); a " +
      "separate processing lineage from demo/batch-7, never stitched to it.",
    lineage: { familyId: "demo", batchId: "batch-7", aliquotId: "demo", processing: ["anneal"] },
    element: "Ir",
    witness: null,
    distribution: null,
    creditedScLead: false,
    optical: null,
    measured: { fluxExclusion: true },
  }),
];

// ---- Default assessment inputs for the Ledger tab (Task 5: static render; Task 6 makes the
// evidence controls live). DEFAULT_TH mirrors DEFAULT_CONFIG.thresholds exactly (see
// tests/test_ledger_parity.py::_th_js — same numbers). DEFAULT_DOUBLET is the single observed
// IR doublet already characterised in research.js (the same (1429.53, 1490.99) cm^-1 pair the
// "contaminant" finding scored as a plausible carboxylate match, residual 0.59).
export const DEFAULT_TH = Object.freeze({
  hc02MinIsolated: 0.85,
  hc02MaxClustered: 0.2,
  hc02ClusterMargin: 0.05,
  hc02PgmPgmTol: 0.15,
  hc02BondLen: 3.2,
  replMinBatches: 3,
  replMinLabs: 2,
});
export const DEFAULT_DOUBLET = Object.freeze([1429.53, 1490.99]);

// ---- status-ladder presentation (label + CSS palette class). Purely cosmetic — never fed back
// into any computed value.
const STATUS_LABEL = [
  "Candidate",
  "Lead",
  "Anomalous",
  "Provisionally Supported",
  "Supported",
  "Independently Replicated",
];
function _statusLabel(status) {
  return STATUS_LABEL[status] || "Candidate";
}
function _statusClass(status) {
  return `lvl-${status}`;
}
const _ROUTE_GLYPH = { [ROUTE.CONVENTIONAL]: "⚡ conv.", [ROUTE.OPTICAL]: "✦ opt.", [ROUTE.NONE]: "" };

// ---- tiny DOM-building helpers. All researcher/derived text goes through textContent — never
// innerHTML (Phase-3 recorder security posture, carried here).
function _el(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text != null) node.textContent = text;
  return node;
}
// Guarded event-attach: real browsers always have addEventListener, but the Task-5 Node/DOM
// smoke shim (tests/test_ledger_render_smoke.py) intentionally exposes a minimal FakeElement
// without it — renderLedger must keep working (no "HUDSON CLAIM VALIDATED", no innerHTML) under
// that shim, so control-wiring never assumes addEventListener exists.
function _on(node, evt, handler) {
  if (node && typeof node.addEventListener === "function") node.addEventListener(evt, handler);
}
// Guarded attribute-set: the Task-5 Node/DOM smoke shim's FakeElement (above) has no
// setAttribute either — same rationale as _on.
function _attr(node, name, value) {
  if (node && typeof node.setAttribute === "function") node.setAttribute(name, value);
}
function _statusDot(status) {
  const dot = _el("span", `status-dot ${_statusClass(status)}`);
  dot.title = _statusLabel(status);
  return dot;
}

// ---- Legend: the status ladder + neutrality banner. ----------------------------------------
function _buildLegend() {
  const wrap = _el("div", "ledger-legend");
  const row = _el("div", "ledger-legend-row");
  for (let s = CLAIM_STATUS.CANDIDATE; s <= CLAIM_STATUS.INDEPENDENTLY_REPLICATED; s++) {
    const item = _el("span", "ledger-legend-item");
    item.appendChild(_statusDot(s));
    item.appendChild(_el("span", "ledger-legend-label", _statusLabel(s)));
    row.appendChild(item);
    if (s < CLAIM_STATUS.INDEPENDENTLY_REPLICATED) row.appendChild(_el("span", "ledger-legend-arrow", "→"));
  }
  wrap.appendChild(row);
  wrap.appendChild(
    _el("p", "ledger-neutrality", "Triage, not proof — the lab never asserts a validated verdict.")
  );
  return wrap;
}

// ---- Roll-up cards: portfolio best-of + integrated max_lineage(min_claim). ------------------
function _bestMaterialsForClaim(entries, hcIdx) {
  let best = null;
  const winners = [];
  for (const e of entries) {
    const rec = e.records[hcIdx];
    if (best === null || rec.status > best) {
      best = rec.status;
      winners.length = 0;
    }
    if (rec.status === best) winners.push(e);
  }
  return { best, winners };
}

function _buildPortfolioCard(entries, portfolioClaims) {
  const card = _el("div", "ledger-card");
  card.appendChild(_el("div", "ledger-card-title", "Portfolio claim coverage"));
  const nCovered = portfolioClaims.filter((c) => c.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED).length;
  card.appendChild(
    _el("p", "ledger-card-sub", `${nCovered} of ${HC.length} claims ≥ Provisionally Supported (best-of, across ALL materials — not one coherent lineage).`)
  );
  // If any covered claim is supported only by demonstration states, say so — the count is not a
  // findings tally.
  const demoDerived = HC.some((hc, j) => portfolioClaims[j].status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED
    && _bestMaterialsForClaim(entries, j).winners.some((w) => w.material.demo));
  if (demoDerived) {
    card.appendChild(_el("p", "ledger-card-note muted",
      "Coverage includes demonstration states (badged DEMO in the matrix) — not findings."));
  }
  const list = _el("div", "ledger-rollup-list");
  HC.forEach((hc, j) => {
    const rec = portfolioClaims[j];
    const row = _el("div", "ledger-rollup-row");
    row.appendChild(_el("span", "ledger-rollup-hc", hc));
    row.appendChild(_statusDot(rec.status));
    row.appendChild(_el("span", "ledger-rollup-status", _statusLabel(rec.status)));
    if (rec.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED) {
      const { winners } = _bestMaterialsForClaim(entries, j);
      const names = winners.map((w) => w.material.title).join(", ");
      row.appendChild(_el("span", "ledger-rollup-via", `via ${names}`));
    } else {
      row.appendChild(_el("span", "ledger-rollup-via muted", "no supporting material"));
    }
    list.appendChild(row);
  });
  card.appendChild(list);
  return card;
}

function _buildIntegratedCard(entries, result) {
  const card = _el("div", "ledger-card");
  card.appendChild(_el("div", "ledger-card-title", "Best coherent same-material candidate"));
  card.appendChild(
    _el(
      "p",
      "ledger-card-sub",
      `integrated = max_lineage(min_claim over CORE) — the strongest SINGLE lineage's weakest-link status, never the best cell from different materials stitched together.`
    )
  );
  const statusRow = _el("div", "ledger-rollup-row");
  statusRow.appendChild(_statusDot(result.integratedStatus));
  statusRow.appendChild(_el("span", "ledger-rollup-status", _statusLabel(result.integratedStatus)));
  const bestEntry = entries.find((e) => e.key === result.integratedLineageId);
  statusRow.appendChild(
    _el("span", "ledger-rollup-via", bestEntry ? `lineage: ${bestEntry.material.title}` : "no lineage clears any core claim")
  );
  card.appendChild(statusRow);

  const gateList = _el("div", "ledger-gate-list");
  const gateRow = (label, value) => {
    const row = _el("div", `ledger-gate-row ${value ? "pass" : "fail"}`);
    row.appendChild(_el("span", "ledger-gate-lbl", label));
    row.appendChild(_el("span", "ledger-gate-val", value ? "closed-with-evidence" : "closed (default-block)"));
    return row;
  };
  gateList.appendChild(gateRow("g_conventional_superconductivity", result.gate.gConventionalSuperconductivity));
  gateList.appendChild(gateRow("g_hudson_mechanism", result.gate.gHudsonMechanism));
  card.appendChild(gateList);
  card.appendChild(_el("p", "ledger-verdict", result.gate.interimVerdict));

  // Anti-Frankenstein divergence, made visible: when the portfolio's best per CORE claim beats
  // the integrated (single-lineage) status, name which material earned each CORE claim so the
  // divergence — never stitched together as a single candidate — is legible.
  const coreIdx = CORE.map((hc) => HC.indexOf(hc));
  const perClaimBest = coreIdx.map((j) => _bestMaterialsForClaim(entries, j));
  const forbiddenMax = Math.max(...perClaimBest.map((b) => (b.best === null ? CLAIM_STATUS.CANDIDATE : b.best)));
  if (forbiddenMax > result.integratedStatus) {
    const reasons = CORE.map((hc, i) => {
      const b = perClaimBest[i];
      if (b.best === null || b.best < CLAIM_STATUS.PROVISIONALLY_SUPPORTED) return null;
      const names = b.winners.map((w) => w.material.title).join("/");
      return `${hc} on ${names}`;
    }).filter(Boolean);
    if (reasons.length) {
      card.appendChild(
        _el("p", "ledger-divergence", `Diverges from the portfolio card: no single material clears the core set — ${reasons.join(", ")}.`)
      );
    }
  }
  return card;
}

// ---- Phase B: two-branch flow render. Reads branchFlow(...) only — no new decision logic, no
// path that lets one branch's evidence fill the other (Branch A stages/result read only
// `bf.conventional.*`; Branch B stages/result read only `bf.hudson.*`).
function _flowStageNode(label, filled) {
  const node = _el("div", "ledger-flow-node" + (filled ? " filled" : ""));
  node.appendChild(_el("span", "ledger-flow-node-lbl", label));
  _attr(node, "aria-label", `${label}: ${filled ? "evidence present" : "no evidence"}`);
  return node;
}

function _flowConn(flowing) {
  return _el("div", "ledger-flow-conn" + (flowing ? " flowing" : ""));
}

function _flowResultNode(label, open) {
  const node = _el("div", "ledger-flow-result" + (open ? " open" : " closed"));
  node.appendChild(_el("span", "ledger-flow-result-lock", open ? "\u{1F513}" : "\u{1F512}"));
  node.appendChild(_el("span", "ledger-flow-result-lbl", label));
  node.appendChild(_el("span", "ledger-flow-result-state", open ? "OPEN" : "CLOSED (DEFAULT-BLOCK)"));
  _attr(node, "aria-label", `${label}: ${open ? "open" : "closed (default-block)"}`);
  return node;
}

// Appends [stage, connector, stage, connector, ...] for a chain of (label, filled) pairs; the
// connector after stage i is `.flowing` iff stage i AND stage i+1 are both filled. Returns the
// filled-state of the LAST stage, so the caller can decide the connector into the result node.
function _appendStageChain(row, stages) {
  let lastFilled = true; // vacuous true before the first stage (no connector precedes it)
  stages.forEach(([label, filled], i) => {
    row.appendChild(_flowStageNode(label, filled));
    if (i < stages.length - 1) row.appendChild(_flowConn(filled && stages[i + 1][1]));
    lastFilled = filled;
  });
  return lastFilled;
}

function _buildBranchFlow(material, doublet, th) {
  const bf = branchFlow(material, doublet, th);

  const section = _el("div", "ledger-flow");
  _attr(section, "role", "region");
  _attr(section, "aria-labelledby", "ledger-flow-heading");
  const heading = _el("h3", "ledger-card-title", `Two-branch flow — ${material.title}`);
  _attr(heading, "id", "ledger-flow-heading");
  section.appendChild(heading);
  section.appendChild(
    _el(
      "p",
      "ledger-card-sub",
      "Conventional superconductivity and the Hudson optical mechanism are independent results — a material may clear one without the other."
    )
  );

  // Branch A · conventional SC — reads ONLY bf.conventional.* (never bf.hudson.*).
  const trackA = _el("div", "ledger-flow-track");
  trackA.appendChild(_el("div", "ledger-flow-label", "Branch A · conventional SC"));
  const rowA = _el("div", "ledger-flow-row");
  const stagesA = [
    ["zero-R", bf.conventional.zeroR],
    ["Meissner flux", bf.conventional.flux],
    ["critical behavior", bf.conventional.critical],
    ["artifact excluded", bf.conventional.artifact],
  ];
  const lastFilledA = _appendStageChain(rowA, stagesA);
  rowA.appendChild(_flowConn(lastFilledA && bf.conventional.result));
  rowA.appendChild(_flowResultNode("G_conventional_superconductivity", bf.conventional.result));
  trackA.appendChild(rowA);
  section.appendChild(trackA);

  // Branch B · Hudson optical — reads ONLY bf.hudson.* (never bf.conventional.*).
  const trackB = _el("div", "ledger-flow-track");
  trackB.appendChild(_el("div", "ledger-flow-label", "Branch B · Hudson optical"));
  const rowB = _el("div", "ledger-flow-row");
  const stagesB = [
    ["coherent mode", bf.hudson.coherentMode],
    ["material coupling", bf.hudson.materialCoupling],
    ["energy transport", bf.hudson.energyTransport],
    ["causal magnetism", bf.hudson.causalMagnetism],
  ];
  const lastFilledB = _appendStageChain(rowB, stagesB);
  rowB.appendChild(_flowConn(lastFilledB && bf.hudson.result));
  rowB.appendChild(_flowResultNode("G_hudson_mechanism", bf.hudson.result));
  trackB.appendChild(rowB);

  // Feeder: Hudson material state + replication join into the same result node above.
  const feederRow = _el("div", "ledger-flow-row ledger-flow-feeder");
  feederRow.appendChild(_flowStageNode("Hudson material state", bf.hudson.materialState));
  feederRow.appendChild(_flowConn(bf.hudson.materialState && bf.hudson.replication));
  feederRow.appendChild(_flowStageNode("replication", bf.hudson.replication));
  feederRow.appendChild(_flowConn(bf.hudson.replication && bf.hudson.result));
  trackB.appendChild(feederRow);
  section.appendChild(trackB);

  return section;
}

// ---- Claim matrix: HC-01..HC-08 rows x material columns. Column headers are clickable — they
// set the focused-material control panel (Task 6); default focus = first material (caller's
// responsibility to pass focusedKey / onFocus consistently with the controls panel below).
function _buildMatrix(entries, focusedKey, onFocus) {
  const wrap = _el("div", "ledger-matrix-wrap");
  const table = _el("table", "ledger-matrix");
  const thead = _el("thead");
  const headRow = _el("tr");
  headRow.appendChild(_el("th", "ledger-matrix-corner", "Claim"));
  entries.forEach((e) => {
    const isFocused = e.key === focusedKey;
    const th = _el("th", "ledger-matrix-colhead" + (isFocused ? " focused" : ""));
    const btn = _el("button", "ledger-matrix-colbtn");
    btn.type = "button";
    btn.appendChild(_el("span", "ledger-matrix-coltitle", e.material.title));
    if (e.material.demo) btn.appendChild(_el("span", "ledger-demo-badge", "demo"));
    _on(btn, "click", () => onFocus(e.key));
    th.appendChild(btn);
    headRow.appendChild(th);
  });
  thead.appendChild(headRow);
  table.appendChild(thead);

  const tbody = _el("tbody");
  HC.forEach((hc, j) => {
    const row = _el("tr");
    row.appendChild(_el("th", "ledger-matrix-rowhead", hc));
    entries.forEach((e) => {
      const rec = e.records[j];
      const td = _el("td", "ledger-matrix-cell");
      const earnedBy = rec.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED ? `, earned by ${e.material.title}` : "";
      _attr(td, "aria-label", `${hc}: ${_statusLabel(rec.status)}${earnedBy}`);
      const dotWrap = _el("div", "ledger-cell-dotwrap");
      dotWrap.appendChild(_statusDot(rec.status));
      if ((hc === "HC-06" || hc === "HC-07") && _ROUTE_GLYPH[rec.route]) {
        dotWrap.appendChild(_el("span", "ledger-route-glyph", _ROUTE_GLYPH[rec.route]));
      }
      td.appendChild(dotWrap);
      if (rec.status >= CLAIM_STATUS.PROVISIONALLY_SUPPORTED) {
        td.appendChild(_el("span", "ledger-cell-material", e.material.title));
        const noteEl = _el("span", "ledger-cell-note", rec.note);
        noteEl.title = rec.note;
        td.appendChild(noteEl);
      }
      row.appendChild(td);
    });
    tbody.appendChild(row);
  });
  table.appendChild(tbody);
  wrap.appendChild(table);
  return wrap;
}

// ---- HC-02 detail: f1 fraction + margin band + PGM-PGM coordination as a bar (never a bare
// checkmark). None of the Phase-A dossier entries carry a StructuralDistribution yet (both
// findings and demo states leave `distribution: null`) — the panel says so honestly rather
// than fabricating a number.
function _buildHc02Detail(entries, th) {
  const panel = _el("div", "ledger-hc02");
  panel.appendChild(_el("div", "ledger-card-title", "HC-02 detail — atomically dispersed"));
  const withDist = entries.find((e) => e.material.distribution != null);
  if (!withDist) {
    panel.appendChild(
      _el("p", "ledger-card-sub", "No structural distribution (f1 / P(n) / nearest-neighbour) loaded for any dossier material — the policy bar reads empty, not clear.")
    );
    const bar = _el("div", "ledger-hc02-bar");
    bar.appendChild(_el("div", "ledger-hc02-bar-fill empty"));
    panel.appendChild(bar);
    return panel;
  }
  const { fSingle, clusteredUb, coordinated } = _hc02Metrics(withDist.material.distribution, th);
  panel.appendChild(_el("p", "ledger-card-sub", `${withDist.material.title} — f_single=${fSingle.toFixed(2)}, clustered_ub=${clusteredUb.toFixed(2)}, pgm-pgm=${coordinated.toFixed(2)} against policy (isolated≥${th.hc02MinIsolated}, clustered≤${th.hc02MaxClustered}, pgm-pgm≤${th.hc02PgmPgmTol}).`));
  const bar = _el("div", "ledger-hc02-bar");
  const fill = _el("div", fSingle >= th.hc02MinIsolated ? "ledger-hc02-bar-fill pass" : "ledger-hc02-bar-fill");
  fill.style.width = `${Math.max(0, Math.min(100, fSingle * 100))}%`;
  bar.appendChild(fill);
  const marker = _el("div", "ledger-hc02-bar-marker");
  marker.style.left = `${th.hc02MinIsolated * 100}%`;
  bar.appendChild(marker);
  panel.appendChild(bar);
  return panel;
}

// ---- Task 6: interactive evidence controls (live recompute) -------------------------------
// State = { focusedLineageId, measuredByLineage }. `measuredByLineage[key]` is a researcher-
// entered overlay — { measured:{...}, optical:{persistence,supported} } — layered onto the
// DOSSIER material with that lineage key when materials are (re)assembled for evaluateLedger.
// Every field here mirrors hudson_ledger.MeasuredEvidence / hudson_optical persistence exactly
// (see src/orme_lab/hudson_ledger.py MeasuredEvidence + hudson_optical.Persistence) — the JS
// never invents a field the Python assessor doesn't read. Module-level so the panel survives
// tab switches within one page load; renderLedger(el) re-seeds it fresh only on first call.
let _state = { focusedLineageId: null, measuredByLineage: {} };

const _PERSISTENCE_STEPS = ["driven_dissipative", "metastable", "persistent"];
const _PERSISTENCE_LABEL = {
  driven_dissipative: "driven-dissipative (decays on the mode timescale)",
  metastable: "metastable (long-lived, not self-sustaining)",
  persistent: "persistent (self-sustaining — Hudson's claim)",
};
// Levels a measured ring-down at metastable-or-better makes available for scoring (excludes the
// causal-magnetism level, which is its own measured toggle below).
const _COHERENT_TRANSPORT_LEVELS = [
  HUDSON_CLAIM.STRONG_COUPLING,
  HUDSON_CLAIM.MACRO_COHERENCE,
  HUDSON_CLAIM.LOW_LOSS_TRANSPORT,
  HUDSON_CLAIM.ELECTRONIC_COUPLING,
];

// Seed (once) a lineage's overlay from its DOSSIER baseline so an untouched material's controls
// reflect what's already loaded (e.g. demo/batch-7's persistent ring-down), and every field the
// Python MeasuredEvidence dataclass carries has an explicit, never-`undefined` default here.
function _getOverlay(key) {
  if (!_state.measuredByLineage[key]) {
    const material = DOSSIER.find((m) => _lineageKey(m.lineage) === key);
    const bm = (material && material.measured) || {};
    const bo = material && material.optical;
    const brep = bm.replication || {};
    _state.measuredByLineage[key] = {
      measured: {
        zeroResistance: Boolean(bm.zeroResistance),
        fluxExclusion: Boolean(bm.fluxExclusion),
        criticalBehavior: Boolean(bm.criticalBehavior),
        artifactExcluded: Boolean(bm.artifactExcluded),
        hc01NonmetallicConfirmed: Boolean(bm.hc01NonmetallicConfirmed),
        hc02DispersionConfirmed: Boolean(bm.hc02DispersionConfirmed),
        hc04IsotopeConfirmed: Boolean(bm.hc04IsotopeConfirmed),
        replication: {
          nBatches: brep.nBatches || 0,
          nLabs: brep.nLabs || 0,
          // The three qualitative attestations are NOT assumed — the Python replication_gate
          // requires all five, so the researcher must affirm them (surfaced as toggles below).
          preregistered: Boolean(brep.preregistered),
          rawRetained: Boolean(brep.rawRetained),
          blindedOk: Boolean(brep.blindedOk),
        },
      },
      optical: {
        persistence: bo ? bo.persistence : "driven_dissipative",
        supported: bo ? [...bo.supported] : [],
      },
    };
  }
  return _state.measuredByLineage[key];
}

// Layer every touched overlay onto the frozen DOSSIER — never mutates DOSSIER itself.
function _materialsWithOverrides() {
  return DOSSIER.map((material) => {
    const key = _lineageKey(material.lineage);
    const overlay = _state.measuredByLineage[key];
    if (!overlay) return material;
    return { ...material, measured: overlay.measured, optical: overlay.optical };
  });
}

function _measuredBadge() {
  return _el("span", "ledger-measured-badge", "measured lab input");
}

function _checkboxRow(labelText, checked, onToggle) {
  const row = _el("label", "ledger-ctrl-row");
  const input = _el("input");
  input.type = "checkbox";
  input.checked = checked;
  _on(input, "change", () => onToggle(input.checked));
  row.appendChild(input);
  row.appendChild(_el("span", "ledger-ctrl-lbl", labelText));
  row.appendChild(_measuredBadge());
  return row;
}

function _numberRow(labelText, value, onInput) {
  const row = _el("label", "ledger-ctrl-row");
  const input = _el("input", "ledger-ctrl-num");
  input.type = "number";
  input.min = "0";
  input.step = "1";
  input.value = String(value);
  _on(input, "change", () => onInput(Math.max(0, Number(input.value) || 0)));
  row.appendChild(input);
  row.appendChild(_el("span", "ledger-ctrl-lbl", labelText));
  row.appendChild(_measuredBadge());
  return row;
}

// ---- Controls panel for the FOCUSED material (Task 6 Interfaces). Mirrors MeasuredEvidence:
// ring-down slider (driven-dissipative -> metastable -> persistent; Branch-B optical transport
// stays shut until persistent — gCandidateOptical requires persistence === "persistent"), the
// on-resonance dM/dP causal-magnetism toggle, zero-R / flux-exclusion / critical-behavior /
// artifact-excluded toggles (Branch A, all-four required), HC-01/02/04 measured confirmations,
// and replication batches/labs. Every control is visually badged "measured lab input", distinct
// from the computed matrix/cards below it. `onChange` triggers the live recompute + re-render.
function _buildControls(materials, focusedKey, onChange) {
  const material = materials.find((m) => _lineageKey(m.lineage) === focusedKey) || materials[0];
  const key = _lineageKey(material.lineage);
  const overlay = _getOverlay(key);

  const panel = _el("div", "ledger-controls");
  panel.appendChild(_el("div", "ledger-card-title", `Evidence controls — ${material.title}`));
  panel.appendChild(
    _el(
      "p",
      "ledger-card-sub",
      "Live recompute for the focused material (click a matrix column header to change focus). Every gate stays default-blocked until you supply it here — nothing on this panel is simulated evidence."
    )
  );

  // Ring-down persistence slider (Branch B).
  const ringBlock = _el("div", "ledger-ctrl-block");
  const ringHead = _el("div", "ledger-ctrl-heading", "ring-down persistence");
  ringHead.appendChild(_measuredBadge());
  ringBlock.appendChild(ringHead);
  const ring = _el("input", "ledger-ctrl-range");
  ring.type = "range";
  ring.min = "0";
  ring.max = "2";
  ring.step = "1";
  ring.value = String(Math.max(0, _PERSISTENCE_STEPS.indexOf(overlay.optical.persistence)));
  _on(ring, "input", () => {
    const step = _PERSISTENCE_STEPS[Number(ring.value)] || _PERSISTENCE_STEPS[0];
    overlay.optical.persistence = step;
    const s = new Set(overlay.optical.supported);
    if (step === _PERSISTENCE_STEPS[0]) {   // driven_dissipative — clear the coherent-transport evidence
      _COHERENT_TRANSPORT_LEVELS.forEach((lvl) => s.delete(lvl));
    } else {
      _COHERENT_TRANSPORT_LEVELS.forEach((lvl) => s.add(lvl));
    }
    overlay.optical.supported = [...s];
    onChange();
  });
  ringBlock.appendChild(ring);
  ringBlock.appendChild(_el("span", "ledger-ctrl-val", _PERSISTENCE_LABEL[overlay.optical.persistence]));
  panel.appendChild(ringBlock);

  panel.appendChild(
    _checkboxRow("on-resonance ∂M/∂P tracks the optical resonance (causal magnetism)", new Set(overlay.optical.supported).has(HUDSON_CLAIM.MAGNETISM_COUPLED), (checked) => {
      const s = new Set(overlay.optical.supported);
      if (checked) s.add(HUDSON_CLAIM.MAGNETISM_COUPLED);
      else s.delete(HUDSON_CLAIM.MAGNETISM_COUPLED);
      overlay.optical.supported = [...s];
      onChange();
    })
  );

  // Branch A (conventional SC) — all four required (gConventionalSuperconductivity).
  panel.appendChild(_checkboxRow("flux exclusion measured (Meissner)", overlay.measured.fluxExclusion, (v) => { overlay.measured.fluxExclusion = v; onChange(); }));
  panel.appendChild(_checkboxRow("zero resistance measured", overlay.measured.zeroResistance, (v) => { overlay.measured.zeroResistance = v; onChange(); }));
  panel.appendChild(_checkboxRow("critical behavior measured", overlay.measured.criticalBehavior, (v) => { overlay.measured.criticalBehavior = v; onChange(); }));
  panel.appendChild(_checkboxRow("artifact excluded", overlay.measured.artifactExcluded, (v) => { overlay.measured.artifactExcluded = v; onChange(); }));

  // Procedural / identity confirmations.
  panel.appendChild(_checkboxRow("HC-01 nonmetallic phase confirmed", overlay.measured.hc01NonmetallicConfirmed, (v) => { overlay.measured.hc01NonmetallicConfirmed = v; onChange(); }));
  panel.appendChild(_checkboxRow("HC-02 dispersion confirmed (EXAFS/STEM/PDF)", overlay.measured.hc02DispersionConfirmed, (v) => { overlay.measured.hc02DispersionConfirmed = v; onChange(); }));
  panel.appendChild(_checkboxRow("HC-04 isotope/atmosphere sensitivity confirmed", overlay.measured.hc04IsotopeConfirmed, (v) => { overlay.measured.hc04IsotopeConfirmed = v; onChange(); }));

  // Replication (default-blocked: needs >= min batches AND >= min labs).
  const repBlock = _el("div", "ledger-ctrl-block");
  const repHead = _el("div", "ledger-ctrl-heading", "replication");
  repHead.appendChild(_measuredBadge());
  repBlock.appendChild(repHead);
  repBlock.appendChild(_numberRow("independent batches", overlay.measured.replication.nBatches, (v) => { overlay.measured.replication.nBatches = v; onChange(); }));
  repBlock.appendChild(_numberRow("independent labs", overlay.measured.replication.nLabs, (v) => { overlay.measured.replication.nLabs = v; onChange(); }));
  // All five attestations are required (parity with hudson_ledger.replication_gate) — the gate
  // cannot reach INDEPENDENTLY_REPLICATED on batches+labs alone.
  repBlock.appendChild(_checkboxRow("preregistered thresholds", overlay.measured.replication.preregistered, (v) => { overlay.measured.replication.preregistered = v; onChange(); }));
  repBlock.appendChild(_checkboxRow("raw/calibration data retained", overlay.measured.replication.rawRetained, (v) => { overlay.measured.replication.rawRetained = v; onChange(); }));
  repBlock.appendChild(_checkboxRow("blinded controls correctly classified", overlay.measured.replication.blindedOk, (v) => { overlay.measured.replication.blindedOk = v; onChange(); }));
  panel.appendChild(repBlock);

  return panel;
}

// ---- Phase C: the 3D material-state stage region (breadcrumb + canvas host + gate legend). ---
// The canvas host div is created ONCE and cached module-level (`_ledger3dCanvasHost`) — every
// `_renderDash` call clears and rebuilds `dash`'s children, but re-appending the SAME cached
// node (never a fresh one) keeps the live WebGL canvas/renderer mounted across re-renders
// instead of tearing it down and recreating it on every focus/evidence change.
let _ledger3dCanvasHost = null;
let _ledger3dMounted = false;

const _GATE3D_LABELS = [
  ["identity", "identity established"],
  ["materialState", "material state"],
  ["transport", "transport"],
  ["magnetism", "magnetism"],
  ["replication", "replication"],
  ["mechanism", "mechanism"],
];

// Text-fallback legend for the six ring gates — always rendered (WebGL or not) so the ring's
// meaning is available without the canvas. Reads gateRing(...) only; no new decision logic.
function _buildGateLegend3d(ring) {
  const legend = _el("div", "ledger3d-legend");
  _attr(legend, "role", "list");
  _attr(legend, "aria-label", "Six-gate ring states");
  _GATE3D_LABELS.forEach(([key, label]) => {
    const open = Boolean(ring[key]);
    const chip = _el(
      "span",
      "ledger3d-gate-chip" + (open ? " open" : " closed") + (key === "mechanism" ? " mechanism" : "")
    );
    _attr(chip, "role", "listitem");
    _attr(chip, "aria-label", `${label}: ${open ? "open" : "closed"}`);
    chip.appendChild(_el("span", "ledger3d-gate-dot"));
    chip.appendChild(_el("span", "ledger3d-gate-lbl", label));
    chip.appendChild(_el("span", "ledger3d-gate-state", open ? "OPEN" : "CLOSED"));
    legend.appendChild(chip);
  });
  return legend;
}

// Lineage breadcrumb for the focused material: family ▸ batch ▸ aliquot ▸ [processing...]. Each
// segment is clickable ONLY when a real DOSSIER material exists at that exact lineage prefix
// (same familyId/batchId, processing truncated to that depth) — never a fabricated node; a
// segment with no matching material renders as inert text.
function _buildCrumb(material, onFocus) {
  const lin = material.lineage;
  const segments = [{ label: lin.familyId, processing: [] }];
  if (lin.batchId !== lin.familyId) segments.push({ label: lin.batchId, processing: [] });
  if (lin.aliquotId !== lin.batchId && lin.aliquotId !== lin.familyId) {
    segments.push({ label: lin.aliquotId, processing: [] });
  }
  (lin.processing || []).forEach((step, i) => {
    segments.push({ label: step, processing: lin.processing.slice(0, i + 1) });
  });

  const currentKey = _lineageKey(lin);
  const crumb = _el("nav", "ledger3d-crumb");
  _attr(crumb, "aria-label", "Material lineage");
  segments.forEach((seg, i) => {
    const target = DOSSIER.find(
      (m) =>
        m.lineage.familyId === lin.familyId &&
        m.lineage.batchId === lin.batchId &&
        JSON.stringify(m.lineage.processing || []) === JSON.stringify(seg.processing)
    );
    if (target) {
      const key = _lineageKey(target.lineage);
      const btn = _el("button", "crumb-node" + (key === currentKey ? " current" : ""));
      btn.type = "button";
      btn.textContent = seg.label;
      _attr(btn, "aria-label", `Focus ${target.title}`);
      _on(btn, "click", () => onFocus(key));
      crumb.appendChild(btn);
    } else {
      crumb.appendChild(_el("span", "crumb-node crumb-node-inert", seg.label));
    }
    if (i < segments.length - 1) crumb.appendChild(_el("span", "crumb-sep", "▸"));
  });
  return crumb;
}

function _buildLedger3dRegion(material, doublet, th, onFocus) {
  const region = _el("div", "ledger3d-region");
  _attr(region, "role", "region");
  _attr(region, "aria-labelledby", "ledger3d-heading");
  const heading = _el("h3", "ledger-card-title", "Material-state stage");
  _attr(heading, "id", "ledger3d-heading");
  region.appendChild(heading);
  region.appendChild(
    _el(
      "p",
      "ledger-card-sub",
      "Schematic — the cluster is a fixed icon, not a computed structure. The six-gate ring and " +
        "O_H polariton read the parity-locked ledger gates below for the focused material only."
    )
  );
  region.appendChild(_buildCrumb(material, onFocus));

  if (!_ledger3dCanvasHost) {
    _ledger3dCanvasHost = _el("div", "ledger3d-canvas");
    _attr(_ledger3dCanvasHost, "role", "img");
    _attr(
      _ledger3dCanvasHost,
      "aria-label",
      "3D material-state stage (schematic; degrades to a text legend without WebGL)"
    );
  }
  region.appendChild(_ledger3dCanvasHost);
  region.appendChild(_buildGateLegend3d(gateRing(material, doublet, th)));
  return region;
}

// Mount once (fire-and-forget async — mountLedger3d never throws, it resolves {ok:false} on any
// failure), then only ever recompute via updateLedger3d on subsequent renders. updateLedger3d
// itself no-ops when the stage never came up (no WebGL) — see ledger3d.js.
function _mountOrUpdateLedger3d(material, doublet, th) {
  if (!_ledger3dMounted) {
    _ledger3dMounted = true;
    mountLedger3d(_ledger3dCanvasHost)
      .then((r) => {
        if (r.ok) updateLedger3d(material, doublet, th);
      })
      .catch(() => {});
  } else {
    updateLedger3d(material, doublet, th);
  }
}

// ---- renderLedger: the full 2D dashboard over evaluateLedger(materials, ...). Task 5 shipped a
// static render from the frozen dossier; Task 6 layers the evidence-controls overlay (state
// above) so any change recomputes evaluateLedger and re-renders the matrix + cards + HC-02
// detail live, without ever mutating DOSSIER itself.
export function renderLedger(el) {
  el.textContent = "";
  const dash = _el("div", "ledger-dash");
  el.appendChild(dash);
  _renderDash(dash);
}

function _renderDash(dash) {
  dash.textContent = "";
  const th = DEFAULT_TH;
  const doublet = DEFAULT_DOUBLET;

  const materials = _materialsWithOverrides();
  const entries = materials.map((material) => ({
    key: _lineageKey(material.lineage),
    material,
    records: _materialClaimRecords(material, doublet, th),
  }));
  const result = evaluateLedger(materials, { th, doublet });

  const focusedKey = _state.focusedLineageId || _lineageKey(DOSSIER[0].lineage);
  const focusedMaterial = materials.find((m) => _lineageKey(m.lineage) === focusedKey) || materials[0];
  const onFocus = (key) => {
    _state.focusedLineageId = key;
    _renderDash(dash);
  };

  // Phase C: the 3D material-state stage region, ahead of the legend — the "spine" the rest of
  // the dashboard relates to. Mounted once; every render (focus change or evidence edit) just
  // recomputes the schematic for the currently-focused material.
  dash.appendChild(_buildLedger3dRegion(focusedMaterial, doublet, th, onFocus));
  _mountOrUpdateLedger3d(focusedMaterial, doublet, th);

  dash.appendChild(_buildLegend());

  const cards = _el("div", "ledger-cards");
  cards.appendChild(_buildPortfolioCard(entries, result.claims));
  cards.appendChild(_buildIntegratedCard(entries, result));
  dash.appendChild(cards);

  dash.appendChild(_buildBranchFlow(focusedMaterial, doublet, th));
  dash.appendChild(_buildMatrix(entries, focusedKey, onFocus));
  dash.appendChild(_buildHc02Detail(entries, th));
  dash.appendChild(_buildControls(materials, focusedKey, () => _renderDash(dash)));
}
