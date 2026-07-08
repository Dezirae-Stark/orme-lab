# Patent-claim triage screens — findings

Three Hudson-patent (DE3920144A1) signature claims translated into deterministic,
evidence-clamped triage screens and run against the patent's own quoted values.
Every verdict below is **Evidence Level 1/6 (mathematical consistency; triage, not
proof)** and is clamped to the lab ceiling (`LAB_CEILING` = 2).

## Provenance

Claims and quoted values are extracted in
`~/.claude/research-wiki/prior-art/hudson-orme-patents-de3920144a1.md`; the screens
surface on the lab site as registry cards **P-IR**, **P-THERM**, **P-MEISS**
(computable) and **P-JJ**, **P-ASSAY** (documented). Screen sources:
`src/orme_lab/ir_signature.py`, `src/orme_lab/thermal_stability.py`,
`src/orme_lab/meissner_field.py`. Web mirrors: `web/patent_tests.js`, pinned to the
Python constants by `tests/test_patent_web_parity.py`.

## Method

Three focused screens, each a frozen-dataclass computation returning a computed
quantity, a cited reference band, a verdict enum, and an evidence level. Reference
values are **representative literature ranges with a source comment, never presented
as novel measurements**.

**IR doublet** (`ir_signature.py`). Harmonic diatomic:
`ν̃ (cm⁻¹) = 1302.8 · √(k/μ)`, k in mdyne/Å, μ in amu. The screen asks which bond
family could produce a line at the observed wavenumber within its representative
literature force-constant range, and what force constant a metal–metal bond would
need to reach it. Reference bands (Herzberg, *Spectra of Diatomic Molecules*;
Atkins, *Physical Chemistry*): metal–metal force-constant envelope 1–5 mdyne/Å
(including multiply-bonded dimers, e.g. Re₂Cl₈²⁻, ν(M–M) ~275 cm⁻¹); C–O/C=O
5–13 mdyne/Å; C=C 8–10; N–O 10–16.

**Thermal stability** (`thermal_stability.py`). Compares a claimed stability
temperature against the Hüttig (~0.3·T_m) and Tammann (~0.5·T_m) sintering-onset
heuristics computed from the bulk melting point in kelvin. Reference: Tammann/Hüttig
rule (sintering / heterogeneous-catalysis literature); melting points CRC-standard.

**Meissner Hc1** (`meissner_field.py`). From Hc1 back out the London penetration
depth and implied superfluid density:
`B_c1 ≈ (Φ₀ / 4π λ²)·ln κ` (κ ~ 2.7 → ln κ ~ 1, documented default) and
`n_s = m_e / (μ₀ λ² e²)`; test against physical density bounds and the lab's own
isolation premise (H-04/H-05). Reference constants and conventional-SC Hc scales
(Al ~0.01 T, Sn ~0.03 T, Pb ~0.08 T): Tinkham, *Introduction to Superconductivity*.

## Results

### P-IR — IR doublet, 1400–1600 cm⁻¹

*Evidence Level 1/6 (mathematical consistency; triage, not proof).*

Both patent-quoted doublets land **far above** the homodimer metal–metal reachable
band and resolve to `light_atom_consistent`:

| species | quoted lines (cm⁻¹) | M–M reachable band | k required at upper line | verdict |
|---|---|---|---|---|
| Rh | 1429.53 / 1490.99 | 182–406 cm⁻¹ | ~67.4 mdyne/Å | `light_atom_consistent` |
| Ir | 1432.09 / 1495.17 | 133–297 cm⁻¹ | ~126.6 mdyne/Å | `light_atom_consistent` |

A Rh–Rh (or Ir–Ir) vibration tops out near 406 (297) cm⁻¹ within a physical
force-constant envelope (≤5 mdyne/Å); reaching 1491 cm⁻¹ would need k ~67 mdyne/Å
for Rh–Rh and ~127 for Ir–Ir — an order of magnitude beyond any metal–metal bond.
A light-atom (C/N/O) bond reaches the doublet within physical force constants.
Triage read: **metal–metal excluded, light-atom (adsorbate/organic) assignment
consistent** with the observed 1400–1600 cm⁻¹ position. The ruler can fail in the
other direction — a genuinely metal-range doublet (200/300 cm⁻¹) flips the verdict
to `metal_bond_consistent` (covered by test).

### P-THERM — no sinter at 800 °C, amorphous to 1200 °C

*Evidence Level 1/6 (mathematical consistency; triage, not proof).*

