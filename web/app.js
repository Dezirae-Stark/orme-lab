import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import * as SIM from "./sim.js?v=__BUILD__";
import { analyzeCandidate, ask, pingProxy, keyStore, proxyStore } from "./scientist.js?v=__BUILD__";
import { METRICS } from "./metrics.js?v=__BUILD__";
import { renderRegistry, hypothesesForMetric } from "./hypotheses.js?v=__BUILD__";
import { renderPatentTests } from "./patent_tests.js?v=__BUILD__";
import { renderResearch } from "./research.js?v=__BUILD__";

// The eigenstate + DFT-cube feature is the ONLY heavy/optional part of the lab.
// It is loaded LAZILY via dynamic import() rather than a top-level static import,
// so that a single lagging or 404'd module (e.g. mid-CDN-propagation) can at most
// disable its own toggle — it can never throw at module-parse time and abort the
// whole graph before wireControls() runs. That parse-time abort is exactly what
// once blanked the PGM/spin rail. These holders stay null until the module loads.
let Eigen = null;               // { buildEigenstate, buildFromGrid, mRange, MAX_K, MAX_L, energyLabel }
let Cube = null;                // { parseCube }
let eigenModulePromise = null;  // cached in-flight/settled load (null again on failure → retryable)
function loadEigenModule() {
  if (Eigen && Cube) return Promise.resolve(true);
  if (eigenModulePromise) return eigenModulePromise;
  eigenModulePromise = Promise.all([
    import("./eigenstate.js?v=__BUILD__"),
    import("./cube.js?v=__BUILD__"),
  ]).then(([e, c]) => {
    Eigen = e; Cube = c;
    return true;
  }).catch((err) => {
    console.error("[orme-lab] eigenstate/cube feature failed to load:", err);
    eigenModulePromise = null;   // allow a later retry without a page reload
    return false;
  });
  return eigenModulePromise;
}

/* -------------------------------------------------------------------------
 * ORME Lab — interactive 3D front-end.
 * The 3D scene renders the candidate: metallic atoms, the translucent
 * "rice-bean" electron-density ellipsoids, coupling filaments, and the applied
 * magnetic field. All scores are computed live in sim.js (a faithful port of
 * the Python toy models). Nothing here claims proof — the gate cascade can only
 * light up "not ruled out".
 * ---------------------------------------------------------------------- */

const ELEMENT_COLOR = {
  Au: 0xc9a86a, Pt: 0xd8dee9, Pd: 0xccd2da, Ir: 0xc4cad0,
  Rh: 0xd2d6da, Os: 0xaab2be, Ru: 0xc9b79a, Ag: 0xe8ecf1,
};

const state = {
  elSym: "Os", geomKind: "compact13", spinKind: "high", fieldT: 0, tempK: 298.15,
};

// Eigenstate mode (kept separate from `state` so it isn't passed to the sim
// except as the anisotropy override). Default |k=0,l=2,m=0> — a prolate dz².
const eigen = { on: false, k: 0, l: 2, m: 0, cube: null }; // cube: parsed DFT grid or null
let eigenData = null;               // cached { positive, negative, extent, anisotropy, signed }
function rebuildEigen() {
  if (!eigen.on || !Eigen) { eigenData = null; return; }
  // DFT-cube path: if a cube is loaded, isosurface it; else the analytic eigenstate.
  eigenData = eigen.cube ? Eigen.buildFromGrid(eigen.cube) : Eigen.buildEigenstate(eigen.k, eigen.l, eigen.m, 40);
}

// ---- three.js scene ------------------------------------------------------
const stage = document.getElementById("stage");
const scene = new THREE.Scene();
scene.fog = new THREE.FogExp2(0x090c14, 0.012);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 2000);
camera.position.set(14, 9, 18);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
stage.appendChild(renderer.domElement);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.08;
controls.autoRotate = true;
controls.autoRotateSpeed = 0.6;

scene.add(new THREE.AmbientLight(0x4a5a80, 0.9));
const key = new THREE.DirectionalLight(0xffffff, 1.4); key.position.set(8, 14, 10); scene.add(key);
const rim = new THREE.DirectionalLight(0x35d6c4, 0.5); rim.position.set(-10, -4, -8); scene.add(rim);

// subtle ground grid for spatial reference
const grid = new THREE.GridHelper(60, 30, 0x24304a, 0x161d2e);
grid.position.y = -6; scene.add(grid);

const candidateGroup = new THREE.Group();
scene.add(candidateGroup);
const fieldGroup = new THREE.Group();
scene.add(fieldGroup);

// reusable geometries
const sphereGeo = new THREE.SphereGeometry(1, 40, 28);

