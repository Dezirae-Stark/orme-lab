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
   level. For ambient operation the effective pairing scale must give
   `k_B T_c ≳ Δ` at `T ≈ 300 K` → `Δ` on the order of tens of meV *and* a coupling
   strong enough to sustain it without destroying the lattice.
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
| **Meissner flux expulsion** | SQUID magnetometry (ZFC/FC), susceptibility → −1 (SI) | The phase is genuinely superconducting | No diamagnetic screening despite "zero R" ⇒ artifact/short |
| **Specific-heat jump** at `T_c` | calorimetry (`ΔC/C ≈ 1.43` in BCS) | A true thermodynamic phase transition | No anomaly ⇒ no bulk transition |
| **Critical field `H_c`/`H_c2`** | transport/magnetization vs field | Field destroys SC as expected | No field dependence ⇒ not SC |
| **Isotope effect** (if phonon-mediated) | `T_c` vs isotopic mass | Phonon pairing mechanism | Absent ⇒ non-phononic or artifact |
| **Magnetic susceptibility** (normal state) | SQUID/VSM | High-spin PGM moment consistent with H1/H2 | No moment ⇒ high-spin claim fails |

The model's `predict_observables` routes each candidate to the experiment that
would matter most for it (`resistance_regime` = `candidate-sc` means "go measure
the Meissner effect").

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

---

## Summary decision rule

A candidate is credited as a *serious* superconductivity lead only if it shows
**all** of: zero DC resistance **and** bulk Meissner screening **and** a
specific-heat anomaly at `T_c` **and** the expected `H_c` field dependence — and
survives ruling out every alternative in §6. Anything less is a lead worth more
computation and measurement, not a confirmed result.