| metal | claim | Hüttig onset | Tammann onset | verdict |
|---|---|---|---|---|
| Ir | 1200 °C | 543 °C | 1086 °C | `exceeds_envelope` |
| Rh | 1200 °C | 398 °C | 845 °C | `exceeds_envelope` |
| Au | 800 °C | 128 °C | 395 °C | `exceeds_envelope` |
| Os | 500 °C | 719 °C | 1380 °C | `within_refractory_envelope` |

For Ir and Rh, the 1200 °C amorphous-powder claim sits **above** the Tammann
bulk-mobility onset (1086 / 845 °C): persistent non-sintering there would be
anomalous for those metals. The same claim temperature is unremarkable for the most
refractory metals — Os at 500 °C is below even its Hüttig onset (719 °C), i.e. below
the refractory envelope entirely and not diagnostic of any exotic state. Au at
800 °C exceeds its Tammann onset (395 °C) by a wide margin, as expected for a
low-melting metal.

### P-MEISS — Hc1 below Earth's field (~50 µT)

*Evidence Level 1/6 (mathematical consistency; triage, not proof).*

At Hc1 = 50 µT (ln κ = 1): λ ≈ 1.81 µm, n_s ≈ 8.58×10²⁴ m⁻³ — about 8.6×10⁻⁵× a
normal metal's carrier density. The implied superfluid density is dilute but sits
**within** physical bounds [10²², 10²⁹] m⁻³.

- With the lab's isolated-monomer premise **on** (default): verdict
  `in_tension_with_isolation`. The implied density is physical, but Meissner
  screening requires inter-unit phase coherence that an isolated monomer
  (H-04/H-05) lacks — the claim is internally in tension with its own premise.
- With the premise **off** (`isolated_premise=False`): verdict
  `implied_density_physical` — a coupled dilute superconductor at this Hc1 is
  self-consistent on density grounds alone.

## Caveats

- **IR reference bands are representative literature ranges, not per-species
  measurements.** The screen is a reachability ruler, not a spectral assignment; a
  real determination needs Raman/IR on an actual sample, controlled for
  adsorbate/organic bands in the 1400–1600 cm⁻¹ region.
- **Tammann/Hüttig is a heuristic.** The 0.3/0.5·T_m onsets are order-of-magnitude
  sintering guides from the catalysis literature, not sharp thresholds; a claim
  crossing an onset is a flag for TGA/DSC + XRD, not a refutation.
- **The Meissner isolation-tension verdict is contingent on the isolated-monomer
  premise.** It is a statement about internal consistency with H-04/H-05, not about
  the density arithmetic; toggle `isolated_premise=False` to see the density-only
  branch (`implied_density_physical` at 50 µT). A real test is SQUID magnetometry
  (zero-field-cooled Meissner fraction).
- **The two documented cards are not computably falsified here.** P-JJ (ac-Josephson
  response above Hc2) is not independently falsifiable in this framework — it would
  need a real junction I–V with Shapiro steps under microwave drive. P-ASSAY (ore
  "assays to <100%") is unfalsifiable by construction: a claim that evades all
  detection methods is not testable as stated, and requires an independent
  quantitative recovery (ICP-MS mass balance) even to define.

## IR-doublet contaminant control (positive leg)

The IR screen above (`ir_signature.py`) is the **negative** leg: it excludes a
metal–metal bond for the patent's quoted doublet (the higher line needs
k ≈ 67 mdyne/Å against a ≤ 5 mdyne/Å metal–metal envelope) and notes the lines
sit in light-atom territory. `ir_contaminant.py` adds the **positive** leg — does
the doublet actually match a *specific, cited* IR-active species that the patent's
own wet-chemistry route would deposit? Same framing: triage, evidence Level ≤ 2.

The reference library is eight species, every band value sourced from a directly
read primary (not recollection, not an LLM summary) and citation-audited: nitrate
(Goebbert 2009), coordinated carbonate — monodentate and bidentate (Blumentritt
1967 reproducing Fujita/Martell/Nakamoto 1962), carboxylate (Steill & Oomens 2009
free-ion endpoint; Deacon & Phillips 1980 for the Δ-vs-denticity range), water bend
(Goebbert 2009), alkyl C–H (Socrates 2001 for the CH₃ umbrella; U. Delaware Fox
notes for the CH₂ scissor), ammonium (Altaner 1988), and silicone/PDMS (Shabrina,
PMC11721900). Each row scores by both line positions and
the splitting Δ; the verdict is the top candidate's fit.

