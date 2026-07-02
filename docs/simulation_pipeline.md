# Simulation Pipeline

This document describes the data flow of a screen, the meaning of each toy score,
and — critically — the boundary between what the current lightweight model does
and what a real ab-initio calculation would have to do (the `TODO` markers in the
source).

## Overview

```
Element ─▶ Geometry ─▶ SpinState ─▶ Density anisotropy ─▶ Coupling
   │                                                          │
   └──────────────────────────────────────────────┐         ▼
                                                    │   carrier proxy
                                                    ▼         │
                                            Field response ◀──┘
                                                    │
                                                    ▼
                                             Observables
                                                    │
                                                    ▼
                                    Superconductivity plausibility
                                          (AND-gate of gates)
                                                    │
                                                    ▼
                                          Ranked CandidateRecord ─▶ CSV
```

A **candidate** is the triple `(element × geometry × spin state)`. `run_screen`
enumerates candidates, scores each, and returns them ranked best-first. The
ranking is fully deterministic (see the determinism note below).

## Stage-by-stage

### 1. Element (`elements.py`)
Provides valence d/s electron counts and covalent radius. These are textbook
gas-phase atomic values, **not** computed. `TODO(dft)`: derive effective
configurations from an ab-initio calculation for the actual cluster/solid.

### 2. Geometry (`geometry.py`)
Builds monomer → dimer → chain → compact-cluster motifs and computes
nearest-neighbour distance, mean coordination, and radius of gyration. This spans
the **isolated ↔ connected** axis so hypothesis 5 is always exercised. Pure
geometry, no energetics. `TODO(ase)`: relax structures with a real optimizer.

### 3. Spin state (`spin_states.py`)
`spin_polarization_score ∈ [0,1]` — normalized unpaired-electron count. A d⁵
high-spin centre scores 1.0; a closed shell scores 0.0. Encodes H1.

### 4. Electron-density anisotropy (`electron_density.py`)
Maps a spin state to a prolate density **ellipsoid** and reduces it to a
fractional-anisotropy scalar `∈ [0,1]`. The "rice-bean" band is a middle range of
prolate anisotropy. Encodes H2/H3. `TODO(dft)`: replace the heuristic with the
second-moment tensor of a real charge density (cube file).

### 5. Coupling (`coupling.py`)
`inter_unit_coupling_score ∈ [0,1]` from an exponential orbital-overlap proxy
(distance) × a coordination-based connectivity factor. A monomer scores 0 and is
flagged **isolated**. Encodes H4/H5. `TODO(dft/tb)`: use real transfer integrals
`t_ij` or exchange couplings `J`.

### 6. Carrier / coherence proxy (`superconductivity.py`)
`carrier_coherence_proxy` rewards delocalization (coupling) and penalizes runaway
1D anisotropy (needle → localization / Peierls). A superconductor needs mobile
paired carriers, not just coupling.

### 7. Field response (`magnetic_field.py`)
`magnetic_field_suppression_factor ∈ [0,1]` = `1 − (H/H_c)²` for `H < H_c`, else 0
— the parabolic type-I critical-field form. `high_spin_field_stabilization`
handles the opposite (magnetic) case where a field *stabilizes* the state. Encodes
H7. `TODO(physics)`: separate orbital (H_c2) and paramagnetic (Chandrasekhar–
Clogston) pair-breaking limits.

### 8. Observables (`observables.py`)
Predicts magnetic susceptibility (Curie-law proxy), a qualitative resistance
regime, field sensitivity, and — most importantly — a **Meissner screening**
proxy. `has_measurable_signal` feeds the falsifiability gate. `TODO(dft/epw)`:
compute susceptibility and electron-phonon-derived gap.

### 9. Superconductivity plausibility (`superconductivity.py`)
An **AND-gate** of five necessary conditions (coupling, carriers, field tolerance,
structural stability, measurable observable). If any fails, score = 0. If all
pass, score = product of normalized margins (weakest link dominates). The verbal
verdict is always hedged: "RULED OUT" or "NOT RULED OUT" — never "proven".

## Determinism

Given the same `LabConfig`, a screen produces byte-identical CSV. There is no
wall-clock, no unseeded RNG, and records are sorted by a **total, tie-broken key**
(`-plausibility, -coupling, -spin, element, geometry, spin_label`) so ordering
never depends on input order or dict iteration. This matters: reproducibility is a
precondition for the whole enterprise being scientific rather than anecdotal.

## Extending the pipeline with a real backend

Every heavy-physics gap is marked with a `TODO(<backend>)` comment, and each is
now a **concrete extension point** in `src/orme_lab/backends.py`: a
`DFTBackend` interface with named adapter stubs (`ASEBackend`, `PySCFBackend`,
`GPAWBackend`, `ORCABackend`, `NWChemBackend`, `QuantumEspressoBackend`,
`EPWBackend`) keyed to a `Capability` enum. To wire a real calculation in,
subclass a backend, override the seam method, and decorate it with
`@implemented(Capability.X)`:

```python
from orme_lab import DFTBackend, Capability, implemented, run_screen

class MyASE(DFTBackend):
    @implemented(Capability.RELAX_GEOMETRY)
    def relax_geometry(self, geometry):
        ...  # real ASE relaxation, returns a ClusterGeometry

records = run_screen(backend=MyASE())   # relaxation from ASE, everything else toy
```

The pipeline consults the backend **only** for capabilities it genuinely
implements (`backend.provides(...)`) and falls back to the toy model otherwise,
so `run_screen()` with no backend is unchanged. The intended integration order:

1. **ASE** (`RELAX_GEOMETRY`) — structure handling and relaxation.
2. **PySCF / GPAW** (`SPIN_STATE`, `DENSITY_ANISOTROPY`) — cluster/periodic DFT.
3. **Tight-binding fit** (`INTER_UNIT_COUPLING`) — real transfer integrals.
4. **Quantum ESPRESSO + EPW** (`SC_GAP`, `DIELECTRIC_FUNCTION`) — electron-phonon
   coupling and an Eliashberg gap, the *only* route to a defensible
   superconductivity estimate.

Until those land, `available_backends()` is empty and every number this pipeline
emits is a **triage signal** — which candidates deserve real computation, not
which ones superconduct. A wired backend does not by itself raise a result above
the charter's Level 2–3; that needs independent, instrumented replication.
