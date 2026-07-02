/*
 * cube.js -- Gaussian .cube parser → the generic voxel grid the isosurface
 * renderer consumes (same shape as eigenstate.js's hoGrid). This is the DFT-cube
 * path: run a real calculation offline (GPAW / PySCF / ORCA via the Python
 * backends), export a .cube of the charge density (ρ) or an orbital (ψ), and load
 * it here to render with the SAME marching-tetrahedra + anisotropy pipeline.
 *
 * A density cube (ρ ≥ 0) renders as one translucent lobe; an orbital cube (signed
 * ψ) renders as light/deep-teal phase lobes. Anisotropy is scale-invariant, so
 * Bohr-vs-Angstrom units don't matter. Orthogonal voxel axes are assumed (the
 * overwhelmingly common case); non-orthogonal axes fall back to the diagonal.
 */

/** Parse Gaussian cube text → { field, nx,ny,nz, ox,oy,oz, dx,dy,dz, maxAbs, min, title, natoms }. */
export function parseCube(text) {
  const lines = text.split(/\r?\n/);
  if (lines.length < 6) throw new Error("not a .cube file (too short)");

  const title = `${(lines[0] || "").trim()} ${(lines[1] || "").trim()}`.trim();
  const h = lines[2].trim().split(/\s+/).map(Number);
  let natoms = h[0];
  const ox = h[1], oy = h[2], oz = h[3];
  const orbital = natoms < 0;          // negative natoms → orbital cube (extra index line)
  natoms = Math.abs(natoms);

  const rx = lines[3].trim().split(/\s+/).map(Number);
  const ry = lines[4].trim().split(/\s+/).map(Number);
  const rz = lines[5].trim().split(/\s+/).map(Number);
  const nx = Math.abs(rx[0]), ny = Math.abs(ry[0]), nz = Math.abs(rz[0]);
  const dx = rx[1], dy = ry[2], dz = rz[3];   // orthogonal-axes assumption
  if (!(nx > 0 && ny > 0 && nz > 0)) throw new Error("invalid cube voxel counts");

  let start = 6 + natoms;
  if (orbital) start += 1;               // skip the "NmO m1 m2 …" orbital-index line

  const total = nx * ny * nz;
  const nums = [];
  for (let i = start; i < lines.length && nums.length < total * 8; i++) {
    const s = lines[i].trim();
    if (!s) continue;
    for (const t of s.split(/\s+/)) {
      const v = parseFloat(t);
      if (!Number.isNaN(v)) nums.push(v);
    }
  }
  if (nums.length < total) throw new Error(`cube has ${nums.length} values, expected ≥ ${total}`);

  // Orbital cubes may store M components per point; take the first component.
  const M = Math.max(1, Math.round(nums.length / total));
  const field = new Float32Array(total);
  let p = 0, maxAbs = 0, min = Infinity;
  // cube data order: x outer, y middle, z inner (z fastest)
  for (let ix = 0; ix < nx; ix++)
    for (let iy = 0; iy < ny; iy++)
      for (let iz = 0; iz < nz; iz++) {
        const v = nums[p * M]; p++;
        field[ix + nx * (iy + ny * iz)] = v;
        if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v);
        if (v < min) min = v;
      }

  return { field, nx, ny, nz, ox, oy, oz, dx, dy, dz, maxAbs, min, title, natoms };
}