function clearGroup(g) {
  while (g.children.length) {
    const c = g.children.pop();
    c.geometry?.dispose?.();
    c.material?.dispose?.();
  }
}

function centroid(pts) {
  const c = [0, 0, 0];
  for (const p of pts) { c[0] += p[0]; c[1] += p[1]; c[2] += p[2]; }
  return c.map((x) => x / pts.length);
}

// ---- build the candidate in 3D ------------------------------------------
function buildCandidate(res) {
  clearGroup(candidateGroup);
  const { geom, ellipsoid, scores, sc } = res;
  const col = ELEMENT_COLOR[state.elSym] ?? 0xd8dee9;
  const c0 = centroid(geom.positions);
  const survives = sc.allPassed;

  // atoms (metallic spheres) + density ellipsoids
  for (const p of geom.positions) {
    const x = p[0] - c0[0], y = p[1] - c0[1], z = p[2] - c0[2];

    const atom = new THREE.Mesh(sphereGeo, new THREE.MeshStandardMaterial({
      color: col, metalness: 0.92, roughness: 0.32,
    }));
    atom.scale.setScalar(0.62);
    atom.position.set(x, y, z);
    candidateGroup.add(atom);

    // heuristic "rice-bean" ellipsoid — only when NOT in eigenstate mode.
    if (!eigen.on) {
      const shell = new THREE.Mesh(sphereGeo, new THREE.MeshStandardMaterial({
        color: survives ? 0x35d6c4 : col,
        transparent: true,
        opacity: 0.12 + 0.28 * scores.aniso,
        metalness: 0.0, roughness: 1.0,
        emissive: survives ? 0x1a6b63 : 0x000000,
        emissiveIntensity: survives ? 0.6 : 0.0,
        depthWrite: false,
      }));
      const s = 1.35;
      shell.scale.set(ellipsoid.a * s, ellipsoid.c * s, ellipsoid.b * s);
      shell.position.set(x, y, z);
      candidateGroup.add(shell);
    }
  }

  // eigenstate electron cloud (real |k,l,m> isosurfaces) — replaces the ellipsoids.
  // Two phase lobes in light/deep teal (matching the atomic palette), translucent
  // so atoms and coupling filaments stay visible through the cloud deformation.
  if (eigen.on && eigenData) {
    const scale = 6.0 / eigenData.extent; // normalize display size across states
    const lobe = (arr, colorHex, opacity) => {
      if (!arr || !arr.length) return;
      const g = new THREE.BufferGeometry();
      g.setAttribute("position", new THREE.BufferAttribute(arr, 3));
      g.computeVertexNormals();
      const mesh = new THREE.Mesh(g, new THREE.MeshStandardMaterial({
        color: colorHex, emissive: colorHex, emissiveIntensity: 0.28,
        transparent: true, opacity, metalness: 0.0, roughness: 1.0,
        side: THREE.DoubleSide, depthWrite: false,
      }));
      mesh.scale.setScalar(scale);   // centered at origin == cluster centroid
      candidateGroup.add(mesh);
    };
    lobe(eigenData.positive, 0x7af0e4, 0.40); // positive phase — light teal
    lobe(eigenData.negative, 0x0e5c55, 0.50); // negative phase — deep teal
  }

  // coupling filaments between near neighbours (thickness/opacity ~ coupling)
  const pts = geom.positions;
  const nn = SIM.nearestNeighbor(geom);
  const coupling = scores.coupling;
  if (isFinite(nn) && coupling > 0) {
    const cutoff = 1.25 * nn;
    const linkColor = new THREE.Color(coupling >= 0.5 ? 0x35d6c4 : 0xc9a86a);
    for (let i = 0; i < pts.length; i++)
      for (let j = i + 1; j < pts.length; j++) {
        const a = pts[i], b = pts[j];
        const d = Math.hypot(a[0]-b[0], a[1]-b[1], a[2]-b[2]);
        if (d > cutoff) continue;
        const start = new THREE.Vector3(a[0]-c0[0], a[1]-c0[1], a[2]-c0[2]);
        const end = new THREE.Vector3(b[0]-c0[0], b[1]-c0[1], b[2]-c0[2]);
        const mid = start.clone().add(end).multiplyScalar(0.5);
        const len = start.distanceTo(end);
        const tube = new THREE.Mesh(
          new THREE.CylinderGeometry(0.04 + 0.12 * coupling, 0.04 + 0.12 * coupling, len, 8),
          new THREE.MeshStandardMaterial({
            color: linkColor, transparent: true, opacity: 0.25 + 0.6 * coupling,
            emissive: linkColor, emissiveIntensity: 0.3 * coupling, metalness: 0.5, roughness: 0.5,
          })
        );
        tube.position.copy(mid);
        tube.quaternion.setFromUnitVectors(
          new THREE.Vector3(0, 1, 0),
          end.clone().sub(start).normalize()
        );
        candidateGroup.add(tube);
      }
  }

  // fit camera target to the cluster
  controls.target.set(0, 0, 0);
}

