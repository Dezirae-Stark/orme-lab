# Validation Tests — What Would Confirm or Kill the Claim

This is the falsification playbook. For the ORME/PGM ambient-superconductivity
claim to be taken seriously, it must survive specific, discriminating experiments
— not just produce a suggestive number. This document lists those tests, the
observable each targets, and what result *kills* the claim.

The project's stance: we take the premise as a working assumption to reverse-
engineer *how* it could be true, but the validation layer must retain real
discriminating power. A "validation" that cannot fail is not validation.

---

## 1. What would need to be mathematically/physically true for ambient superconductivity

A superconductor is not "a material with zero resistance." It is a
**macroscopic quantum phase** with, at minimum:

1. **A pairing mechanism** binding carriers into a condensate (Cooper pairs in
   BCS; some other boson in exotic scenarios). An energy gap Δ opens at the Fermi
   level and **closes at `T_c`**. For a weak-coupling *isotropic BCS reference*,
   `2Δ(0) ≈ 3.53 k_B T_c`, i.e. `Δ(0) ≈ 1.76 k_B T_c`; a 300 K transition
   (`k_B T_c ≈ 25.85 meV`) implies a *zero-temperature* gap `Δ(0) ≈ 45.5 meV`. This
   is a **mechanism-dependent reference scale, not a universal requirement** —
   strong-coupling, anisotropic, multiband, and unconventional phases give other
   `2Δ/k_B T_c` ratios — and because Δ closes at `T_c`, the gap is *not* tens of meV
   at 300 K itself. The pairing must also be strong enough to sustain the phase
   without destroying the lattice.
2. **Macroscopic phase coherence** — a single complex order parameter
   `ψ = |ψ| e^{iφ}` with `φ` rigid across the sample. This is what an isolated
   atom cannot provide (see §4).
3. **Thermodynamic stability** of that phase at ambient `T` and `P` — the
   condensation energy must exceed thermal fluctuations `~k_B T` over the coherence
   volume. This is the brutal constraint at 300 K: the coherence volume is tiny
   and `k_B T` is large.
4. **Electrodynamic consequences** — the London equations must hold, giving a
   finite penetration depth `λ_L` and flux expulsion (the Meissner effect).

Encoded in the model: gap/pairing → `carrier_coherence_proxy`; coherence →
`inter_unit_coupling_score`; stability → `structural_stability_proxy`;
electrodynamics → `meissner_screening_proxy`.

---

## 2. Experimental observables that validate or falsify

| Observable | Instrument | Confirms | Falsifies |
|-----------|-----------|----------|-----------|
| **Zero DC resistance** | 4-probe transport | Necessary (not sufficient) | Finite `R` at all `T` |
| **Meissner flux expulsion** | SQUID (ZFC/FC); **demagnetization-corrected** `χ_int → −1` (SI), not raw `χ` | The phase is genuinely superconducting | No diamagnetic screening despite "zero R" ⇒ artifact/short |
| **Specific-heat jump** at `T_c` | calorimetry (`ΔC/γT_c ≈ 1.43` in *weak-coupling* BCS) | A true thermodynamic phase transition | No resolvable anomaly ⇒ *upper bound on bulk SC fraction* (does not alone exclude filamentary/granular/broadened/unconventional SC) |
| **Critical field `H_c`/`H_c2`** | transport/magnetization vs field | Field destroys SC as expected | No field dependence ⇒ not SC |
| **Isotope effect** (if phonon-mediated) | `T_c` vs isotopic mass | Phonon pairing mechanism | Absent ⇒ non-phononic or artifact |
| **Magnetic susceptibility** (normal state) | SQUID/VSM | High-spin PGM moment consistent with H1/H2 | No moment ⇒ high-spin claim fails |

