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
| H1-open-shell | High-spin **open-shell** PGM units (d_shell_vacancies > 0: Ir, Os, Pt, Rh, Ru) show prolate rice-bean anisotropy | Anisotropy ~0 for an open-shell high-spin element | open |
| H1-closed-shell | High-spin **closed-shell** PGM units (d¹⁰: Ag, Au, Pd) show prolate anisotropy | Anisotropy > 0 for any closed-shell element (in the toy model it is 0 — this variant is expected to be refuted) | open |
| H2 | High-spin states deform electron density into anisotropic shapes | `electron_density.py` | `electron_density_anisotropy_score` | Anisotropy score stays ~0 across all accessible spin states |
| H3-cluster | Compact clusters are structurally stable (compactness controls stability) | A compact cluster scores unstable | open |
| H3-monomer | Isolated monomers carry structural stability | A monomer scores stable (in the toy model stability is 0 — expected refuted) | open |
| H4 | **Bulk** superconductivity requires an inter-unit coupling channel | `coupling.py` | `inter_unit_coupling_score` | (structural premise — encoded as a *necessary gate*, not tested for rejection) |
| H5 | If units are truly electronically isolated, superconductivity fails | `coupling.py`, `superconductivity.py` | `is_electronically_isolated` + plausibility gate | A monomer/isolated unit is scored as a viable bulk SC candidate (would signal a **model bug**, not a discovery) |
| H6 | Alternatives: nanoclusters, granular Josephson networks, plasmonic/polaritonic coherence, oxide/hydroxide/salt phases, measurement artifacts | all modules + `validation_tests.md` | routing via `predict_resistance_regime`, `meissner_screening_proxy` | An alternative is ruled out only by the specific discriminating measurement in `validation_tests.md` |
| H7-singlet | Under a **singlet** pairing assumption, a static moment pair-breaks the state: the critical field is suppressed and Pauli-limited (Chandrasekhar-Clogston, Bc_pauli = 1.86·Tc) | `magnetic_field.py` (`pairing_critical_field`, `PairingSymmetry.SINGLET`) | `field_response_ratio` | The measured critical field exceeds the Pauli limit (`field_response_ratio` > 1 — only a triplet can host that) |
| H7-triplet | Under an **equal-spin triplet** pairing assumption, the moment is carried by the condensate itself: the critical field is field-robust and may exceed the Pauli limit | `magnetic_field.py` (`pairing_critical_field`, `PairingSymmetry.TRIPLET`) | `field_response_ratio` | The measured critical field stays at or below the Pauli limit (`field_response_ratio` <= 1 — no evidence of triplet enhancement) |
| H16-drive-triplet | A spin-carrying (equal-spin triplet) coherent condensate can be parametrically pumped by an AC **magnetic** drive (magnon-BEC analogue) — live only while H7-triplet is still open | `electromagnetic_coherence.py` (`magnetic_drive_response`) | `em_drive_response` | The modeled magnetic-drive response falls below baseline (`em_drive_response` < `DRIVE_BASELINE` = 0.1), or its parent H7-triplet is killed (liveness gate — INCONCLUSIVE, not a kill) |

**Why H7 is pairing-scoped, and the two decisive measurements:** singlet and equal-spin-triplet
pairing make *opposite* Pauli-limit predictions from the same applied-field data, so a single H7
would be un-killable by field alone (whichever way the field response goes, some pairing channel
"explains" it). Splitting it lets a field measurement retire exactly one branch: `field_response_ratio`
(critical field vs the Chandrasekhar-Clogston Pauli limit, 1.86·Tc) kills H7-singlet when it is > 1
and kills H7-triplet when it is <= 1. `H16-drive-triplet` adds a second, independent decisive
measurement — modeled magnetic-drive response vs `DRIVE_BASELINE` — and is judge-time-gated live
only while H7-triplet remains open (`LIVENESS_DEPENDENCIES`, `src/orme_lab/lab_loop/hypotheses.py`):
a dead H7-triplet makes the drive channel INCONCLUSIVE, never a false SURVIVED.

**Why H1/H3 are element/geometry-scoped (measured):** `d_shell_vacancies` exactly predicts the
toy anisotropy — closed-shell (d¹⁰: Ag, Au, Pd) → 0.000 in both spin states; open-shell (Ir, Os,
Pt, Rh, Ru) → 0.165–0.458 in high-spin. A single binary H1 would be retired globally by the first
closed-shell counterexample even though it holds for open-shell elements; the scoped variants retire
independently. H3 splits the same way by geometry (compact_cluster stability 0.333 vs monomer 0.000).
The lab loop's `HYPOTHESES` registry (`src/orme_lab/lab_loop/hypotheses.py`) carries the scoped ids;
avenues target a scoped variant and a mislabeled one (wrong element/geometry class) is skipped.

## How the hypotheses chain together

The hypotheses are **not** independent; they form a dependency chain that the
pipeline walks in order:

```
H1 (spin) ──▶ H2/H3 (density anisotropy / shape)
                     │
H4/H5 (coupling) ────┼──▶ carrier proxy ──▶ H7-singlet/H7-triplet (field response)
                     │                            │
                     └────────────▶ observables ──┴──▶ SC plausibility (AND-gate)
```

The key design decision: **H4/H5 dominate**. A candidate can be maximally
high-spin (H1), beautifully rice-bean (H2/H3), and field-tolerant (H7-singlet/H7-triplet), and still
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
