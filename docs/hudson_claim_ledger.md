# Hudson Claim Ledger

`src/orme_lab/hudson_ledger.py` — a REPORTING layer above the per-candidate pipeline. It is not
a gate inside the SC AND-gate or the closure oracle, and it is a different object from
`lab_loop/ledger.py` (the experiment ledger). See the design spec at
`docs/superpowers/specs/2026-07-11-hudson-claim-ledger-design.md` and the primary source extraction
at `research-wiki/prior-art/hudson-orme-patents-de3920144a1.md` (Hudson patent DE3920144A1) for the
claim language this module operationalizes. No new citations are introduced here.

## Framing: falsify-first, not validate-Hudson

The ledger's objective is to determine whether a reproducible material state exists that
satisfies Hudson's stated properties — attacking the ordinary (mundane) explanation of each claim
first, not assuming the Hudson mechanism and looking for confirming evidence. Every `ClaimRecord`
carries both the `required_observation` needed to support the claim and the `mundane_alternative`
that must be ruled out first (contamination, ordinary diamagnetism, buoyancy artifact, percolation,
etc.). Extraordinary claims (superconductivity, the Hudson mechanism, independent replication) are
default-blocked: they cannot be reached from simulated inputs alone, only from measured evidence
supplied by the researcher. The ledger never self-asserts `g_hudson_mechanism` or
`g_conventional_superconductivity` from simulation, and it never emits the string
`"HUDSON CLAIM VALIDATED"` under any input — `explain()` and `_interim_verdict()` are the only
places that produce a summary sentence, and both are deterministic, closed vocabularies checked by
`tests/test_hudson_ledger.py`.

## The eight claims (HC-01 .. HC-08)

| ID | Claim | Required observation | Mundane alternative | Source |
|---|---|---|---|---|
| HC-01 | Stable nonmetallic PGM form | elemental PGM, zero oxidation, non-metallic phase | oxide / hydroxide / salt / ligand complex | Hudson patent, identity claims |
| HC-02 | Atomically dispersed ("monoatomic") | predominantly isolated atoms (EXAFS/STEM/PDF) | undetected clusters / nanoparticles | Hudson patent, dispersion claims |
| HC-03 | Orbital rearrangement | reproducible electronic structure distinct from known compounds (XPS/XAS/EELS) | ordinary crystal-field / oxidation-state change | Hudson patent |
| HC-04 | 1400-1600 cm⁻¹ IR doublet | reproducible isotope- & atmosphere-sensitive assignment | water / carbonate / nitrate / ligand / instrument background (carboxylate contaminant) | Hudson patent IR-doublet marker |
| HC-05 | Conversion back to metal | mass-balanced recovery of the original PGM | contamination / reduction of an ordinary salt | Hudson patent |
| HC-06 | Flux exclusion > 200 K | geometry-corrected diamagnetic shielding | magnetic artifact / ordinary diamagnetism | Hudson patent, Meissner/Josephson language |
| HC-07 | Superconductivity | R→0 + magnetic + thermodynamic evidence | ionic conduction / percolation / contact artifact | Hudson patent |
| HC-08 | Anomalous apparent mass | replication on independent balances under controlled gas flow | buoyancy / convection / magnetic force / balance coupling | Hudson patent |

`HudsonClaimId` fixes this order (`HC-01` .. `HC-08`); every roll-up iterates claims in this exact
order so results are deterministic and order-independent of dict/set iteration.

## Evidentiary-status ladder

`ClaimStatus` is an ordered `IntEnum` so `max`/`min` roll-ups are well-defined numerically:

```
CANDIDATE (0) < LEAD (1) < ANOMALOUS (2) < PROVISIONALLY_SUPPORTED (3) < SUPPORTED (4) < INDEPENDENTLY_REPLICATED (5)
```

A `LEAD` is promising evidence, not support. Simulation-only inputs cap at `LEAD` for the
transport/superconductivity claim: `candidate.credited_sc_lead` maps to `HC-07 -> LEAD`, never to
`SUPPORTED` — a simulated SC lead is a reason to look harder, not a claim of superconductivity.
`HC-07` reaches `SUPPORTED` only from `MeasuredEvidence` — either the full conventional route
(`g_conventional_superconductivity`: measured zero resistance AND flux exclusion AND critical
behavior AND artifact exclusion) or the optical route (`g_candidate_optical` on a measured
`HudsonOpticalResult`). `INDEPENDENTLY_REPLICATED` is reached only via `ReplicationEvidence`
(external replication metadata: multiple batches, multiple labs, preregistered thresholds, raw
data retained, blinded controls correctly classified) — never from a single lab's measurement.

