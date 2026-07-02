/*
 * eigenstate.js -- 3D isotropic quantum harmonic-oscillator eigenstates |k,l,m>.
 *
 * Renders the ACTUAL wavefunction (not a heuristic ellipsoid): analytic ψ on a
 * grid → isosurfaces via marching tetrahedra → the two phase lobes. The density
 * anisotropy is computed from the real |ψ|² second-moment tensor, so the
 * visualization drives the metric.
 *
 * Honest scope: the harmonic well is a MODEL potential (an exactly-solvable,
 * physically-legible stand-in), not the real atomic/cluster potential — that is
 * DFT territory (the backends.py seams). This stays a Level-2 simulation
 * artifact; it upgrades the *descriptor* (anisotropy from a real wavefunction),
 * not the evidence level. THREE-free: returns plain arrays; app.js builds meshes.
 *
 *   Energy:  E = (2k + l + 3/2) ħω .
 */

// Real solid harmonics C_lm(x,y,z) ∝ r^l Y_lm — correct shape and sign, l = 0..3.
function solidHarmonic(l, m, x, y, z) {
  const r2 = x * x + y * y + z * z;
  switch (l) {
    case 0: return 1;
    case 1:
      if (m === -1) return y;
      if (m === 0) return z;
      if (m === 1) return x;
      break;
    case 2:
      if (m === -2) return x * y;
      if (m === -1) return y * z;
      if (m === 0) return 3 * z * z - r2;      // 3z² − r²
      if (m === 1) return x * z;
      if (m === 2) return x * x - y * y;
      break;
    case 3:
      if (m === -3) return y * (3 * x * x - y * y);
      if (m === -2) return x * y * z;
      if (m === -1) return y * (5 * z * z - r2);
      if (m === 0) return z * (5 * z * z - 3 * r2);
      if (m === 1) return x * (5 * z * z - r2);
      if (m === 2) return z * (x * x - y * y);
      if (m === 3) return x * (x * x - 3 * y * y);
      break;
  }
  return 0;
}

// Associated Laguerre L_k^α(x) by recurrence.
function laguerre(k, alpha, x) {
  if (k <= 0) return 1;
  let l0 = 1, l1 = 1 + alpha - x;
  for (let i = 1; i < k; i++) {
    const l2 = ((2 * i + 1 + alpha - x) * l1 - (i + alpha) * l0) / (i + 1);
    l0 = l1; l1 = l2;
  }
  return l1;
}

/** ψ_{k,l,m}(x,y,z) in oscillator units (radial × angular × Gaussian). */
export function psi(k, l, m, x, y, z) {
  const r2 = x * x + y * y + z * z;
  return solidHarmonic(l, m, x, y, z) * Math.exp(-r2 / 2) * laguerre(k, l + 0.5, r2);
}

export const MAX_L = 3;
export const MAX_K = 4;
export const mRange = (l) => Array.from({ length: 2 * l + 1 }, (_, i) => i - l);
export const energyLabel = (k, l) => {
  const n2 = 2 * (2 * k + l) + 3; // (2k+l+3/2) = n2/2
  return `E = ${n2}/2 ħω`;
};

/*
 * Generic voxel grid — the common shape the renderer consumes, whether the field
 * is an analytic eigenstate (below) or a parsed DFT .cube (cube.js):
 *   { field: Float32Array(nx*ny*nz),   // index ix + nx*(iy + ny*iz)
 *     nx, ny, nz, ox, oy, oz, dx, dy, dz, maxAbs, min }
 * coord(ix,iy,iz) = (ox+ix*dx, oy+iy*dy, oz+iz*dz).
 */

