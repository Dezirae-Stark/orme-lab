# Design — Patent-Claim Tests (IR-doublet, thermal stability, Meissner Hc1)

**Date:** 2026-07-06 · **Status:** approved for implementation planning
**Source:** Hudson ORME patent DE3920144A1 (family: granted US 5,076,973). Full extraction:
`~/.claude/research-wiki/prior-art/hudson-orme-patents-de3920144a1.md`.

## Purpose

Translate three of the Hudson patent's own signature claims into deterministic, evidence-clamped
triage screens, and surface all of the patent's claim-methods on the lab site as tracked
hypotheses. This tests the patent *on its own terms* rather than via the metal-lattice EPW proxy.

Framing is unchanged from the rest of the lab: **triage, not proof.** Every verdict is clamped to
evidence Level ≤ 2 (`LAB_CEILING`). Each screen is a *ruler built from cited physical ranges*; the
verdict is whatever the observed value lands on when compared to that ruler. The validation layer
must remain able to fail — a different element or a softer bond flips the verdict on its own. No
verdict is written into this spec as foregone; the actual outputs are recorded in
`docs/patent-claim-tests.md` only after the screens are run.

## Non-goals (YAGNI)

- No new EPW / DFT compute. These are closed-form screens.
- No wet-chemistry modeling of the preparation routes.
- ac-Josephson and "assay < 100%" get documented cards, not computable screens (neither is cleanly
  falsifiable in this framework; the latter is flagged unfalsifiable-by-construction).
- No network egress, no telemetry, loopback-only — unchanged lab invariants.

## Architecture

Three focused screen modules in `src/orme_lab/`, each mirroring the existing
`superconductivity.py` / `observables.py` pattern: a frozen result dataclass carrying the computed
quantity, the cited physical reference band, a verdict enum, an evidence level (≤2), and the
falsification quantity. Python is authoritative and tested; the web layer presents verdicts and adds
live-input widgets whose shared constants are pinned by Python parity tests.

```
src/orme_lab/
  ir_signature.py       # Test 1 — harmonic diatomic reachable-band screen
  thermal_stability.py  # Test 2 — Tammann/Hüttig sintering-onset screen
  meissner_field.py     # Test 3 — Hc1 → penetration depth / superfluid density screen
tests/
  test_ir_signature.py
  test_thermal_stability.py
  test_meissner_field.py
  test_patent_web_parity.py   # pins web JS constants to the Python modules
web/
  patent_tests.js       # 3 live-input widgets (one-line-formula JS mirrors)
  hypotheses.js         # + new "patent" group (5 cards)
  index.html, app.js, styles.css  # mount the panel, reuse existing card styles
docs/
  patent-claim-tests.md # findings write-up, authored AFTER running the screens
```

Each module exposes: a small reference-data table (module-level, cited), a pure forward function,
the result dataclass, and a `screen_*()` entry point taking the patent's observed value(s).

## Test 1 — IR-doublet (`ir_signature.py`)

**Claim.** OUMEs show an IR doublet between 1400–1600 cm⁻¹. Quoted values: Rh 1429.53 / 1490.99;
Ir (post-H₂) 1432.09 / 1495.17 cm⁻¹.

**Physics.** Harmonic diatomic relation
ν̃ (cm⁻¹) = 1302.8 · √(k / μ), with k in mdyne/Å and μ in amu.
Calibration check (in tests): H₂ k=5.7, μ=0.5 → 4417 cm⁻¹ (obs 4401); HCl k=5.2, μ≈0.980 → 3000 cm⁻¹
region. The constant 1302.8 and these force constants are standard diatomic-spectroscopy reference
values (Herzberg, *Spectra of Diatomic Molecules*; Atkins, *Physical Chemistry*), used here as
representative bands, not novel measurements.

**Computation.**
- *Reachable band* per bond family: [1302.8·√(k_min/μ), 1302.8·√(k_max/μ)].
- *Verdict per observed line*: which families' reachable bands contain ν̃_obs.
- *Aggregation to a single doublet verdict*: both lines are evaluated; the overall `verdict` reports
  the family that can account for the doublet, with metal–metal marked excluded when neither line is
  reachable within the metal–metal band (the higher line, which drives the largest k_required, is
  decisive). `reachable_by_family` retains the per-line detail.
- *Falsification quantity* (inverse): k_required = μ · (ν̃_obs / 1302.8)². For the Rh line
  (1490.99, μ = 102.905/2 = 51.45) this is ≈ 67.4 mdyne/Å — reported alongside the metal–metal
  envelope and CO (18.6) for scale.

**Reference bond families (representative literature ranges, cited as above):**

| family                | μ (amu)            | k range (mdyne/Å) |
|-----------------------|--------------------|-------------------|
| metal–metal (Rh/Ir)   | ~51 (homodimer)    | 1 – 5 (incl. multiply-bonded dimers) |
| C–O / C=O             | 6.86               | 5 – 13            |
| C=C                   | 6.0                | 8 – 10            |
| N–O                   | 7.47               | 10 – 16           |

Values are stored as a module table with a source comment. The metal–metal upper bound is the
representative envelope including quadruple-bonded dimers (e.g. Re₂Cl₈²⁻, ν(M–M) ~275 cm⁻¹); flagged
as such.

**Result dataclass** `IrSignatureResult`: `observed_lines`, `k_required_mdyne`,
`reachable_by_family` (dict), `verdict` ∈ {`metal_bond_excluded`, `metal_bond_consistent`,
`light_atom_consistent`, `indeterminate`}, `evidence_level` (≤2), `note`.