// ---- magnetic field visualization ---------------------------------------
function buildField(res) {
  clearGroup(fieldGroup);
  if (state.fieldT <= 0) return;
  const strength = state.fieldT / 8;
  const n = Math.round(3 + strength * 6);
  const supp = res.scores.supp;
  // field arrows pointing +y; colour warns when the field is suppressing the state
  const col = new THREE.Color(supp < 0.3 ? 0xd66a4a : 0x6aa6d6);
  const span = 9;
  for (let i = 0; i < n; i++) {
    const ang = (i / n) * Math.PI * 2;
    const r = 6;
    const x = Math.cos(ang) * r, z = Math.sin(ang) * r;
    const dir = new THREE.Vector3(0, 1, 0);
    const origin = new THREE.Vector3(x, -span / 2, z);
    const arrow = new THREE.ArrowHelper(dir, origin, span, col.getHex(),
      1.2 + strength, 0.5 + 0.4 * strength);
    arrow.line.material.transparent = true;
    arrow.line.material.opacity = 0.35 + 0.5 * strength;
    fieldGroup.add(arrow);
  }
}

// ---- HUD / readouts ------------------------------------------------------
const $ = (id) => document.getElementById(id);
const pct = (x) => (x * 100).toFixed(0) + "%";
const f3 = (x) => x.toFixed(3);

function updateHUD(res) {
  const { el, st, scores, sc, em } = res;

  $("stageTitle").innerHTML =
    `${el.name} <span class="sub">${el.config} &middot; ${state.geomKind} &middot; ${st.isHigh ? "high" : "low"}-spin &middot; ${st.unpaired} unpaired e⁻</span>`;

  // metrics
  $("mSpin").textContent = f3(scores.spin);
  $("mAniso").textContent = f3(scores.aniso);
  setFlag($("fBean"), scores.bean, "rice-bean", "off-band");
  $("mCoupling").textContent = f3(scores.coupling);
  setFlag($("fIso"), !scores.isolated, "coupled", "isolated");
  $("mCarrier").textContent = f3(scores.carrier);
  $("mSupp").textContent = f3(scores.supp);
  $("mStab").textContent = f3(scores.stability);
  $("mRegime").textContent = scores.regime;

  // gate cascade
  const gnames = {
    coupling: "Inter-unit coupling", carriers: "Carrier / coherence",
    field_tolerance: "Field tolerance", structural_stability: "Structural stability",
    observable_signal: "Measurable observable",
  };
  const cascade = $("cascade");
  cascade.innerHTML = "";
  sc.gates.forEach((g) => {
    const row = document.createElement("div");
    row.className = "gate tappable " + (g.passed ? "pass" : "fail");
    row.dataset.metric = "gate_" + g.name;
    row.setAttribute("role", "button");
    row.tabIndex = 0;
    row.innerHTML = `<span class="led"></span><span class="lbl">${gnames[g.name]}</span>
      <span class="num">${f3(g.value)} / ${g.threshold}</span>`;
    cascade.appendChild(row);
  });

  // verdict bar
  const badge = $("vBadge"), line = $("vLine"), band = $("vBand");
  if (sc.ruledOut) {
    const failed = sc.gates.filter((g) => !g.passed).map((g) => gnames[g.name]);
    badge.className = "badge no"; badge.textContent = "RULED OUT";
    band.hidden = true;
    line.textContent = "Fails necessary condition(s): " + failed.join(", ") + ".";
  } else {
    badge.className = "badge ok"; badge.textContent = "NOT RULED OUT";
    band.hidden = false;
    band.className = "cband cband--" + res.band.key;
    band.textContent = "candidate · " + res.band.label;
    line.textContent = "a triage signal, not evidence of superconductivity. Needs ab-initio + measurement.";
  }
  line.title = "A screening result — a ranking of where to look next, NOT a probability of superconductivity.";
  $("vEvidence").textContent = res.evidence.badge;

  // EM coherence
  $("mEmRegime").textContent = em.regime;
  $("mEmScore").textContent = f3(em.score);
  $("mPlasmon").textContent = em.plasmon.toFixed(2) + " eV";
  drawPlasmon(em);

  // ranking highlight
  markRanking();

  // lab scientist deterministic analysis
  updateScientist(res);
}

// ---- lab scientist -------------------------------------------------------
function esc(str) {
  return String(str).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c]));
}