**Result (computed after the library was fixed; not pre-judged).** Both patent
doublets return **`plausible_match`**, top candidate **carboxylate/acetate COO⁻
(ionic/bridging/monodentate)** (residual ≈ 0.57–0.59 band-widths), several times
ahead of the next candidate (alkyl C–H ≈ 3.4–3.8, monodentate carbonate ≈ 4.8). The
`unmatched` branch — which, combined with the metal–metal exclusion, would have been
the *anomalous* result favouring the patent — was **not** triggered: the
citation-clean library does find a mundane explanation. The layer-2
coupled-oscillator model backs out bond k ≈ 8.6 mdyne/Å and interaction
k′ ≈ 0.36 mdyne/Å for the carboxylate assignment — physically ordinary for a
light-atom stretch [4–18] — so the positive leg is internally self-consistent.

Read together: **metal–metal bonding is excluded, and the doublet's best mundane
explanation is an ionic/bridging carboxylate (organic residue) contaminant —
plausible and physically self-consistent, though not a tight single-species match.**
The reason it stays *plausible* rather than *tight* is sharper than a wide-band
coincidence: the patent's *splitting* (≈61 cm⁻¹) is **chelating**-carboxylate-like
(the chelating floor is Δ≈65), but its line *positions* (1429/1490) are **ionic**-
carboxylate-like (chelating carboxylate sits higher, ν_sym 1456–1472 / ν_asym
1537–1550). The doublet matches **no single carboxylate coordination mode on both
positions and splitting at once** — which is why the dedicated chelating row scores
*poorly* (residual ≈ 5) despite the near-coincident Δ.

### Caveats specific to the contaminant control

- **Not a spectral assignment.** A `plausible_match` means the observed doublet is
  *reachable* by a cited contaminant's band ranges, not that the sample contains it.
  Deciding it needs Raman/IR on an actual sample with adsorbate/organic controls —
  exactly the experiment the negative-leg caveat above already names.
- **Carboxylate position bands are broad.** The ionic/bridging/monodentate row's
  bands still span ~120–140 cm⁻¹, so it contains lines fairly readily — a real
  limitation of a reachability ruler, recorded, not hidden. (An earlier version made
  this worse by lumping *all* coordination modes into one row; see the next point.)
- **Carboxylate is split by coordination mode — positions and splitting must agree.**
  A given carboxylate complex is in one coordination state, so its lower line, upper
  line, and splitting all come from that one state. The library therefore carries two
  carboxylate rows: **ionic/bridging/monodentate** (ν_sym 1280–1400 / ν_asym
  1510–1650 / Δ 100–285; Steill & Oomens 2009, Deacon & Phillips 1980) and
  **chelating** (ν_sym 1456–1472 / ν_asym 1537–1550 / Δ 65–94; Grigorev 1963, one hop
  through a directly-read Wits MSc thesis Table 2.4, citation-audited against the raw
  PDF). An earlier single wide row combined the chelating *splitting* floor (Δ≈65)
  with the ionic *positions*, which let the two be satisfied by different modes at
  once — a physical incoherence (flagged in review). Splitting the rows removes it:
  the chelating row can now tightly match a genuine chelating pair (e.g. 1472/1537),
  and the patent doublet — chelating-like in Δ but ionic-like in position — correctly
  matches *neither* mode tightly, landing at `plausible_match` against the ionic row.
  The chelating floor was set to the value the literature supports, not to move the
  verdict; the verdict is unchanged from before it was sourced. Residual gap: 65 is
  the lowest *verified* chelating Δ, one hop from Grigorev's original Soviet-journal
  paper (not directly fetched); a lower value in paywalled sources (Deacon & Phillips
  1980; Zeleňák 2007) cannot be excluded.
- **Citation provenance is uneven, and flagged in-code.** Nitrate, water bend, and
  PDMS were independently re-fetched and confirmed. Carbonate traces to the
  recommended primary one hop through a directly-read thesis. Carboxylate's
  denticity range is confirmed one hop through an open-access paper citing Deacon &
  Phillips (the review itself was bot-walled), and its chelating floor (65 cm⁻¹) one
  hop through a directly-read thesis reproducing Grigorev 1963. Ammonium substitutes Altaner 1988 for
  the auditor-recommended Oxton/Knop/Falk series (Cloudflare-walled after repeated
  attempts). Every row carries its actual source in `_CONTAMINANTS`; none is a value
  I could not attribute to something read.