The model's `predict_observables` routes each candidate to the experiment that
would matter most for it (`resistance_regime` = `candidate-sc` means "go measure
the Meissner effect").

### Gate-calibration notes (do not universalize the BCS benchmarks)

- **Meissner / susceptibility — demagnetization is not optional.** A raw `χ → −1`
  target is directionally right but geometry-dependent. Report the
  demagnetization-corrected intrinsic susceptibility
  `χ_int = χ_meas / (1 − N χ_meas)` (subject to the unit/sign convention in use),
  because apparent shielding fractions depend on demagnetization factor `N`, sample
  shape, packing density, porosity, grain orientation, SC volume fraction, field
  amplitude, and ZFC-vs-FC — and can even exceed 100 % when `N` is underestimated.
  The validation output should carry: raw magnetic moment; mass- and
  volume-normalized susceptibility; assumed sample density; `N`; corrected shielding
  fraction; ZFC/FC divergence; and field-amplitude dependence.
- **Specific-heat jump — `ΔC/γT_c ≈ 1.43` is the weak-coupling isotropic BCS value,
  not a universal requirement.** Strong coupling, anisotropic/nodal gaps, multiband
  structure, inhomogeneous volume fractions, and broadened transitions all shift it
  (reported values run from well below to ~2.3 and beyond). A missing calorimetric
  anomaly therefore bounds the *bulk* SC fraction and argues against a homogeneous
  bulk transition — it does not by itself exclude a small-volume, filamentary,
  granular, strongly broadened, or unconventional component. The calorimetry gate
  stays important; it is not universalized past its actual discriminating power.

---

## 3. Why zero resistance alone is insufficient — the Meissner requirement

Zero measured resistance can be produced by mundane things that are **not**
superconductivity:

- a metallic short or percolating conductive path,
- contact/measurement artifacts (thermal EMF, current-path issues),
- a filamentary/granular path that carries the test current but is not a bulk
  phase.

What separates a real superconductor is that it **actively expels magnetic flux**
(the Meissner effect) — a thermodynamic equilibrium property, not just a
consequence of `R = 0`. A perfect conductor with `R = 0` would merely *trap*
whatever flux was present when it was cooled; a superconductor *pushes flux out*
regardless of cooling history. That is why the model treats
`meissner_screening_proxy` as a **first-class, independent gate**: a candidate
with apparent zero-R but zero screening is flagged in `ObservableSet.notes` as a
probable artifact. This is the single most common failure mode of extraordinary
superconductivity claims (LK-99 being a recent public example: initial zero-R /
levitation reports were not backed by bulk diamagnetic screening).

---

## 4. Why isolated monatomic states create a coupling problem

The ORME claim, taken literally, describes **electronically isolated, monatomic**
species. But superconductivity is intrinsically **collective**: the order
parameter's phase `φ` must be coherent across a macroscopic region. An isolated
atom has:

- no neighbour to share a pair wavefunction with,
- no band structure (no `k`-space — you need a lattice for that),
- no channel for phase to propagate.

So a *literally* monatomic isolated ORME cannot be a bulk superconductor. The
model encodes this as a hard consequence: a monomer geometry has
`nearest_neighbor_distance = ∞` → `inter_unit_coupling_score = 0` →
`is_electronically_isolated = True` → the SC plausibility AND-gate returns 0.
**If a monomer ever scored as a viable SC candidate, that would be a model bug,
not a discovery.** The reverse-engineering task is therefore precisely: *what
supplies the coupling channel?* (see §6).

---

## 5. How high-spin deformation could be translated into modern physics

The vague "high-spin / rice-bean deformation" language maps onto real,
well-posed condensed-matter concepts:

- **High-spin state** → Hund's-rule-maximized local moment; large unpaired-`d`
  count; treatable with unrestricted/broken-symmetry DFT or a Hubbard-`U` model.
- **"Rice-bean" density anisotropy** → a prolate charge/spin-density distribution;
  quantifiable as the anisotropy of the second-moment tensor of the density, or as
  orbital polarization (`d_{z²}` vs `d_{x²−y²}` occupancy).
- **Possible route to pairing** → strong local moments + coupling can give
  *magnetically mediated* or *spin-fluctuation* pairing (as in heavy-fermion and
  some unconventional superconductors). This is a legitimate, if demanding,
  mechanism — and notably one where high-spin PGM chemistry could plausibly play a
  role, *if* the coupling channel of §4/§6 exists.

This is the productive translation: it turns an untestable slogan into a set of
DFT-computable quantities and a named candidate mechanism.

---

## 6. Alternative explanations that must be ruled out (H6)

Before crediting "ambient superconductivity in high-spin monatomic PGM," each of
these more-mundane explanations must be excluded by a specific measurement:

| Alternative | Signature that distinguishes it | Discriminating test |
|-------------|--------------------------------|---------------------|
| **Nanocluster / granular metal** | SC lives in grains, weak links between | grain-size dependence; `H_c2` anisotropy |
| **Granular Josephson network** | Broad resistive transition, excess noise, non-BCS `I–V` | microwave response; Shapiro steps under RF |
| **Plasmonic / polaritonic coherence** | Optical-frequency coherence, not DC transport | ultrafast/optical spectroscopy vs DC |
| **Oxide / hydroxide / salt phase** | The "monatomic" powder is actually a compound | XRD, XPS, EDS composition; is it even the metal? |
| **Measurement artifact** | Zero-R without Meissner; irreproducible | independent SQUID; blind replication |
| **Diamagnetic non-SC material** | Screening present but no `T_c`, no `H_c`, no `ΔC` | temperature/field sweep of susceptibility |

The model does not "rule these out" by itself — it **routes** a candidate toward
the experiment that would. Ruling out is an empirical act; the code's job is to
say which experiment is decisive for a given candidate.

### G_identity — phase identity is a hard upstream gate

The "oxide / hydroxide / salt phase" row above is not just one alternative among
many — it is *upstream* of the whole superconductivity interpretation. A specimen
must clear a **phase-identity gate before it may enter the superconductivity branch
at all**:

```
G_identity = G_composition ∧ G_phase ∧ G_morphology ∧ G_oxidation
```

Until there is enough characterization to distinguish among **metallic PGM · oxide ·
hydroxide · chloride/other salt · ligand complex · carbon-supported single atoms ·
nanoparticles · sub-nanometre clusters · mixed/contaminated phases**, a "zero
resistance" or "diamagnetic" reading cannot be attributed to a superconducting phase
of the metal, because it may belong to a different compound entirely. The
characterization package that discharges this gate draws on some combination of:
**XRD or total-scattering/PDF · XPS · ICP-MS/OES · STEM-HAADF · EDS/EELS ·
XANES/EXAFS · Raman/FTIR · TGA**. The charter's "independent, instrumented,
reproducible observation" standard already implies these witnesses; `G_identity`
makes them a *compulsory precondition* rather than a parallel caveat.

*Implementation status:* documented here as a gate; the pipeline does not yet enforce
`G_identity` as code upstream of the superconductivity AND-gate (scoped follow-up).

---

## Summary decision rule

A candidate is credited as a *serious* superconductivity lead only if it shows
**all** of: zero DC resistance **and** bulk Meissner screening **and** a
specific-heat anomaly at `T_c` **and** the expected `H_c` field dependence — and
survives ruling out every alternative in §6. Anything less is a lead worth more
computation and measurement, not a confirmed result.

The standard of proof is an **independent, instrumented, reproducible
observation**: the witness is a calibrated instrument (SQUID, ESR, XRD, Raman,
neutron scattering, calorimetry), and another laboratory with comparable
equipment must reproduce the result under the same conditions. Per the charter's
evidence hierarchy (`CHARTER.md`), the tests above move a candidate from a
Level-3 *laboratory prediction* to Level 4 (single reproducible experiment) and
only reach Level 5–6 on independent replication. Everything this repository
produces is a Level-2/3 artifact and must be labeled as such.
