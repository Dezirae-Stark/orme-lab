# Hudson Claim Ledger — Design Spec

**Date:** 2026-07-11
**Status:** approved for planning
**Depends on:** `identity.py` (G_identity), `structure.py` (StructuralDistribution), `hudson_optical.py` + `branch_verdict.py` (Branch B), `mechanisms.py`, `meissner_field.py`, `validator.py`, `evidence.py`. All merged to master (`fd15904`).

## 1. Purpose and framing

The Hudson Claim Ledger is the lab's structured, falsify-first application of the adversarial-validator pattern to David Hudson's eight ORME claims. Its objective is **not** to validate Hudson. It is to *determine whether a reproducible material state exists that satisfies Hudson's stated properties* — attacking the ordinary explanation of each claim first, and only advancing effects that survive.

The ledger is a **reporting layer above the per-candidate pipeline**, not a new gate inside the superconductivity AND-gate or its closure oracle. It is named `hudson_ledger` to stay distinct from the existing `lab_loop/ledger.py` (the append-only *experiment* ledger — a different object).

Two invariants govern the whole design:
- **Default-block extraordinary claims.** Every transport, magnetism, and replication sub-gate is *unestablished* at pure-simulation level. The simulation emits the decisive experiment (a Level-3 laboratory prediction); a researcher loading measured evidence is what climbs the gate. The ledger can **never** self-assert `G_hudson_mechanism` from simulation alone.
- **No Frankenstein validation.** The integrated Hudson state may be credited only when *one materially continuous lineage* satisfies the combined claims — never by assembling one claim each from unrelated specimens.

The ledger **never emits "HUDSON CLAIM VALIDATED."** The strongest terminal verdict is `independent-replication-achieved`, reachable only with real external replication metadata, and even that clamps to the evidence ceiling appropriate to its source.

## 2. The eight claims (HC-01 … HC-08)

HC-namespaced to avoid collision with the lab's existing `H-04`/`H-05` (the isolated-monomer premise hypotheses in `meissner_field.py`).

| ID | Hudson claim | Required observation | Strongest mundane alternative | Computable source |
|----|--------------|----------------------|-------------------------------|-------------------|
| HC-01 | Stable nonmetallic PGM form | elemental PGM, zero oxidation, **not** the metallic lattice | oxide / hydroxide / salt / ligand complex | `identity` witness (composition + phase + oxidation) |
| HC-02 | Atomically dispersed ("monoatomic") | predominantly isolated atoms (EXAFS/STEM/PDF) | undetected clusters / nanoparticles | `structure` (`f1`, `size_distribution`, `nn_distances`) + policy |
| HC-03 | Orbital rearrangement | reproducible electronic structure distinct from known compounds | ordinary crystal-field / oxidation-state change | **none** → decisive-experiment design (XPS/XAS/EELS) |
| HC-04 | 1400–1600 cm⁻¹ doublet | reproducible, isotope- & atmosphere-sensitive assignment | water / carbonate / nitrate / ligand / instrument bkg | `ir_contaminant` + `control_experiment` (built) |
| HC-05 | Conversion back to metal | mass-balanced recovery of original PGM | contamination / reduction of an ordinary salt | **none** → decisive-experiment design |
| HC-06 | Flux exclusion > 200 K | geometry-corrected diamagnetic shielding | magnetic artifact / ordinary diamagnetism | `meissner_field` |
| HC-07 | Superconductivity | R→0 + magnetic + thermodynamic evidence | ionic conduction / percolation / contact artifact | SC gate + `mechanisms` + Branch B |
| HC-08 | Anomalous apparent mass | replication on independent balances, controlled gas flow | buoyancy / convection / magnetic force / balance coupling | **none** → decisive-experiment design |

Claims with a computable source roll up per-candidate evidence into a verdict. HC-03/05/08 have no computable surface; the ledger emits a `validator`-style decisive-experiment design (naming the mundane alternative and the discriminating measurement) at Level 3, and their claim status stays at `candidate`/`lead` until real evidence is loaded.

## 3. Per-claim evidentiary status ladder

A "lead" is *promising evidence*, not support. Each claim, per candidate, carries a status:

```
candidate → lead → anomalous → provisionally_supported → supported → independently_replicated
```

- **candidate** — the material is a formal candidate for the claim; nothing shown.
- **lead** — a simulation signal consistent with the claim (e.g. `credited_sc_lead` for HC-07, a plausible IR match for HC-04). **Simulation caps here.**
- **anomalous** — a measured result inconsistent with the mundane alternative but not yet clearing the full gate.
- **provisionally_supported** — one measured result clears the preregistered claim gate; not yet replicated.
- **supported** — the claim gate is cleared with blinded controls correctly classified.
- **independently_replicated** — cleared across ≥3 batches / >1 lab.

