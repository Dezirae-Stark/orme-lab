// web/ledger3d.js — Ledger tab's 3D "material-state stage" (Phase C).
//
// SCHEMATIC HONESTY: the atom cluster below is a fixed icon (a small fixed offset lattice, NOT a
// computed structure — same honesty posture as vibration.js). The six-gate ring reads ONLY the
// parity-locked gates exported by ledger.js (gateRing()/branchFlow()) — this module computes no
// new decision logic of its own. The mechanism node (ring gate 6, the keystone) reads CLOSED
// until its conjunction is met; this module never renders the string "HUDSON CLAIM VALIDATED".
// The O_H polariton is a schematic pulse keyed to material.optical.persistence, not a physical
// simulation.
//
// GUARDED: `three` and `three/addons/controls/OrbitControls.js` are loaded via *dynamic* import
// (not a static top-level import) so that any failure to resolve them — same as a WebGL context
// failure — degrades gracefully to a `.ledger3d-nowebgl` note instead of aborting module load.
// This also reuses the exact same CDN `three` importmap the Lab stage already loads: no new
// network egress, just a deferred fetch of the identical specifier. Every renderer/controls/
// scene use below is gated on `stage3d`; the rAF loop no-ops (but keeps polling) when `!stage3d`
// or the `#ledger` tab overlay is hidden, so nothing renders into a detached/invisible canvas.
//
// DETERMINISM: no Date.now/Math.random/new Date anywhere in this file. `performance.now()` is
// used exclusively inside the render loop to animate the polariton pulse — never returned or
// serialized as a computed value.
import { gateRing, branchFlow } from "./ledger.js?v=__BUILD__";

// ---- module-scope renderer state (all null until a successful mount) ---------------------
let THREE = null;
let renderer = null, controls = null, scene = null, camera = null;
let stage3d = false;
let clusterGroup = null, ringGroup = null, polaritonGroup = null;
let current = null;          // { material, ring, coherent, persistence } — last built stage
let reducedMotion = false;
let _loopStarted = false;
let _containerRef = null;

// geometries/materials are created lazily (after THREE resolves) and reused across rebuilds.
let _sphereGeo = null, _nodeGeo = null, _keystoneGeo = null, _torusGeo = null;

// Small self-contained element palette (a subset of app.js's ELEMENT_COLOR, kept local per the
// plan's "simplified and self-contained" instruction — this module does not import from app.js).
const ELEMENT_COLOR = {
  Au: 0xc9a86a, Pt: 0xd8dee9, Pd: 0xccd2da, Ir: 0xc4cad0,
  Rh: 0xd2d6da, Os: 0xaab2be, Ru: 0xc9b79a, Ag: 0xe8ecf1,
};
const DEFAULT_COLOR = 0xd8dee9;

// A fixed, non-physical offset lattice for the schematic cluster icon (center + six around it).
const _SCHEMATIC_OFFSETS = [
  [0, 0, 0],
  [1.15, 0, 0], [-1.15, 0, 0],
  [0, 1.15, 0], [0, -1.15, 0],
  [0, 0, 1.15], [0, 0, -1.15],
];

// Ring gate order + display labels (mirrors gateRing's returned keys exactly).
const GATE_ORDER = ["identity", "materialState", "transport", "magnetism", "replication", "mechanism"];

function _visible() {
  const overlay = typeof document !== "undefined" ? document.getElementById("ledger") : null;
  return !overlay || !overlay.hidden;
}

function _appendFallbackNote(container, err) {
  if (typeof console !== "undefined" && console.warn) {
    console.warn("[orme-lab] ledger3d stage unavailable (no WebGL / three failed to load).", err);
  }
  if (!container || typeof container.appendChild !== "function") return;
  const note = document.createElement("div");
  note.className = "ledger3d-nowebgl";
  note.textContent = "3D material-state stage unavailable (WebGL required); the dashboard below is fully usable.";
  container.appendChild(note);
}

function _resize(container) {
  if (!stage3d || !renderer || !camera || !container) return;
  const w = container.clientWidth, h = container.clientHeight;
  if (!w || !h) return;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}

function _clearGroups() {
  [clusterGroup, ringGroup, polaritonGroup].forEach((g) => {
    if (!g) return;
    while (g.children.length) {
      const c = g.children.pop();
      c.geometry?.dispose?.();
      c.material?.dispose?.();
    }
  });
  if (polaritonGroup) polaritonGroup.userData = {};
}

function _buildCluster(element) {
  const col = ELEMENT_COLOR[element] ?? DEFAULT_COLOR;
  for (const [x, y, z] of _SCHEMATIC_OFFSETS) {
    const atom = new THREE.Mesh(_sphereGeo, new THREE.MeshStandardMaterial({
      color: col, metalness: 0.85, roughness: 0.35,
    }));
    atom.scale.setScalar(0.42);
    atom.position.set(x, y, z);
    clusterGroup.add(atom);
  }
  // translucent rice-bean shell — schematic density icon, not a computed density.
  const shell = new THREE.Mesh(_sphereGeo, new THREE.MeshStandardMaterial({
    color: col, transparent: true, opacity: 0.13, metalness: 0, roughness: 1, depthWrite: false,
  }));
  shell.scale.setScalar(1.95);
  clusterGroup.add(shell);
}

function _buildRing(ring) {
  const R = 3.1;
  GATE_ORDER.forEach((key, i) => {
    const angle = (i / GATE_ORDER.length) * Math.PI * 2;
    const open = !!ring[key];
    const isMechanism = key === "mechanism";
    const geo = isMechanism ? _keystoneGeo : _nodeGeo;
    const color = open ? (isMechanism ? 0xd4af37 : 0x35d6c4) : 0x394760;
    const node = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({
      color,
      emissive: open ? color : 0x000000,
      emissiveIntensity: open ? (isMechanism ? 0.85 : 0.55) : 0,
      metalness: 0.3, roughness: 0.5,
    }));
    node.position.set(Math.cos(angle) * R, isMechanism ? 0.45 : 0, Math.sin(angle) * R);
    node.scale.setScalar(isMechanism ? 0.4 : 0.28);
    node.userData.gate = key;
    ringGroup.add(node);
  });
}