## Test 2 — thermal stability (`thermal_stability.py`)

**Claim.** Does not sinter at 800 °C (reducing); remains amorphous powder to 1200 °C.

**Physics.** Sintering-onset heuristics from bulk melting point T_m (K):
Hüttig T ≈ 0.3·T_m (surface-atom mobility onset), Tammann T ≈ 0.5·T_m (bulk mobility onset).
Established rule in sintering / heterogeneous-catalysis literature; stored as a heuristic with a
source comment. Melting points from CRC-standard values (Rh 1964, Ir 2446, Pt 1768, Pd 1555,
Os 3033, Ru 2334, Au 1064, Ag 962, Cu 1085 °C).

**Computation.** For a given element and claimed stability temperature T_claim:
compute T_Hüttig, T_Tammann; classify whether T_claim sits below the refractory sintering envelope
(ordinary powder would already survive it → not diagnostic) or above it (would be anomalous for that
element). Genuinely per-element: refractory PGMs place 800–1200 °C below Tammann onset; a
low-melting element places the same claim above its Tammann onset.

**Result dataclass** `ThermalStabilityResult`: `symbol`, `t_melt_c`, `t_huttig_c`, `t_tammann_c`,
`t_claim_c`, `verdict` ∈ {`within_refractory_envelope`, `exceeds_envelope`, `marginal`},
`evidence_level` (≤2), `note`.

## Test 3 — Meissner Hc1 (`meissner_field.py`)

**Claim.** Lower critical field Hc1 below Earth's field (~50 µT) for Ir/Au S-OUME; slightly above for
Rh.

**Physics.** From B_c1 ≈ (Φ0 / 4πλ²)·ln κ (κ default ~2.7 → ln κ ≈ 1, documented assumption),
back out the London penetration depth λ, then the implied superfluid density
n = m_e / (μ0 · λ² · e²). Constants: Φ0 = 2.067×10⁻¹⁵ Wb; conventional type-I Hc for scale
(Al ~0.01 T, Sn ~0.03 T, Pb ~0.08 T) cited to Tinkham, *Introduction to Superconductivity*.
Earth's field taken as 50 µT nominal.

**Computation.** Input B_c1 → λ, n. Compare n to (a) a normal-metal reference (~10²⁸–10²⁹ m⁻³) and
(b) the dilute-monomer density that `electron_density.py` estimates. Then apply the internal-
consistency cross-check: any Meissner screening requires inter-unit phase coherence, which the
isolated-monomer premise (H-04 / H-05) lacks. The verdict therefore reports not just whether the
implied density is physical but whether the claim is internally consistent with the isolation
premise the rest of the lab already gates on.

**Result dataclass** `MeissnerFieldResult`: `b_c1_tesla`, `lambda_london_m`,
`implied_superfluid_density_m3`, `normal_metal_ratio`, `verdict` ∈ {`implied_density_physical`,
`implied_density_unphysical`, `in_tension_with_isolation`}, `evidence_level` (≤2), `note`.

## Documented cards (no compute)

- **ac-Josephson transition** — patent claims an ac-Josephson-type response above Hc2. Documented
  card linking the existing coupling-channel prior-art (`granular-josephson-network-channel.md`,
  `orme-coupling-channels-verdict.md`); marked "not independently falsifiable in this framework."
- **Assay < 100% ore premise** — patent claims OUMEs evade conventional instrumental analysis.
  Card flagged **unfalsifiable-by-construction** (a claim that fails all detection is not testable).

## Web integration

New `"patent"` group in `hypotheses.js` (5 cards: 3 computable linked to modules, 2 documented),
rendered by the existing registry machinery. New `web/patent_tests.js` panel with three live-input
widgets:
1. IR doublet — enter two lines, see reachable-band comparison + verdict (headline, live recompute).
2. Thermal — pick element + claimed T, see Hüttig/Tammann vs claim.
3. Meissner — enter Hc1, see implied λ / n / verdict.

Each widget is a one-line-formula JS mirror. `test_patent_web_parity.py` extracts the shared
constants (1302.8; Tammann/Hüttig coefficients; Φ0) from `patent_tests.js` and asserts they equal
the Python modules' values, so the site cannot drift from the authoritative screens.

## Testing

- `test_ir_signature.py`: formula calibration vs known diatomics (H₂, HCl, CO); reachable-band
  membership; k_required inverse; per-family discrimination; the patent's quoted doublets.
- `test_thermal_stability.py`: Hüttig/Tammann arithmetic; refractory vs low-melting discrimination;
  boundary/marginal cases.
- `test_meissner_field.py`: λ and n back-out against a hand-worked value; normal-metal ratio;
  isolation-tension branch.
- `test_patent_web_parity.py`: JS-vs-Python constant parity.
- All verdicts assert `evidence_level ≤ 2`.

## Invariants preserved

Evidence ceiling 2 on every verdict; deterministic (no time/RNG in any path); no network egress;
loopback-only; no telemetry; no fabricated citations (all reference values carry a source comment and
are presented as representative literature ranges, not novel measurements); neutral-outcomes
discipline (verdicts recorded only after the screens are run).

## Open items for the writing-plans step

- Exact element input set for the web widgets (default: the core screen set + Rh/Ir/Au named in the
  patent).
- Whether the docs write-up is one file or a section appended to the existing EPW run-log — default
  new file `docs/patent-claim-tests.md`.
