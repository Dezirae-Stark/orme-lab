// web/ledger.js — Hudson Claim Ledger dashboard (Phase A). Parity-locked to hudson_ledger.py.
// Every assessor/gate below is a faithful port of src/orme_lab/hudson_ledger.py (read that file
// for the authoritative thresholds/branch order — this module must not compute anything the
// Python doesn't). Pure/deterministic: no Date, no Math.random, no network.

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
export function assessHc02(distribution, th) {
  const fSingle = distribution.f1;
  const clusteredUb = Math.min(1.0, 1.0 - fSingle + th.hc02ClusterMargin);
  let coordinated = 0.0;
  for (const [dist, frac] of distribution.nnDistances) {
    if (isFinite(dist) && dist <= th.hc02BondLen) coordinated += frac;
  }
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

export function renderLedger(el) {
  el.textContent = "";
  const p = document.createElement("p");
  p.className = "reg-sub";
  p.textContent = "Ledger dashboard loading…";
  el.appendChild(p);
}