function updateScientist(res) {
  const a = analyzeCandidate(res);
  const el = $("sciAnalysis");
  const readingHtml = a.reading
    .map((line) => {
      const cls = line.includes("RULED OUT") ? "ro" : line.includes("NOT RULED OUT") ? "ok" : "";
      // highlight the verdict token
      let html = esc(line)
        .replace("NOT RULED OUT", '<span class="ok">NOT RULED OUT</span>')
        .replace(/(?<!NOT )RULED OUT/, '<span class="ro">RULED OUT</span>');
      return `<p class="reading">${html}</p>`;
    })
    .join("");
  const listHtml = (items, cls) =>
    items.length
      ? `<ul>${items.map((i) => `<li class="${cls}">${esc(i)}</li>`).join("")}</ul>`
      : "";
  el.innerHTML =
    readingHtml +
    (a.suggestions.length ? `<div class="sci-block-label">Suggested next moves</div>${listHtml(a.suggestions, "")}` : "") +
    (a.caveats.length ? `<div class="sci-block-label">Caveats</div>${listHtml(a.caveats, "caveat")}` : "");

  // one-line hint on the collapsed header
  $("sciHint").textContent = res.sc.ruledOut
    ? `ruled out — ${res.sc.gates.filter((g) => !g.passed).length} gate(s) failed`
    : `not ruled out — screening score ${res.sc.score.toFixed(3)}`;
}

function addChatMsg(cls, text) {
  const chat = $("sciChat");
  const div = document.createElement("div");
  div.className = "sci-msg " + cls;
  div.textContent = text;
  chat.appendChild(div);
  $("sciBody").scrollTop = $("sciBody").scrollHeight;
  return div;
}

async function askScientist() {
  const input = $("sciInput");
  const q = input.value.trim();
  if (!current) return;
  if (q) addChatMsg("you", q);
  input.value = "";
  const pending = addChatMsg("pending", "thinking…");
  try {
    const { text, via } = await ask(current, q);
    pending.remove();
    const msg = addChatMsg("claude", text);
    const tag = document.createElement("div");
    tag.className = "sci-via";
    tag.textContent = "via " + via;
    msg.appendChild(tag);
  } catch (e) {
    pending.remove();
    addChatMsg("err", e.message);
  }
}

async function refreshProxyStatus() {
  const el = $("sciProxyState");
  if (!el) return;
  el.textContent = "checking…";
  const h = await pingProxy();
  if (h && h.auth && h.auth !== "none") {
    el.innerHTML = `<span class="ok">connected</span> — ${h.auth}${h.token_required ? " · token required" : ""}`;
  } else if (h && h.auth === "none") {
    el.innerHTML = `<span class="ro">running, no credentials</span> — set ANTHROPIC_API_KEY or run \`ant auth login\``;
  } else {
    el.innerHTML = `<span class="off">not running</span> — start <code>python tools/orme-claude-proxy.py</code>`;
  }
}

// ---- view tabs (Lab | Registry) ------------------------------------------
function setTab(name) {
  $("registry").hidden = name !== "registry";
  $("loop").hidden = name !== "loop";
  $("research").hidden = name !== "research";
  document.querySelectorAll(".tab").forEach((t) => {
    const active = t.dataset.tab === name;
    t.classList.toggle("active", active);
    t.setAttribute("aria-selected", String(active));
  });
}

// ---- load a Research-dossier result into the sterile base widgets --------------
// Only fills widget inputs and fires their existing update handlers; never changes
// the underlying model. This is the sole path by which conducted research enters
// the otherwise-sterile Lab tab, and it is always an explicit click.
function loadPreset(entry) {
  if (!entry || !entry.preset) return;
  setTab("lab");
  // Route purely by input id — widget input ids are globally unique. entry.preset.widget
  // is descriptive metadata (which widget the preset targets), not used for routing.
  const ids = Object.keys(entry.preset.inputs);
  for (const id of ids) {
    const node = $(id);
    if (!node) continue;
    node.value = entry.preset.inputs[id];
    node.dispatchEvent(new Event("input", { bubbles: true }));
    node.dispatchEvent(new Event("change", { bubbles: true }));
  }
  const first = ids.length ? $(ids[0]) : null;
  if (first && first.scrollIntoView) first.scrollIntoView({ behavior: "smooth", block: "center" });
  showLoadedToast(entry.title);
}

function showLoadedToast(title) {
  let t = $("loadToast");
  if (!t) {
    t = document.createElement("div");
    t.id = "loadToast";
    t.className = "load-toast";
    document.body.appendChild(t);
  }
  t.textContent = "loaded: " + title;        // textContent — never innerHTML
  t.classList.add("show");
  clearTimeout(showLoadedToast._h);
  showLoadedToast._h = setTimeout(() => t.classList.remove("show"), 2600);
}