// coherent + persistence come from branchFlow(...).hudson.coherentMode / material.optical.persistence
// — never a new computation. Absent (no coherent mode, or driven_dissipative) = no mesh at all.
function _buildPolariton(coherent, persistence) {
  if (!coherent || !persistence || persistence === "driven_dissipative") return;
  const baseOpacity = persistence === "persistent" ? 0.85 : 0.4;
  const emissiveIntensity = persistence === "persistent" ? 0.85 : 0.4;
  const torus = new THREE.Mesh(_torusGeo, new THREE.MeshStandardMaterial({
    color: 0x7af0e4, emissive: 0x35d6c4, emissiveIntensity,
    transparent: true, opacity: baseOpacity, metalness: 0, roughness: 0.6, depthWrite: false,
  }));
  torus.rotation.x = Math.PI / 2.4;
  polaritonGroup.add(torus);
  polaritonGroup.userData = { persistence, baseOpacity };
}

// Render-loop-only animation (performance.now() here, never in a returned/serialized value).
function _animatePolariton(t) {
  if (!polaritonGroup || !polaritonGroup.children.length) return;
  const { persistence, baseOpacity } = polaritonGroup.userData;
  const speed = reducedMotion ? 0 : (persistence === "persistent" ? 0.0016 : 0.001);
  const amp = reducedMotion ? 0 : 0.15;
  const phase = Math.sin(t * speed) * amp;
  polaritonGroup.children.forEach((mesh) => {
    mesh.material.opacity = Math.max(0.05, baseOpacity + phase);
    if (!reducedMotion) mesh.rotation.z += 0.002;
  });
}

function _loop(t) {
  if (!stage3d || !_visible()) {
    requestAnimationFrame(_loop);
    return;
  }
  requestAnimationFrame(_loop);
  controls.update();
  _animatePolariton(typeof t === "number" ? t : performance.now());
  renderer.render(scene, camera);
}

// ---- mountLedger3d(container): guarded async mount. Returns { ok } — true iff the renderer is
// live; on any failure (WebGL unavailable, or `three` fails to resolve/load) appends a
// `.ledger3d-nowebgl` note into `container` and returns { ok:false }. Never throws.
export async function mountLedger3d(container) {
  _containerRef = container;
  try {
    const [threeMod, controlsMod] = await Promise.all([
      import("three"),
      import("three/addons/controls/OrbitControls.js"),
    ]);
    THREE = threeMod;
    const OrbitControlsCtor = controlsMod.OrbitControls;

    // The one call that needs a real WebGL context — guarded exactly like app.js's stage.
    renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    stage3d = true;

    const w = (container && container.clientWidth) || 360;
    const h = (container && container.clientHeight) || 360;
    renderer.setPixelRatio(Math.min((typeof window !== "undefined" && window.devicePixelRatio) || 1, 2));
    renderer.setSize(w, h);
    if (container && typeof container.appendChild === "function") container.appendChild(renderer.domElement);

    scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x090c14, 0.035);
    camera = new THREE.PerspectiveCamera(45, w / h, 0.1, 200);
    camera.position.set(6, 4, 8);

    scene.add(new THREE.AmbientLight(0x4a5a80, 0.9));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.2);
    keyLight.position.set(6, 8, 6);
    scene.add(keyLight);
    const rimLight = new THREE.DirectionalLight(0x35d6c4, 0.5);
    rimLight.position.set(-6, -3, -4);
    scene.add(rimLight);

    _sphereGeo = new THREE.SphereGeometry(1, 24, 18);
    _nodeGeo = new THREE.SphereGeometry(1, 16, 12);
    _keystoneGeo = new THREE.OctahedronGeometry(1, 0);
    _torusGeo = new THREE.TorusGeometry(3.6, 0.12, 12, 48);

    clusterGroup = new THREE.Group(); scene.add(clusterGroup);
    ringGroup = new THREE.Group(); scene.add(ringGroup);
    polaritonGroup = new THREE.Group(); scene.add(polaritonGroup);

    controls = new OrbitControlsCtor(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.08;
    controls.autoRotate = false;

    reducedMotion = !!(typeof window !== "undefined" && window.matchMedia
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches);

    if (typeof ResizeObserver !== "undefined" && container) {
      const ro = new ResizeObserver(() => _resize(container));
      ro.observe(container);
    }

    if (!_loopStarted) {
      _loopStarted = true;
      requestAnimationFrame(_loop);
    }
    return { ok: true };
  } catch (err) {
    stage3d = false;
    _appendFallbackNote(container, err);
    return { ok: false };
  }
}

// ---- updateLedger3d(material, doublet, th): rebuild the cluster + ring + polariton for the
// focused material. No-ops entirely when the stage isn't live (no WebGL). Pure rebuild — reads
// gateRing()/branchFlow() only, never computes a gate itself.
export function updateLedger3d(material, doublet, th) {
  if (!stage3d || !material) return;
  _clearGroups();
  _buildCluster(material.element);
  const ring = gateRing(material, doublet, th);
  _buildRing(ring);
  const bf = branchFlow(material, doublet, th);
  const persistence = material.optical ? material.optical.persistence : null;
  _buildPolariton(bf.hudson.coherentMode, persistence);
  current = { material, ring, coherent: bf.hudson.coherentMode, persistence };
}