`credited_sc_lead` maps to **lead**, never `supported`. HC-07 is `supported` only when a candidate clears the preregistered HC-07 evidence gate (measured R→0 + magnetic + thermodynamic, mundane alternatives excluded) — not from a simulation lead.

Status maps to the evidence ladder: `candidate/lead` ≤ L2 (SIMULATION_CANDIDATE); decisive designs = L3 (LABORATORY_PREDICTION); `anomalous/provisionally_supported/supported` carry L4 (INITIAL_OBSERVATION) **only** as measured inputs; `independently_replicated` = L5 (INDEPENDENT_REPLICATION), external metadata only. The simulation never *produces* an evidence_level above L2.

## 4. Gate decomposition

Five top-level named gates (with named sub-gates below). Conventional superconductivity and the Hudson mechanism are **separate reportable results** — a candidate may clear one without the other.

```
G_identity_established           = composition_known ∧ phase_known ∧ structure_known
G_hudson_material_state          = HC-01_nonmetallic ∧ HC-02_atomically_dispersed
G_conventional_superconductivity = zero_resistance ∧ flux_exclusion ∧ critical_behavior ∧ artifact_exclusion
G_candidate_optical              = coherent_mode_gate ∧ material_coupling_gate ∧ energy_transport_gate
G_hudson_mechanism               = G_hudson_material_state ∧ G_candidate_optical
                                   ∧ optical_magnetic_causality_gate ∧ replication_gate
```

### 4.1 Identity split (the load-bearing correction)

`identity.py` bakes in `G_phase = (phase == "metallic")` — correct for Branch-A SC-lead crediting (you must *be the metal*), but backwards for Hudson, whose HC-01 wants a **nonmetallic elemental** state (composition = the PGM, oxidation ≈ 0, but *not* the metallic lattice, and *not* an oxide/salt). Therefore:

- **`identity.py` is left untouched** — it continues to gate Branch-A crediting.
- The ledger computes its identity gates **fresh** from the same `IdentityWitness` + `StructuralDistribution`:
  - `G_identity_established` = every descriptor is *known* (composition, phase, morphology/structure, oxidation present within stated uncertainty) — **phase-agnostic**. "We know what it physically is," whether metal, compound, or novel phase.
  - `G_hudson_material_state` = `HC-01 ∧ HC-02` (Hudson-conformant).
- A new phase value `nonmetallic-elemental` distinguishes Hudson's claimed state from both `metallic` and the compound phases (`oxide`/`salt`/…). HC-01 clears when: composition = target PGM ∧ `|oxidation| ≤ tol` ∧ phase = `nonmetallic-elemental`. The compound phases are the ruled-out mundane alternative.

Hudson-identity has four outcomes, distinct from generic identity:
- **established** — characterization is complete (G_identity_established true), regardless of what it found.
- **hudson-satisfied** — established ∧ nonmetallic ∧ atomically dispersed.
- **hudson-failed** — identified, but metallic / clustered / compound → incompatible with the claimed state.
- **hudson-unresolved** — characterization cannot distinguish isolated atoms from clusters/other phases.

### 4.2 HC-02 as measurement + policy (not Boolean)

HC-02 is a **policy over `structure.py` measurements**, which already expose the exact quantities:
- `StructuralDistribution.f1()` — fraction of isolated PGM sites (`f_single`).
- `.size_distribution()` — P(n), cluster-size → fraction.
- `.nn_distances()` — R_PGM–PGM per population (the coordination signal).

HC-02 clears when **all** hold (thresholds configurable — no method proves literal 100 % monatomicity):
```
f_single ≥ hudson_hc02_min_isolated_fraction
∧ clustered_fraction_upper_bound ≤ hudson_hc02_max_clustered_fraction
∧ no PGM–PGM coordination signal exceeds hudson_hc02_pgm_pgm_tolerance
```
`clustered_fraction_upper_bound` uses the distribution's clustered mass plus a configurable uncertainty margin (the "upper confidence bound" — a surrogate at sim level, a real CI when measured data is loaded).

### 4.3 Either-route, labelled (individual claims)

The conventional and optical branches remain independent (`branch_verdict.py`). "Either route" lives at the *individual claim* level, and the verdict records which:
- **HC-06 (flux exclusion):** satisfied by `meissner_field` diamagnetic shielding (route = `conventional`) **or** Branch-B level-7 ∂M/∂P tracking resonance (route = `optical`).
- **HC-07 (transport):** satisfied by measured R→0 from the SC gate (route = `conventional`) **or** Branch-B level-5 persistent-ring-down transport (route = `optical`).

The *integrated* gates stay distinct rather than OR-merged: `G_conventional_superconductivity` (Branch A) and `G_hudson_mechanism` (Branch B optical composition) are reported side by side.

### 4.4 Branch-B mapping