// A real digest from the offline generator (orme_lab.lab_loop), embedded so the
// static page shows genuine loop output — the page can't run the Python loop.
const LOOP_DIGEST = `# Autonomous lab-loop digest

_Stopped: budget reached. Evidence ceiling: Level 2/6 — simulation candidate._
_Nothing here is confirmed. A surviving lead is a screening/triage signal,_
_not evidence of superconductivity; independent verification requires physical Level 4-6._

## Hypotheses retired (killed in-sim)
- H5 — by avenue H-Ir-monomer

## Screening leads (NOT RULED OUT — Level <=2 triage signal, not evidence of superconductivity)
- H-Ir-dimer (targeted H5) — worth real computation/measurement, not evidence of SC
- H-Ir-linear_chain (targeted H5) — worth real computation/measurement, not evidence of SC
- H-Ir-compact_cluster (targeted H5) — worth real computation/measurement, not evidence of SC`;

// ---- eigenstate mode controls --------------------------------------------
function eigenRepopulateM() {
  if (!Eigen) return;   // selects are only populated once the optional module is loaded
  const ms = Eigen.mRange(eigen.l);
  if (!ms.includes(eigen.m)) eigen.m = 0;
  $("eigenM").innerHTML = ms.map((v) => `<option value="${v}"${v === eigen.m ? " selected" : ""}>${v}</option>`).join("");
}
function eigenRefreshLabels() {
  // when a DFT cube is loaded it overrides the analytic k/l/m selection
  const cubeOn = !!eigen.cube;
  ["eigenK", "eigenL", "eigenM"].forEach((id) => { $(id).disabled = cubeOn; });
  $("cubeClear").hidden = !cubeOn;
  if (!eigen.on) { $("eigenEnergy").textContent = ""; return; }
  if (cubeOn) {
    $("eigenEnergy").textContent = eigenData && eigenData.signed ? "orbital ψ" : "density ρ";
    $("cubeSource").innerHTML = `source: <strong>DFT cube</strong> — ${escapeHtml(eigen.cube.title || "(loaded)")} · ${eigen.cube.nx}×${eigen.cube.ny}×${eigen.cube.nz}. A computed density (still Level 2 — computational simulation, not an experimental fact).`;
  } else {
    $("eigenEnergy").textContent = Eigen ? Eigen.energyLabel(eigen.k, eigen.l) : "";
    $("cubeSource").innerHTML = 'source: harmonic-oscillator model. Load a Gaussian <code>.cube</code> (real DFT density ρ or an orbital ψ, exported offline) to render the actual calculation through the same pipeline.';
  }
}
function escapeHtml(s) { return String(s).replace(/[&<>]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[c])); }

// The k/l/m selects and the .cube input are wired ONLY after the optional module
// has loaded (they reference its exports). Wired at most once.
let eigenInputsWired = false;
function initEigenInputs() {
  if (eigenInputsWired || !Eigen || !Cube) return;
  const ksel = $("eigenK"), lsel = $("eigenL"), msel = $("eigenM");
  ksel.innerHTML = Array.from({ length: Eigen.MAX_K + 1 }, (_, i) => `<option value="${i}"${i === eigen.k ? " selected" : ""}>${i}</option>`).join("");
  lsel.innerHTML = Array.from({ length: Eigen.MAX_L + 1 }, (_, i) => `<option value="${i}"${i === eigen.l ? " selected" : ""}>${i}</option>`).join("");
  eigenRepopulateM();
  ksel.addEventListener("change", () => { eigen.k = +ksel.value; rebuildEigen(); eigenRefreshLabels(); recompute(); });
  lsel.addEventListener("change", () => { eigen.l = +lsel.value; eigenRepopulateM(); rebuildEigen(); eigenRefreshLabels(); recompute(); });
  msel.addEventListener("change", () => { eigen.m = +msel.value; rebuildEigen(); eigenRefreshLabels(); recompute(); });

  // DFT-cube path: load a Gaussian .cube (parsed client-side), or revert to analytic.
  $("cubeFile").addEventListener("change", (e) => {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      try {
        eigen.cube = Cube.parseCube(String(reader.result));
      } catch (err) {
        eigen.cube = null;
        $("cubeSource").innerHTML = `<span style="color:var(--ruled)">could not parse cube: ${escapeHtml(err.message)}</span>`;
        e.target.value = "";
        return;
      }
      e.target.value = "";
      rebuildEigen(); eigenRefreshLabels(); recompute();
    };
    reader.readAsText(file);
  });
  $("cubeClear").addEventListener("click", () => {
    eigen.cube = null;
    rebuildEigen(); eigenRefreshLabels(); recompute();
  });
  eigenInputsWired = true;
}

