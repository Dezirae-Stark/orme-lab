# Hypothesis Matrix

This document is the project's scientific spine. It lists every claim the ORME/PGM
literature makes (or that we can charitably reconstruct from it), states each as a
**falsifiable hypothesis**, names the model that encodes it, and gives the concrete
condition under which the hypothesis is **rejected**.

The project does **not** assume any of these are true. Hudson-style "Orbitally
Rearranged Monoatomic Element" superconductivity is treated as an unproven claim.
Our job is to translate the claims into computable models, rule out the ones that
contradict physics, and identify the physically meaningful alternatives that
survive.

| # | Hypothesis (charitable reconstruction) | Encoded in | Toy score | Rejected when… |
|---|----------------------------------------|-----------|-----------|----------------|
| H1 | PGM atoms/clusters can enter unusual metastable electronic configurations | `spin_states.py` | `spin_polarization_score` | No configuration with elevated multiplicity exists for the element (closed shell, e.g. Pd d¹⁰) |
| H2 | High-spin states deform electron density into anisotropic shapes | `electron_density.py` | `electron_density_anisotropy_score` | Anisotropy score stays ~0 across all accessible spin states |
| H3 | The "rice-bean" shape ≈ electron-density anisotropy / MO density / cluster geometry | `electron_density.py`, `geometry.py` | `ricebean_score`, ellipsoid `is_prolate` | Anisotropy never enters the prolate rice-bean band for any candidate |
| H4 | **Bulk** superconductivity requires an inter-unit coupling channel | `coupling.py` | `inter_unit_coupling_score` | (structural premise — encoded as a *necessary gate*, not tested for rejection) |
| H5 | If units are truly electronically isolated, superconductivity fails | `coupling.py`, `superconductivity.py` | `is_electronically_isolated` + plausibility gate | A monomer/isolated unit is scored as a viable bulk SC candidate (would signal a **model bug**, not a discovery) |
| H6 | Alternatives: nanoclusters, granular Josephson networks, plasmonic/polaritonic coherence, oxide/hydroxide/salt phases, measurement artifacts | all modules + `validation_tests.md` | routing via `predict_resistance_regime`, `meissner_screening_proxy` | An alternative is ruled out only by the specific discriminating measurement in `validation_tests.md` |
| H7 | Magnetic fields stabilize / perturb / suppress / destroy the state, depending on phase | `magnetic_field.py` | `magnetic_field_suppression_factor`, `high_spin_field_stabilization` | The candidate shows no field dependence of any observable |

## How the hypotheses chain together

The hypotheses are **not** independent; they form a dependency chain that the
pipeline walks in order:

```
H1 (spin) ──▶ H2/H3 (density anisotropy / shape)
                     │
H4/H5 (coupling) ────┼──▶ carrier proxy ──▶ H7 (field response)
                     │                            │
                     └────────────▶ observables ──┴──▶ SC plausibility (AND-gate)
```

The key design decision: **H4/H5 dominate**. A candidate can be maximally
high-spin (H1), beautifully rice-bean (H2/H3), and field-tolerant (H7), and still
be *ruled out* for bulk superconductivity if it has no coupling channel. This is
the whole point of the Hudson critique: a genuinely monatomic, electronically
isolated species has no mechanism to host a macroscopic coherent condensate.

## What would falsify the *interesting* version of the claim

The interesting claim is not "PGM atoms have magnetic moments" (trivially true for
some) — it is "a room-temperature, ambient-pressure superconducting phase exists in
these materials." That is falsified the moment any of the following holds for every
candidate the model surfaces:

1. No coupling channel survives at realistic interatomic distances (H5).
2. No predicted observable exceeds a detectable magnitude (unfalsifiable ⇒ we
   decline to endorse it).
3. Every candidate that shows apparent zero resistance shows **no** diamagnetic
   screening (see `validation_tests.md` — zero-R without Meissner is not SC).

See `validation_tests.md` for the discriminating experiments and
`terminology_translation.md` for how the fringe vocabulary maps onto standard
condensed-matter concepts.

## Extended hypotheses (H12, H14–H20)

The seven hypotheses above are the repo's core. The originating research
discussion identified several more, which shape the roadmap. The most important
is **H16 / H12**: that the effect Hudson described as "light flowing through" the
material is not superconductivity at all but **polaritonic / plasmonic
electromagnetic coherence** — a real quantum-materials phenomenon. This reframes
the central question from "is it a room-temperature superconductor?" to "is it an
unusual coherent quantum material?" The full extended set (H12, H14–H20) and its
status in the codebase is tabulated in `terminology_translation.md`.