`G_candidate_optical` and the causality gate map directly onto Branch-B claim levels (`hudson_optical.HudsonClaim`):
- `coherent_mode_gate` = STRONG_COUPLING (L3) ∧ MACRO_COHERENCE (L4)
- `material_coupling_gate` = ELECTRONIC_COUPLING (L6)
- `energy_transport_gate` = LOW_LOSS_TRANSPORT (L5, requires PERSISTENT ring-down)
- `optical_magnetic_causality_gate` = MAGNETISM_COUPLED (L7)

So `G_hudson_mechanism` reduces to **Branch-B HUDSON_PHASE (L8) ∧ G_hudson_material_state ∧ replication_gate** — level 8 already conjoins {L3,L4,L5,L6,L7} with PERSISTENT, and stays a conjunction-only *prediction* (never crediting).

### 4.5 Replication gate

`replication_gate` is a **default-blocked metadata gate** — a `ReplicationEvidence` record the researcher fills:
```
n_batches ≥ 3 ∧ n_labs > 1 ∧ preregistered_thresholds ∧ raw_data_retained
∧ blinded_controls_correctly_classified
```
No metadata → `False` (unestablished). The simulation never asserts replication.

## 5. Two roll-ups

### 5.1 Claim-level (best-of, existential)

```
claim_status(HC_j) = max over candidates c of candidate_claim_status(c, HC_j)
```
Answers: *"Has any tested material supported this individual claim?"* Best-of is valid here — it is discovery/portfolio reporting, and it is clearly labelled as such (which candidate, at what status).

### 5.2 Integrated-material (weakest-link within one lineage, then best across)

```
S_integrated = max over lineages m of ( min over j ∈ CORE of S(m, HC_j) )
```
where `CORE = {HC-01, HC-02, HC-04, HC-06, HC-07, G_candidate_optical, replication_gate}`. The inner **min** enforces the weakest-link principle within one lineage; the outer **max** selects the strongest *complete* lineage. This is the **only** roll-up permitted to speak to the integrated Hudson state.

**Two distinct integrated outputs, both same-lineage, reported separately** (do not conflate):
- `integrated_status` — the **phenomenological** integrated state: the weakest-link `S_integrated` over `CORE`. Answers *"does one lineage exhibit all the claimed properties?"*
- `g_hudson_mechanism` (§4) — the narrower **mechanistic** claim: `G_hudson_material_state ∧ G_candidate_optical ∧ optical_magnetic_causality_gate ∧ replication_gate`, evaluated on the *same* lineage. Answers *"is that state produced by the optical-coherence mechanism Hudson proposed?"* It adds the causal optical-magnetic attribution that the phenomenological conjunction does not require.

The phenomenological state can be supported (a lineage shows the marker, flux exclusion, and transport) without the mechanism gate firing (the optical-magnetic causality is not established) — and the ledger says exactly that.

Explicitly forbidden: `min_j ( max_c S(c, HC_j) )` — that permits a different candidate to satisfy each claim (the Frankenstein bug). The ledger must not compute it for either integrated output.

## 6. Lineage model (new infrastructure)

No provenance/lineage module exists today; this is net-new. A `MaterialLineage` record carries:
```
material_family_id            # the recipe / precursor family
preparation_batch_id          # one homogeneous preparation
aliquot_id                    # one physical portion tested
processing_history            # ordered treatments (anneal, hydrate, irradiate, field)
characterization_fingerprint  # structural/chemical fingerprint for matching
```

Three integration levels, in increasing strength:
- **same-specimen** — the exact physical aliquot receives transport/optical/magnetic tests. Strongest correlation; may be impossible for destructive/incompatible tests.
- **same-batch** — aliquots from one homogeneous batch. **Minimum acceptable for initial integrated evidence.**
- **same-lineage** — independent batches, same recipe, matching fingerprints. Required for replication/qualification.

A claim observed after annealing / hydration / irradiation / field treatment attaches to the **resulting** material state (a new `processing_history` entry), not automatically to the original precursor.

At pure-simulation level each computational candidate `(element, geometry, spin)` is its own singleton lineage. Real lab evidence carries explicit IDs, and the integrated roll-up groups aliquots by lineage before applying the weakest-link min.

## 7. Module structure and data model

New: `src/orme_lab/hudson_ledger.py`, `src/orme_lab/lineage.py` (the provenance type), `docs/hudson_claim_ledger.md`, `tests/test_hudson_ledger.py`, `tests/test_lineage.py`. New `ModelThresholds` fields for the HC-02 policy and the replication minima.