/** Sample ψ_{k,l,m} onto a cubic grid → generic grid descriptor. */
export function hoGrid(k, l, m, res = 40) {
  const extent = Math.sqrt(2 * (2 * k + l) + 3) + 2.6; // ~classical turning radius + margin
  const step = (2 * extent) / (res - 1);
  const field = new Float32Array(res * res * res);
  let maxAbs = 0, min = Infinity, idx = 0;
  for (let iz = 0; iz < res; iz++) {
    const z = -extent + iz * step;
    for (let iy = 0; iy < res; iy++) {
      const y = -extent + iy * step;
      for (let ix = 0; ix < res; ix++) {
        const v = psi(k, l, m, -extent + ix * step, y, z);
        field[idx++] = v;
        if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v);
        if (v < min) min = v;
      }
    }
  }
  return { field, nx: res, ny: res, nz: res, ox: -extent, oy: -extent, oz: -extent,
           dx: step, dy: step, dz: step, maxAbs, min };
}

const gridCenter = (g) => [g.ox + (g.nx - 1) * g.dx / 2, g.oy + (g.ny - 1) * g.dy / 2, g.oz + (g.nz - 1) * g.dz / 2];
/** Half of the largest side — for normalizing display size. */
export const gridExtent = (g) => 0.5 * Math.max((g.nx - 1) * g.dx, (g.ny - 1) * g.dy, (g.nz - 1) * g.dz);

/**
 * Density anisotropy in [0,1] from the field's second-moment tensor — the same
 * fractional-anisotropy measure as the heuristic ellipsoid. `densityWeight`:
 * weight by the field itself (for a non-negative density ρ), else by field²
 * (for a signed wavefunction ψ, whose density is ψ²). Diagonal (axis-aligned)
 * variances; full eigendecomposition is a future refinement for tilted densities.
 */
export function anisotropyFromGrid(g, densityWeight) {
  const { field, nx, ny, nz, ox, oy, oz, dx, dy, dz } = g;
  let sw = 0, sx = 0, sy = 0, sz = 0, sxx = 0, syy = 0, szz = 0, idx = 0;
  for (let iz = 0; iz < nz; iz++) {
    const z = oz + iz * dz;
    for (let iy = 0; iy < ny; iy++) {
      const y = oy + iy * dy;
      for (let ix = 0; ix < nx; ix++) {
        const f = field[idx++];
        const w = densityWeight ? Math.max(f, 0) : f * f;
        if (w === 0) continue;
        const x = ox + ix * dx;
        sw += w; sx += w * x; sy += w * y; sz += w * z;
        sxx += w * x * x; syy += w * y * y; szz += w * z * z;
      }
    }
  }
  if (sw === 0) return 0;
  const vx = sxx / sw - (sx / sw) ** 2, vy = syy / sw - (sy / sw) ** 2, vz = szz / sw - (sz / sw) ** 2;
  const [a, b, c] = [Math.sqrt(Math.max(vx, 0)), Math.sqrt(Math.max(vy, 0)), Math.sqrt(Math.max(vz, 0))]
    .sort((p, q) => q - p);
  const mean = (a + b + c) / 3;
  const num = Math.sqrt((a - mean) ** 2 + (b - mean) ** 2 + (c - mean) ** 2);
  const den = Math.sqrt(a * a + b * b + c * c);
  return den === 0 ? 0 : Math.min(Math.max(Math.sqrt(1.5) * num / den, 0), 1);
}

// ---- marching tetrahedra (robust, small tables; DoubleSide-tolerant) -------
const CORNER = [
  [0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0],
  [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1],
];
const TETS = [
  [0, 5, 1, 6], [0, 1, 2, 6], [0, 2, 3, 6],
  [0, 3, 7, 6], [0, 7, 4, 6], [0, 4, 5, 6],
];

function interp(iso, pa, va, pb, vb) {
  const t = Math.abs(vb - va) < 1e-12 ? 0.5 : (iso - va) / (vb - va);
  return [pa[0] + t * (pb[0] - pa[0]), pa[1] + t * (pb[1] - pa[1]), pa[2] + t * (pb[2] - pa[2])];
}

/**
 * Mesh the level set {field = iso} (inside = field ≥ iso) as a triangle-soup
 * Float32Array of positions. Winding is not guaranteed — render DoubleSide with
 * computed normals.
 */
