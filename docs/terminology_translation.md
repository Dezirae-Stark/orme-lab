# Terminology Translation — The Physics Translation Matrix

Hudson-era ORME vocabulary is not standard physics vocabulary. Using it directly
leads to two failure modes: (a) accepting the claims because the words *sound*
profound, or (b) rejecting them because the words are non-standard. Both are lazy.

This matrix does the disciplined thing instead: for each piece of ORME language,
it names the **most charitable modern interpretation**, states whether that
interpretation is **testable**, and points to where the model encodes it. This
lets us translate slogans into hypotheses that modern physics can analyze —
without prejudging the answer.

## Core translation matrix

| ORME / Hudson wording | Charitable modern interpretation | Testable? | Encoded in |
|-----------------------|----------------------------------|-----------|------------|
| "Orbitally rearranged" | An unusual / metastable electronic configuration; altered orbital occupancy | **Yes** — DFT config search | `spin_states.py`, `elements.py` |
| "High spin" | A measurable spin state; maximized unpaired-electron count (Hund-like). **Treat as a placeholder term** until mapped to a measurable quantity — it may mean collective electronic/nuclear spin *order* (H13), not literal universal alignment | **Yes** — magnetometry, ESR/EPR, NMR, DFT spin density | `spin_states.py` |
| "Monatomic" | Isolated atoms **or** nanoclusters **or** a distinct chemical phase | **Yes** — XRD/XPS/EDS; coupling analysis | `geometry.py`, `coupling.py` |
| "Rice-bean shape" | Anisotropic (prolate) electron/spin density, or a molecular-orbital density, or cluster geometry | **Yes** — charge-density anisotropy tensor | `electron_density.py`, `geometry.py` |
| "Light flows through it" | **Electromagnetic/quantum coherence**; polaritons; plasmonic modes; lossless energy transport — **not** electrons literally becoming photons | **Yes** — optical/THz/IR spectroscopy | roadmap: EM-coherence module (see below) |
| "Weight loss" | Artifact, buoyancy, magnetic force, or a genuine anomaly (extraordinary claim) | **Yes** — controlled gravimetry with field/vacuum controls | not modeled (out of scope v0.1) |
| "Superconductivity" | Zero DC resistance **AND** Meissner flux expulsion (both required) | **Yes** — transport + SQUID | `superconductivity.py`, `observables.py` |

## The "light" reframing (the important one)

Hudson's claim that superconducting electrons "become light" is, read literally,
incompatible with condensed-matter physics: Cooper pairs are composite bosons of
two electrons; photons are massless gauge bosons. They are different objects.

But there is a defensible reframing. Instead of

> electrons → photons

the charitable hypothesis is

> electrons become **phase-coherent and strongly coupled to an electromagnetic
> field**.

That second statement is recognizable modern physics: cavity photons hybridizing
with electronic excitations (exciton-polaritons), plasmonic collective modes, and
light-driven/light-controlled superconductivity are all active research areas.
Someone observing long-lived coherent polarization or plasmon-polariton behavior
*without* the modern vocabulary might well describe it as "light flowing through
the material."

This shifts the research question from the near-unfalsifiable

> "Is this a room-temperature superconductor?"

to the tractable

> "Is this an unusual **coherent quantum material** (polaritonic / plasmonic /
> cavity-coupled)?"

Related but not identical questions — and the second is where the reverse-
engineering has the most room to work.

## Extended hypothesis set

The core repo encodes 7 hypotheses (see `hypothesis_matrix.md`). The originating
research discussion added several more; they are recorded here because they shape
the roadmap even though v0.1 does not fully model all of them:

| # | Hypothesis | Status in codebase |
|---|-----------|--------------------|
| H12 | **Electromagnetic-coherence misidentification** — the "light" effect is EM/quantum coherence (polaritons/plasmons), not superconductivity per se | roadmap module |
| H13 | **Collective spin polarization** — "high spin" = a high degree of *collective* electronic/nuclear spin **order**, not literal identical-spin alignment of every particle (forbidden by Pauli exclusion + the nuclear shell model as a stable ground state). Probe via ESR/EPR, NMR, SQUID, synchrotron X-ray | partially: `spin_states.py` (electronic only); roadmap: collective/nuclear order |
| H14 | Electron-density anisotropy increases inter-unit coupling/coherence, favoring SC-like behavior | modeled: `electron_density.py` → `carrier_coherence_proxy` |
| H15 | The active unit is a **nanocluster**, not monatomic | modeled: `geometry.py` compact clusters |
| H16 | Claimed SC is actually **polaritonic / plasmonic** coherence | roadmap module |
| H17 | The material is a **granular Josephson network** | partially: `resistance_regime`; roadmap: explicit network model |
| H18 | Preparation creates **metastable charge/spin states** | modeled: spin-state enumeration; roadmap: charge states |
| H19 | Magnetic fields **stabilize or destroy** the state depending on phase | modeled: `magnetic_field.py` (both directions) |
| H20 | "Rice-bean" is a **molecular-orbital** shape, not an atomic-shell shape | partially: cluster geometry; roadmap: MO density from DFT |

## Roadmap module implied by this matrix

The translation matrix makes clear that a future **`electromagnetic_coherence.py`**
module is warranted, to model H12/H16: plasmon/polariton mode frequencies, light–
matter coupling strength, and coherence lifetime, with predicted optical/THz
observables. That is the natural next expansion beyond the current
spin → density → coupling → SC chain, and it is where Hudson's "light" language,
charitably translated, actually points.