// Ensure the optional module is loaded and its inputs are wired. Returns false if
// the module could not be fetched (feature stays off; the core lab is unaffected).
async function ensureEigenFeature() {
  const ok = await loadEigenModule();
  if (ok) initEigenInputs();
  return ok;
}

function setEigenStatus(msg) {
  const el = $("eigenStatus");
  if (!el) return;
  el.textContent = msg || "";
  el.hidden = !msg;
}

// Only the toggle is wired at boot — it is safe (references no module export) and
// pulls the heavy module in on demand. Turning the feature ON awaits the load;
// turning it OFF never needs the module.
function wireEigenToggle() {
  const toggle = $("eigenToggle");
  toggle.addEventListener("click", async () => {
    if (!eigen.on) {
      // turning ON — the optional module must be present first
      toggle.disabled = true;
      setEigenStatus("loading…");
      const ok = await ensureEigenFeature();
      toggle.disabled = false;
      if (!ok) {
        setEigenStatus("module unavailable — core lab unaffected; try again shortly");
        return;   // stay off; nothing else in the app is touched
      }
      setEigenStatus("");
    }
    eigen.on = !eigen.on;
    toggle.setAttribute("aria-pressed", String(eigen.on));
    $("eigenControls").hidden = !eigen.on;
    rebuildEigen(); eigenRefreshLabels(); recompute();
  });

  // Warm the module in the background so the first click is instant — but a
  // failure here is silent and harmless (the click path will retry + report).
  loadEigenModule().then((ok) => { if (ok) initEigenInputs(); });
}

function wireTabs() {
  renderRegistry($("regBody"));
  renderPatentTests($("patentWidgets"));
  renderResearch($("researchBody"), loadPreset);
  const digestEl = $("loopDigest");
  if (digestEl) digestEl.textContent = LOOP_DIGEST;   // real loop output
  document.querySelectorAll(".tab").forEach((t) =>
    t.addEventListener("click", () => setTab(t.dataset.tab)));
  $("regClose").addEventListener("click", () => setTab("lab"));
  const loopClose = $("loopClose");
  if (loopClose) loopClose.addEventListener("click", () => setTab("lab"));
  const researchClose = $("researchClose");
  if (researchClose) researchClose.addEventListener("click", () => setTab("lab"));
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && (!$("registry").hidden || !$("loop").hidden || !$("research").hidden)) setTab("lab");
  });
}

// ---- metric inspector ----------------------------------------------------
let lastFocused = null;
function openMetric(key) {
  const m = METRICS[key];
  if (!m || !current) return;
  lastFocused = document.activeElement;
  $("mmEyebrow").textContent = m.eyebrow;
  $("mmTitle").textContent = m.title;
  $("mmValue").textContent = m.get(current);
  $("mmDef").textContent = m.definition;
  $("mmCalc").textContent = m.calculation;
  $("mmExp").textContent = m.experimental;
  $("mmConfidence").textContent = m.confidence;
  $("mmFuture").textContent = m.future;
  $("mmSource").textContent = m.source;
  // related hypotheses (reverse cross-link back to the registry)
  const related = hypothesesForMetric(key);
  const hypDd = $("mmHyp"), hypDt = $("mmHypDt");
  if (related.length) {
    hypDd.innerHTML = related
      .map((h) => `<button class="mm-hyp" data-hyp="${h.id}" title="${h.statement.replace(/"/g, "&quot;")}">${h.id}</button>`)
      .join(" ");
    hypDd.hidden = false; hypDt.hidden = false;
  } else {
    hypDd.hidden = true; hypDt.hidden = true;
  }
  $("metricModal").hidden = false;
  $("mmClose").focus();
}

// Registry → lab: jump from a hypothesis card to its live metric inspector.
function inspectFromRegistry(metricKey) {
  setTab("lab");
  openMetric(metricKey);
}
// Lab → registry: jump from a metric's related-hypothesis chip to its card.
function jumpToHypothesis(id) {
  closeMetric();
  setTab("registry");
  const card = document.getElementById("hyp-" + id);
  if (card) {
    card.scrollIntoView({ behavior: "smooth", block: "center" });
    card.classList.remove("hyp-flash"); void card.offsetWidth; // restart animation
    card.classList.add("hyp-flash");
  }
}
function closeMetric() {
  $("metricModal").hidden = true;
  if (lastFocused && lastFocused.focus) lastFocused.focus();
}

function handleInspectorTarget(target) {
  const hyp = target.closest("[data-hyp]");
  if (hyp) { jumpToHypothesis(hyp.dataset.hyp); return true; }
  const inspect = target.closest("[data-inspect]");
  if (inspect) { inspectFromRegistry(inspect.dataset.inspect); return true; }
  const metric = target.closest("[data-metric]");
  if (metric) { openMetric(metric.dataset.metric); return true; }
  return false;
}