Core types:
- `HudsonClaimId(Enum)` — HC_01 … HC_08.
- `ClaimStatus(IntEnum)` — CANDIDATE < LEAD < ANOMALOUS < PROVISIONALLY_SUPPORTED < SUPPORTED < INDEPENDENTLY_REPLICATED (ordered so `max`/`min` roll-ups are numeric).
- `Route(Enum)` — CONVENTIONAL | OPTICAL | NONE.
- `ClaimRecord(frozen)` — `id, claim_text, required_observation, mundane_alternative, status, evidence_level, route, computable: bool, decisive_experiment: ValidationSuite | None, note`.
- `MaterialLineage(frozen)` — the fields in §6, plus `integration_level`.
- `ReplicationEvidence(frozen)` — the fields in §4.5; `None` ⇒ unestablished.
- `HudsonGateResult(frozen)` — the gates of §4 (each a bool + route/label + evidence_level), `g_hudson_mechanism: bool`, `g_conventional_superconductivity: bool`, `interim_verdict: str`.
- `HudsonLedger(frozen)` — `claims: tuple[ClaimRecord, ...]` (fixed HC order), `gate: HudsonGateResult`, `integrated_status: ClaimStatus` (phenomenological, §5.2), `integrated_lineage_id: str | None`, `explain()`.

Key functions (all pure, deterministic, fixed iteration order):
- Per-claim assessors `_assess_hc01(...) … _assess_hc08(...)` — each pulls from its source (§2), applies the falsify-first policy, returns a `ClaimRecord`. Procedural claims return a `decisive_experiment` design via `validator`.
- Sub-gate functions `g_identity_established(witness)`, `g_hudson_material_state(witness, distribution, th)`, `g_conventional_superconductivity(record, measured=None)`, `g_candidate_optical(hudson_optical_result)`, `optical_magnetic_causality(hudson_optical_result)`, `replication_gate(rep_evidence, th)`.
- `evaluate_hudson_ledger(candidates, *, lineages=None, replication=None, thresholds) -> HudsonLedger` — the two-layer roll-up: per-claim best-of for the portfolio, weakest-link-within-lineage for the integrated result.

Inputs consumed (read-only, no mutation): `CandidateRecord` (identity_verdict, credited_sc_lead, surviving_mechanisms, `hudson_*` Branch-B fields, meissner fields, IR-screen outputs), `IdentityWitness`, `StructuralDistribution`, `HudsonOpticalResult`/`BranchVerdict`.

## 8. Evidence discipline and determinism

- Simulation-produced `evidence_level` ≤ LAB_CEILING (2). Decisive designs = PREDICTION_CEILING (3). L4 appears only as measured `evidence_level_if_confirmed`; L5 only from external replication metadata.
- No `time.time()`, no unseeded RNG, no order-dependent iteration. Claims emit in fixed HC order; lineage grouping is sorted by id.
- No web surface, no network egress, loopback only. Python/stdlib only.
- No fabricated citations; the procedural decisive-experiment designs reuse the `validator` vocabulary and cite nothing new.

## 9. Testing strategy

- Each computable claim wires to its source and reflects it (HC-01 rules out oxide/salt; HC-02 policy clears/blocks on `f1`/clustered-UB/PGM–PGM; HC-04 folds the IR control; HC-06 Meissner; HC-07 SC+Branch B).
- **Identity split:** a metallic specimen is `G_identity_established=True` but `G_hudson_material_state=False` (hudson-failed); a nonmetallic-elemental dispersed specimen is both; an ambiguous morphology is hudson-unresolved.
- **credited_sc_lead ⇒ LEAD, not SUPPORTED:** a candidate with `credited_sc_lead` gives HC-07 portfolio status LEAD; HC-07 `supported` requires the measured gate.
- **Either-route labelling:** Meissner satisfies HC-06 route=conventional; Branch-B ∂M/∂P satisfies it route=optical; the verdict names which.
- **Default-blocks:** no measured transport/magnetism/replication ⇒ those gates `False` ⇒ `G_hudson_mechanism` and `G_conventional_superconductivity` cannot fire; the ledger emits designs instead.
- **Anti-Frankenstein (the keystone test):** a portfolio where candidate A clears HC-01, B clears HC-02, C the optical mode, D the magnetism, E the transport — best-of shows every *claim* supported, but the **integrated** result is *not* supported because no single lineage clears the core conjunction. Assert `integrated_status < SUPPORTED` while `claim_status(each) ≥ supported`.
- **Never "VALIDATED":** assert the verdict string is never "HUDSON CLAIM VALIDATED" under any input, including a fully-satisfied single lineage (which reaches at most `independent-replication-achieved`).
- Determinism: identical inputs → identical ledger (frozen equality).

## 10. Out of scope (this build)

- Web/3D visualization of the ledger.
- Claim-hierarchy levels 9–10 (independent reproduction campaign, practical transduction) beyond the metadata gate.
- Modifying `identity.py`, the SC gate, or Branch B — the ledger is strictly a consuming layer.
- Automating real replication (the `ReplicationEvidence` record is filled by a researcher, not synthesized).
