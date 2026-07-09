// web/vibration.js
/*
 * vibration.js -- THREE-free data + math for the 3D vibrational-mode viewer.
 *
 * Renders the two hypotheses the isotope control decides between: a carboxylate
 * C-O group (H_contaminant) and a metal-metal dimer (H_intrinsic). The isotope
 * math here is a DIRECT MIRROR of src/orme_lab/control_experiment.py and is
 * parity-locked by tests/test_vibration_parity.py -- ¹³C/¹⁸O shift a C-O bond,
 * a metal-metal bond (no C/O) is unmoved.
 *
 * Honest scope: the per-atom mode displacement vectors below are SCHEMATIC
 * (in-phase vs out-of-phase illustration), not a normal-coordinate analysis --
 * like eigenstate.js's model potential, this visualizes a result, it does not
 * assert new physics. app.js builds the THREE meshes; this file stays THREE-free.
 */

// Dominant-isotope masses (amu), CODATA -- mirror of control_experiment._ISO.
export const ISO = { C: 12.0, O: 15.994915, N: 14.003074, Rh: 102.905, Ir: 192.217 };

// Isotope label -> [element substituted, substituted mass]; "12C" is the no-substitution
// baseline. Mirror of control_experiment._LABEL (plus the "12C" identity option).
export const LABEL = {
  "12C": null,
  "13C": ["C", 13.003355],
  "18O": ["O", 17.99916],
  "15N": ["N", 15.000109],
};

// Species geometry + schematic normal-mode displacement vectors (one [dx,dy,dz] per atom).
export const SPECIES = {
  carboxylate: {
    label: "carboxylate COO⁻",
    bond_atoms: ["C", "O"],
    atoms: [
      { el: "C", pos: [0, 0, 0] },
      { el: "O", pos: [-1.1, 0.75, 0] },
      { el: "O", pos: [1.1, 0.75, 0] },
    ],
    bonds: [[0, 1], [0, 2]],
    modes: {
      asym: { label: "νasym (out-of-phase)", nu: 1490.99, disp: [[0, 0, 0], [-1, 0, 0], [1, 0, 0]] },
      sym: { label: "νsym (in-phase)", nu: 1429.53, disp: [[0, -0.6, 0], [0.5, 0.5, 0], [-0.5, 0.5, 0]] },
    },
  },
  metal_dimer: {
    label: "metal–metal dimer",
    bond_atoms: ["M", "M"],   // "M" placeholder; app.js substitutes the chosen metal symbol
    atoms: [
      { el: "M", pos: [-1.3, 0, 0] },
      { el: "M", pos: [1.3, 0, 0] },
    ],
    bonds: [[0, 1]],
    modes: { stretch: { label: "ν(M–M)", nu: 275, disp: [[-1, 0, 0], [1, 0, 0]] } },
  },
};

const reduced = (a, b) => (a * b) / (a + b);

/**
 * Frequency ratio ν'/ν = sqrt(μ_old / μ_new) for a diatomic `bond` (pair of element
 * symbols) under isotope `labelKey`. Returns 1.0 (no shift) when the label is the "12C"
 * baseline OR the labelled element is not in the bond -- so a metal–metal bond, or a ¹⁵N
 * label on a C–O bond, is unmoved. Mirror of control_experiment._shift_for_bond's ratio.
 */
export function freqRatio(bond, labelKey) {
  const spec = LABEL[labelKey];
  if (!spec) return 1.0;
  const [elem, isoMass] = spec;
  if (!bond.includes(elem)) return 1.0;
  const massOf = (s) => (s in ISO ? ISO[s] : ISO.Rh); // "M" or unknown -> a metal mass (no C/O to label)
  const m0 = [massOf(bond[0]), massOf(bond[1])];
  const m1 = m0.slice();
  for (let i = 0; i < bond.length; i++) {
    if (bond[i] === elem) { m1[i] = isoMass; break; }
  }
  const muOld = reduced(m0[0], m0[1]);
  const muNew = reduced(m1[0], m1[1]);
  return Math.sqrt(muOld / muNew);
}

/** Isotopic red-shift (cm⁻¹) of a line at `nu` for `bond` under `labelKey` (≤0). */
export function shiftCm(nu, bond, labelKey) {
  return nu * (freqRatio(bond, labelKey) - 1.0);
}