function wireMetricInspector() {
  // delegated open: metric rows / gate rows / verdict badge+band ([data-metric]),
  // registry cards ([data-inspect]), and related-hypothesis chips ([data-hyp]).
  document.body.addEventListener("click", (e) => handleInspectorTarget(e.target));
  document.body.addEventListener("keydown", (e) => {
    if (e.key !== "Enter" && e.key !== " ") return;
    const el = e.target.closest?.('[data-metric],[data-inspect],[data-hyp]');
    if (el) { e.preventDefault(); handleInspectorTarget(e.target); }
  });
  // close: ✕, overlay click, Escape
  $("mmClose").addEventListener("click", closeMetric);
  $("metricModal").addEventListener("click", (e) => { if (e.target.id === "metricModal") closeMetric(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !$("metricModal").hidden) closeMetric(); });
}

function wireScientist() {
  const toggle = $("sciToggle");
  toggle.addEventListener("click", () => {
    const body = $("sciBody");
    const open = body.hidden;
    body.hidden = !open;
    toggle.setAttribute("aria-expanded", String(open));
    if (open) refreshProxyStatus();  // re-check proxy each time the drawer opens
  });
  $("sciSend").addEventListener("click", askScientist);
  $("sciInput").addEventListener("keydown", (e) => { if (e.key === "Enter") askScientist(); });

  // local proxy settings
  const proxyUrl = $("sciProxyUrl"), proxyToken = $("sciProxyToken");
  proxyUrl.value = proxyStore.url();
  proxyToken.value = proxyStore.token();
  $("sciProxySave").addEventListener("click", () => {
    proxyStore.setUrl(proxyUrl.value || "http://127.0.0.1:8787");
    proxyStore.setToken(proxyToken.value);
    refreshProxyStatus();
  });
  $("sciProxyCheck").addEventListener("click", refreshProxyStatus);

  // direct key settings
  const keyInput = $("sciKey"), modelSel = $("sciModel"), state = $("sciKeyState");
  const refreshState = () => {
    state.textContent = keyStore.get() ? "key saved (this browser only)" : "no key set";
    modelSel.value = keyStore.model();
  };
  refreshState();
  $("sciSaveKey").addEventListener("click", () => {
    if (keyInput.value.trim()) { keyStore.set(keyInput.value); keyInput.value = ""; }
    keyStore.setModel(modelSel.value);
    refreshState();
  });
  $("sciClearKey").addEventListener("click", () => { keyStore.clear(); refreshState(); });
  modelSel.addEventListener("change", () => keyStore.setModel(modelSel.value));
}

function setFlag(node, on, onText, offText) {
  node.className = "flag " + (on ? "on" : "off");
  node.textContent = on ? onText : offText;
}

// ---- plasmon spectrum canvas --------------------------------------------
const specCanvas = $("plasmon");
const sctx = specCanvas.getContext("2d");
function drawPlasmon(em) {
  const w = specCanvas.width = specCanvas.clientWidth * 2;
  const h = specCanvas.height = specCanvas.clientHeight * 2;
  sctx.clearRect(0, 0, w, h);
  const maxE = 16; // eV axis
  const toX = (e) => (e / maxE) * w;
  const peak = (cx, color, amp) => {
    const width = w * 0.03;
    sctx.beginPath();
    for (let x = 0; x <= w; x += 2) {
      const y = h - amp * h * 0.8 * Math.exp(-((x - cx) ** 2) / (2 * width * width));
      x === 0 ? sctx.moveTo(x, y) : sctx.lineTo(x, y);
    }
    sctx.strokeStyle = color; sctx.lineWidth = 3; sctx.stroke();
  };
  // baseline
  sctx.strokeStyle = "#24304a"; sctx.lineWidth = 1;
  sctx.beginPath(); sctx.moveTo(0, h - 1); sctx.lineTo(w, h - 1); sctx.stroke();
  const strong = em.regime !== "weak";
  peak(toX(em.split.longitudinal), strong ? "#35d6c4" : "#8792a8", 0.9);
  peak(toX(em.split.transverse), "#c9a86a", 0.7);
  $("specL").textContent = "L " + em.split.longitudinal.toFixed(1) + " eV";
  $("specT").textContent = em.split.transverse.toFixed(1) + " eV";
}