## The six gates and the identity split

- `g_identity_established(witness)` — **phase-agnostic**. True once every descriptor
  (composition, phase, morphology, oxidation state) is known within stated uncertainty, regardless
  of whether the material turns out to be an ordinary metal, an ordinary compound, or the Hudson
  phase. This answers "do we know what it physically is", and is a distinct gate from
  `identity.py`'s metallic-target gate, which is Branch-A (conventional superconductivity) specific.
- `g_hudson_material_state(witness, distribution, target, thresholds)` — the Hudson-specific
  narrowing of identity: `G_hudson_material_state = HC-01 (nonmetallic-elemental) AND HC-02
  (atomically dispersed)`. Both sub-claims must reach at least `PROVISIONALLY_SUPPORTED`. Returns
  `(passed, HudsonIdentity)`, where `HudsonIdentity` is `established` / `hudson-satisfied` /
  `hudson-failed` / `hudson-unresolved`.
- `g_conventional_superconductivity(measured)` — Branch A, measured only: zero resistance AND
  flux exclusion AND critical behavior AND artifact excluded. Default-blocked (all fields of
  `MeasuredEvidence` default `False`).
- `g_candidate_optical(optical_result)` — Branch B: coherent-mode (`STRONG_COUPLING` +
  `MACRO_COHERENCE`) AND material-coupling (`ELECTRONIC_COUPLING`) AND energy-transport
  (`LOW_LOSS_TRANSPORT`) all present in the measured `HudsonOpticalResult.supported` set.
- `optical_magnetic_causality(optical_result)` — Branch B level-7: measured `dM/dP` tracks the
  optical resonance (`MAGNETISM_COUPLED` in `supported`).
- `replication_gate(rep, thresholds)` — default-blocked: `None` returns `False`; otherwise
  requires `n_batches >= min_batches`, `n_labs >= min_labs` (more than one lab), preregistered
  thresholds, raw data retained, and blinded controls correctly classified.

`g_hudson_mechanism = g_hudson_material_state AND g_candidate_optical AND
optical_magnetic_causality AND replication` — the full claim that the Hudson mechanism, not
ordinary superconductivity, explains the observations, is default-blocked behind measured optical
transport, measured magnetic causality, and external replication; it can never be true from
simulated inputs alone.

## HC-02 as a policy over `structure`

HC-02 is not a Boolean measurement, it is a policy evaluated over a `StructuralDistribution`:

- `f_single = distribution.f1()` — the isolated-atom fraction must clear
  `th.hudson_hc02_min_isolated_fraction`.
- `clustered_ub = min(1.0, (1 - f_single) + th.hudson_hc02_cluster_margin)` — an upper bound on
  the clustered fraction (`P(n)` for n > 1), which must stay under
  `th.hudson_hc02_max_clustered_fraction`.
- `coordinated = sum` of `distribution.nn_distances()` fractions whose finite bond distance is
  within `th.hudson_hc02_bond_length_ang` — a direct PGM–PGM coordination signal, which must stay
  under `th.hudson_hc02_pgm_pgm_tolerance`. A monomer's nearest-neighbor distance is `+inf` (no
  bond), so it never contributes to `coordinated`.

HC-02 clears (reaches `PROVISIONALLY_SUPPORTED`) only when all three conditions hold
simultaneously; otherwise it stays at `CANDIDATE`.

## Two roll-ups

**Layer 1 — portfolio best-of.** For each claim `HC-j`, take the best (`max` by `ClaimStatus`)
record for that claim across *all* candidates in the portfolio, independently per claim. This
answers "what is the best evidence for HC-j anywhere in the portfolio" and is reported as
`HudsonLedger.claims`.

**Layer 2 — integrated weakest-link within a lineage, then best across lineages.** Candidates are
grouped by `lineage_key` (same batch/family combine via per-claim `max`, i.e. aliquots of one
physical sample corroborate each other). Within one lineage, the integrated status over the core
claim set `_CORE = (HC-01, HC-02, HC-04, HC-06, HC-07)` is the **weakest link**:

```
integrated(lineage) = min_{j in CORE} status(lineage, HC-j)
```

The reported `integrated_status` is then the **best across lineages**:

```
integrated_status = max_lineage( min_{j in CORE} status(lineage, HC-j) )
```

This is `max_lineage( min_claim )` — the correct, non-Frankenstein form. **It is never**
`min_claim( max_candidate )` — i.e. never taking the best candidate independently per claim and
then AND-ing those independently-optimized claims together across different lineages. That
inverted form (`min_j[max_c ...]`) would let one specimen's identity evidence be stitched to a
*different* specimen's IR doublet and a *third* specimen's flux exclusion, manufacturing an
integrated "supported" state that no single physical sample ever exhibited. The ledger computes
only `max_lineage(min_claim)`; `tests/test_hudson_ledger.py` asserts this directly by constructing
a portfolio where the Frankenstein form and the correct form diverge.

Gates (`g_identity_established`, `g_hudson_material_state`, `g_conventional_superconductivity`,
`g_candidate_optical`, `optical_magnetic_causality`, `replication`) are evaluated **only on the
winning lineage's own measured evidence** — never on a cross-lineage union of measured evidence.
This is the same same-lineage requirement that the anti-Frankenstein roll-up enforces: gates read
one physical sample's data, not evidence assembled from different samples.

## Lineage model

`MaterialLineage` / `lineage_key` / `group_by_lineage` (see `lineage.py`) model three integration
levels — a single specimen, a batch of aliquots from one preparation, and a family of batches —
and claims attach to the *resulting material state* at whichever level candidates were grouped, not
to an abstract "the sample" with no traceable preparation history. `singleton_lineage` is used when
no explicit lineage is supplied, so every candidate still has a well-defined `lineage_key` for
grouping. Lineage grouping is order-independent: `group_by_lineage` sorts by key before returning,
so iteration order never depends on dict insertion order.

## Default-blocks

The following are `False` (or `None`) unless the researcher supplies `MeasuredEvidence` /
`ReplicationEvidence` explicitly — the simulation path can never climb past `LEAD` for these:

- `g_conventional_superconductivity` — all of `zero_resistance`, `flux_exclusion`,
  `critical_behavior`, `artifact_excluded` default `False`.
- `g_candidate_optical` / `optical_magnetic_causality` — `optical_result` defaults `None`.
- `replication_gate` — `replication` defaults `None`; `rep is None` short-circuits to `False`.
- HC-07 (`credited_sc_lead -> LEAD`, never `SUPPORTED`) — a simulated SC lead never reaches
  `SUPPORTED` on its own.
- HC-03 / HC-05 / HC-08 (procedural claims) — `hc03_orbital_confirmed`, `hc05_recovery_confirmed`,
  `hc08_mass_confirmed` all default `False`; without a measured confirmation they stay at
  `CANDIDATE` with a Level-3 decisive-experiment design in the note, never `SUPPORTED`.

## Evidence-level ceilings

Simulation-produced `evidence_level` never exceeds 2 (identity/dispersion witness records, IR
contaminant screen, Meissner screen). A decisive-experiment design (procedural claims with no
measured confirmation) is Level 3. Level 4 is reserved for measured confirmations — a real
observation, not a simulated one. Level 5 (independently replicated) is reachable only from
`ReplicationEvidence` metadata describing an external, multi-lab replication.

## Never "VALIDATED"

`HudsonLedger.explain()` and `_interim_verdict()` are the only summary-string producers in this
module, and both draw from a fixed, closed set of phrases (`identity-unresolved`,
`identity-established (not Hudson-conformant)`, `novel-phase-candidate (Hudson material state; no
transport/magnetism established)`, `SC-like-response (optical coherent transport; mechanism not
yet fully closed)`, `bulk-SC-supported (conventional route; distinct from the Hudson optical
mechanism)`, `independent-replication-achieved (Hudson mechanism supported on one replicated
lineage)`). None of these strings, nor any other code path in this module, ever produces
`"HUDSON CLAIM VALIDATED"`. `explain()` states this invariant explicitly in its own output.
