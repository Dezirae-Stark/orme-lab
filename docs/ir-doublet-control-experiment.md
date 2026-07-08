# IR-doublet control experiment — the decisive measurement

**Status:** Level-3 laboratory prediction (`LABORATORY_PREDICTION`). The lab *designs* this
experiment; it does not and cannot *run* it — a real observation is Level 4+ and needs a
calibrated instrument and an independent replicator. Computed by
`src/orme_lab/control_experiment.py`; framing per `docs/CHARTER.md`.

## The question

The contaminant screen (`docs/patent-claim-tests.md`) found the Hudson patent's 1400–1600 cm⁻¹
identity doublet (DE3920144A1; Rh 1429.53/1490.99, Ir 1432.09/1495.17) **plausibly** an
ionic/bridging carboxylate surface contaminant, with metal–metal bonding excluded. But a
band-reachability match cannot decide **origin**. Two hypotheses remain:

- **H_contaminant** — the doublet is a light-atom (C–O carboxylate) *surface* species.
- **H_intrinsic** — the doublet is *intrinsic to the metal* (a metal–metal bond / the ORME
  high-spin state the patent asserts).

Each control below predicts a *different* outcome under the two hypotheses, so a real
measurement would adjudicate. Predictions are computed symmetrically for both — the module
decides neither.

## Samples and references

1. The ORME/OUME sample as prepared.
2. A clean reference of the same metal (sputter-cleaned or vacuum-annealed foil/powder).
3. A deliberately carboxylate-dosed reference (the same metal exposed to acetic-acid vapour
   or an acetate solution) — the positive control for H_contaminant.
4. A substrate/solvent blank (the preparation route minus the metal) — to attribute bands to
   processing residue.

## Decision table (computed; Rh doublet 1429.53 / 1490.99)

| Control | H_contaminant predicts | H_intrinsic predicts | Decisive? |
|---|---|---|---|
| **¹³C substitution**, re-measure ~1491 cm⁻¹ | red-shift **≈ −33 cm⁻¹** (C–O bond) | ≈ 0 (Rh–Rh has no C) | **yes** |
| **¹⁸O substitution**, re-measure ~1491 cm⁻¹ | red-shift **≈ −36 cm⁻¹** (C–O bond) | ≈ 0 (Rh–Rh has no O) | **yes** |
| **¹⁵N substitution** | ≈ 0 (a C–O carboxylate has no N) | ≈ 0 | **no** — wrong label for this bond |
| **Raman on the same sample** | active in IR *and* Raman; strong Raman νsym ~1430–1470 accompanies the IR doublet | symmetric M–M stretch is **IR-forbidden** (mutual exclusion) — an IR-observed doublet contradicts a centrosymmetric M–M origin; no IR/Raman coincidence | **yes** |
| **Coverage/exposure scaling** (vary exposure or surface-area/volume, track band area) | area grows ~linearly with exposure (Beer–Lambert × sub-saturation Langmuir), saturating at a monolayer; tracks surface area | area invariant to exposure and surface treatment | **yes** |

Result: **4 of 5 controls are decisive.** The Ir doublet gives the same pattern (¹³C ≈ −33,
¹⁸O ≈ −36). The ¹⁵N row is included deliberately to show a *non-decisive* control — the
predictor can fail to discriminate when the label doesn't test the suspected bond, which is
the neutral-outcomes discipline made visible.

## Qualitative controls (in the protocol, not computed)

- **Desorption.** Mild anneal / Ar-sputter / solvent wash: a physi/chemisorbed organic
  contaminant should *lose* the doublet; an intrinsic metal mode should keep it.
- **Dosing.** Deliberately expose the clean reference (sample 2) to carboxylic-acid vapour: if
  the doublet *appears/grows*, it is a carboxylate surface species.

## Physics and citations

- Isotope shift: harmonic diatomic ν ∝ 1/√μ (Herzberg, *Spectra of Diatomic Molecules*;
  Atkins, *Physical Chemistry*). Specific-isotope masses (CODATA): ¹²C 12.000, ¹³C 13.00335,
  ¹⁶O 15.99491, ¹⁸O 17.99916, ¹⁴N 14.00307, ¹⁵N 15.00011.
- Raman/IR mutual-exclusion rule for centrosymmetric species (Atkins; Harris, *Quantitative
  Chemical Analysis*).
- Coverage: Beer–Lambert (band area ∝ absorber count); Langmuir, *J. Am. Chem. Soc.* 40 (1918)
  1361 (adsorption isotherm). This is the softest control — real samples saturate and organics
  desorb, so read the trend (linear vs flat), not an absolute area.

## What a result would mean

- **Doublet shifts with ¹³C/¹⁸O, appears in Raman with a νsym partner, scales with exposure,
  and desorbs on cleaning** → surface carboxylate contamination; the patent's "OUME identity
  marker" is a processing artifact, and the ORME reading of *this* signature is refuted.
- **Doublet is isotope-insensitive, has no Raman νsym coincidence, is invariant to exposure,
  and survives cleaning** → not a light-atom surface species; the mundane explanation fails and
  the claim earns a genuine anomaly to pursue (still not a proof of superconductivity — only
  that the doublet is intrinsic).

Either way the outcome is a real Level-4 observation once measured; this document is the
Level-3 prediction that tells an experimentalist exactly which measurement to make.

## Note on the chelating-carboxylate citation

The carboxylate chelating Δ floor (65 cm⁻¹) used by the screen is cited one hop through a
directly-read Wits MSc thesis (Table 2.4 reproducing Grigorev 1963). The Grigorev primary
(*Russ. J. Inorg. Chem.* 8 (1963) 409f) was **exhaustively searched** (HathiTrust, Springer,
Google Books, eLibrary.ru, Internet Archive — confirmed to hold zero RJIC content —
ScienceDirect) and is **not digitally accessible**; the citation therefore remains one-hop.
See `~/.claude/research-wiki/prior-art/ir-contaminant-bands.md` for the full search log.