// ---- ranking table -------------------------------------------------------
function buildRanking() {
  const rows = SIM.runScreen(state.fieldT, state.tempK).slice(0, 12);
  const tb = $("rankBody");
  tb.innerHTML = "";
  rows.forEach((r) => {
    const tr = document.createElement("tr");
    tr.dataset.el = r.element; tr.dataset.geom = r.geometry; tr.dataset.spin = r.spin;
    tr.innerHTML =
      `<td>${r.element}</td><td>${r.geometry}</td><td>${r.spin[0]}</td>
       <td>${r.coupling.toFixed(2)}</td>
       <td class="${r.ruledOut ? "ro" : "ok"}">${r.ruledOut ? "—" : r.plausibility.toFixed(3)}</td>`;
    tr.addEventListener("click", () => {
      state.elSym = r.element; state.geomKind = r.geometry; state.spinKind = r.spin;
      syncControls(); recompute();
    });
    tb.appendChild(tr);
  });
  markRanking();
}
function markRanking() {
  document.querySelectorAll("#rankBody tr").forEach((tr) => {
    tr.classList.toggle("cur",
      tr.dataset.el === state.elSym && tr.dataset.geom === state.geomKind && tr.dataset.spin === state.spinKind);
  });
}

// ---- recompute + wire ----------------------------------------------------
let current;
function recompute() {
  const anisotropyOverride = eigen.on && eigenData ? eigenData.anisotropy : undefined;
  current = SIM.evaluateCandidate({ ...state, anisotropyOverride });
  buildCandidate(current);
  buildField(current);
  updateHUD(current);
}

function syncControls() {
  document.querySelectorAll("#elChips .chip").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.el === state.elSym));
  document.querySelectorAll("#spinChips .chip").forEach((c) =>
    c.setAttribute("aria-pressed", c.dataset.spin === state.spinKind));
  $("geomSel").value = state.geomKind;
}

function wireControls() {
  // element chips
  const elChips = $("elChips");
  SIM.CORE_SCREEN.concat(["Ru", "Ag"]).forEach((sym) => {
    const b = document.createElement("button");
    b.className = "chip"; b.dataset.el = sym; b.textContent = sym;
    b.setAttribute("aria-pressed", sym === state.elSym);
    b.addEventListener("click", () => { state.elSym = sym; syncControls(); recompute(); });
    elChips.appendChild(b);
  });
  // geometry select
  const gsel = $("geomSel");
  SIM.GEOMETRIES.forEach((g) => {
    const o = document.createElement("option"); o.value = g; o.textContent = g; gsel.appendChild(o);
  });
  gsel.value = state.geomKind;
  gsel.addEventListener("change", () => { state.geomKind = gsel.value; recompute(); });
  // spin chips
  const spinChips = $("spinChips");
  [["high", "high-spin"], ["low", "low-spin"]].forEach(([k, label]) => {
    const b = document.createElement("button");
    b.className = "chip spin"; b.dataset.spin = k; b.textContent = label;
    b.setAttribute("aria-pressed", k === state.spinKind);
    b.addEventListener("click", () => { state.spinKind = k; syncControls(); recompute(); });
    spinChips.appendChild(b);
  });
  // field slider
  const fs = $("fieldSlider");
  fs.addEventListener("input", () => {
    state.fieldT = parseFloat(fs.value);
    $("fieldVal").textContent = state.fieldT.toFixed(1) + " T";
    buildRanking(); recompute();
  });
  // temperature slider
  const ts = $("tempSlider");
  ts.addEventListener("input", () => {
    state.tempK = parseFloat(ts.value);
    $("tempVal").textContent = state.tempK.toFixed(0) + " K";
    buildRanking(); recompute();
  });
  // auto-rotate toggle
  $("rotToggle").addEventListener("click", (e) => {
    controls.autoRotate = !controls.autoRotate;
    e.target.setAttribute("aria-pressed", controls.autoRotate);
  });
}

// ---- resize + render loop ------------------------------------------------
function resize() {
  const w = stage.clientWidth, h = stage.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h; camera.updateProjectionMatrix();
}
window.addEventListener("resize", () => { resize(); if (current) drawPlasmon(current.em); });

function loop() {
  requestAnimationFrame(loop);
  controls.update();
  renderer.render(scene, camera);
}

// ---- boot ----------------------------------------------------------------
// Each step is isolated: a throw in one wiring step is logged and skipped rather
// than aborting the rest of boot. Combined with the lazy eigenstate import above,
// no single feature (or lagging file) can blank the core lab controls again.
function safe(name, fn) {
  try { fn(); } catch (err) { console.error(`[orme-lab] boot step "${name}" failed:`, err); }
}
safe("controls", wireControls);
safe("scientist", wireScientist);
safe("metric-inspector", wireMetricInspector);
safe("tabs", wireTabs);
safe("eigenstate-toggle", wireEigenToggle);
safe("ranking", buildRanking);
safe("resize", resize);
safe("recompute", recompute);
loop();