export function marchGrid(g, iso, sign = 1) {
  const { field, nx, ny, nz, ox, oy, oz, dx, dy, dz } = g;
  const [cx, cy, cz] = gridCenter(g); // emit centered coords for easy display placement
  const at = (ix, iy, iz) => sign * field[ix + nx * (iy + ny * iz)];
  const pos = [];
  const pushT = (a, b, c) => { pos.push(a[0], a[1], a[2], b[0], b[1], b[2], c[0], c[1], c[2]); };
  const P = new Array(8), V = new Array(8);
  for (let iz = 0; iz < nz - 1; iz++) {
    for (let iy = 0; iy < ny - 1; iy++) {
      for (let ix = 0; ix < nx - 1; ix++) {
        for (let c = 0; c < 8; c++) {
          const o = CORNER[c];
          const gx = ix + o[0], gy = iy + o[1], gz = iz + o[2];
          P[c] = [ox + gx * dx - cx, oy + gy * dy - cy, oz + gz * dz - cz];
          V[c] = at(gx, gy, gz);
        }
        for (let t = 0; t < 6; t++) {
          const tet = TETS[t];
          const p = [P[tet[0]], P[tet[1]], P[tet[2]], P[tet[3]]];
          const v = [V[tet[0]], V[tet[1]], V[tet[2]], V[tet[3]]];
          const inside = [v[0] >= iso, v[1] >= iso, v[2] >= iso, v[3] >= iso];
          const cnt = inside[0] + inside[1] + inside[2] + inside[3];
          if (cnt === 0 || cnt === 4) continue;
          if (cnt === 1 || cnt === 3) {
            const lone = cnt === 1;
            const s = inside.indexOf(lone);
            const o0 = [0, 1, 2, 3].filter((i) => i !== s);
            pushT(interp(iso, p[s], v[s], p[o0[0]], v[o0[0]]),
                  interp(iso, p[s], v[s], p[o0[1]], v[o0[1]]),
                  interp(iso, p[s], v[s], p[o0[2]], v[o0[2]]));
          } else { // cnt === 2 -> quad (2 triangles)
            const ins = [0, 1, 2, 3].filter((i) => inside[i]);
            const outs = [0, 1, 2, 3].filter((i) => !inside[i]);
            const e00 = interp(iso, p[ins[0]], v[ins[0]], p[outs[0]], v[outs[0]]);
            const e01 = interp(iso, p[ins[0]], v[ins[0]], p[outs[1]], v[outs[1]]);
            const e11 = interp(iso, p[ins[1]], v[ins[1]], p[outs[1]], v[outs[1]]);
            const e10 = interp(iso, p[ins[1]], v[ins[1]], p[outs[0]], v[outs[0]]);
            pushT(e00, e01, e11);
            pushT(e00, e11, e10);
          }
        }
      }
    }
  }
  return new Float32Array(pos);
}

/**
 * Isosurface any grid (analytic eigenstate OR a DFT .cube). Auto-detects a
 * signed field (a wavefunction, with +/- lobes) vs a non-negative density.
 * Returns { positive, negative, extent, anisotropy, signed }. Positions are
 * centered at the grid centroid.
 */
export function buildFromGrid(g, isoFrac = 0.26) {
  const signed = g.min < -0.02 * g.maxAbs;
  const iso = isoFrac * g.maxAbs;
  return {
    positive: marchGrid(g, iso, 1),                          // {f ≥ +iso}
    negative: signed ? marchGrid(g, iso, -1) : new Float32Array(0), // {f ≤ −iso}
    extent: gridExtent(g),
    anisotropy: anisotropyFromGrid(g, !signed),              // density-weight if unsigned
    signed,
  };
}

/** Convenience: analytic harmonic-oscillator eigenstate |k,l,m>. */
export function buildEigenstate(k, l, m, res = 40, isoFrac = 0.26) {
  return buildFromGrid(hoGrid(k, l, m, res), isoFrac);
}
