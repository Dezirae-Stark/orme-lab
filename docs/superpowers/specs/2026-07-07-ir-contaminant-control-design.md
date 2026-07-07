# Design — IR-doublet contaminant control (`ir_contaminant.py`)

**Date:** 2026-07-07 · **Status:** approved for implementation planning
**Source claim:** Hudson ORME patent DE3920144A1 — OUME identity marker is an IR doublet
in 1400–1600 cm⁻¹ (quoted: Rh 1429.53/1490.99, Ir 1432.09/1495.17 cm⁻¹). Prior-art
extraction: `~/.claude/research-wiki/prior-art/hudson-orme-patents-de3920144a1.md`.
Builds on the shipped negative-leg screen `src/orme_lab/ir_signature.py` (merged PR #1).

## Purpose

The existing `ir_signature.py` is a **negative** ruler: it excludes a metal–metal bond
assignment for the patent's quoted doublet (the higher line needs k≈67 mdyne/Å against a
≤5 mdyne/Å metal–metal envelope) and notes the lines sit in light-atom (C/N/O) territory.
"Light-atom consistent" is an exclusion, not an identification.

This design adds the **positive leg**: a cited reference library of IR-active species that
the patent's own wet-chemistry route would plausibly deposit, and a screen that scores the
observed doublet against each by line position **and** splitting Δ, ranks the matches, and
returns whether a mundane species explains the doublet — or whether nothing does. Together
the two legs form a full positive+negative discrimination on the patent's central
spectroscopic claim, still tested on the patent's own terms.

Framing is unchanged from the rest of the lab: **triage, not proof.** Every verdict is
clamped to evidence Level ≤ 2 (`LAB_CEILING`). The screen is a ruler built from cited
literature band positions; the verdict is whatever the observed doublet lands on. The
validation layer must remain able to fail: a doublet that matches **no** cited contaminant
within tolerance, with metal–metal already excluded, returns `unmatched` — a genuinely
anomalous result that would *support* the patent. No ranking is written into this spec as
foregone; the actual ranked output is recorded in `docs/patent-claim-tests.md` only after
the screen is run.

## Non-goals (YAGNI)

- No new EPW / DFT compute. These are closed-form screens reusing the harmonic relation.
- No wet-chemistry kinetics or surface-coverage modeling — band positions are taken from
  literature, not derived from a reaction model.
- No attempt to identify the *actual* Hudson sample composition (unavailable); the screen
  tests only whether the *published doublet* is consistent with known contaminant bands.
- No network egress, no telemetry, loopback-only — unchanged lab invariants.

## Architecture

New module `src/orme_lab/ir_contaminant.py`, sibling to `ir_signature.py`, mirroring the
existing frozen-dataclass + hedged `explain()` result pattern. The two modules compose at
the web/docs layer, **not** by cross-import: `ir_signature.py` remains the standalone
negative leg, `ir_contaminant.py` the standalone positive leg, each testable in isolation.
The one shared primitive — `wavenumber(k, mu)` — already lives in `ir_signature.py` and is
imported by the layer-2 physics model.

```
src/orme_lab/
  ir_contaminant.py     # NEW — contaminant reference library + match screen + coupled-oscillator model
  ir_signature.py       # unchanged — negative leg (metal–metal exclusion)
tests/
  test_ir_contaminant.py      # NEW
  test_patent_web_parity.py   # extended — JS contaminant table pinned to Python table
web/
  patent_tests.js       # extended — IR widget shows top contaminant match; mirrors _CONTAMINANTS
docs/
  patent-claim-tests.md # extended — contaminant-control findings section, authored AFTER the run
research-wiki/prior-art/
  ir-contaminant-bands.md     # NEW — sourced band positions per candidate (the §4 gate)
```

## Layer 1 — contaminant-match screen

**`ContaminantBand`** (frozen dataclass): `name`, `category` ∈ {`"route_derived"`,
`"standard"`}, lower-line band `(lo_min, lo_max)`, upper-line band `(hi_min, hi_max)`,
characteristic splitting range `(d_min, d_max)`, `source` (citation string). All band edges
are **placeholders until the §4 source gate fills them**; none is written from recollection.

**Candidate roster** (broad standard set; route-derived tier first):

| category      | species                     | why present (mechanism)                          |
|---------------|-----------------------------|--------------------------------------------------|
| route_derived | nitrate NO₃⁻                | aqua regia / HNO₃ processing                      |
| route_derived | carbonate CO₃²⁻             | atmospheric CO₂ + base; NaCl/Na₂CO₃ fusion        |
| route_derived | carboxylate / acetate COO⁻  | organic residue                                  |
| route_derived | water bend δ(H₂O)           | adsorbed/occluded water                          |
| standard      | alkyl C–H scissor/bend pair | ubiquitous organic contamination                 |
| standard      | ammonium NH₄⁺               | ammonia/ammonium salts                           |
| standard      | sulfate SO₄²⁻               | sulfuric-acid processing residue                 |
| standard      | silicone / PDMS             | ubiquitous lab-ware contamination                |

**`screen_contaminants(lines_cm)`** — for each candidate compute a normalized residual on
(a) whether ν_lo falls in `(lo_min, lo_max)`, (b) whether ν_hi falls in `(hi_min, hi_max)`,
and (c) whether Δ = ν_hi − ν_lo falls in `(d_min, d_max)`. The splitting is the primary
discriminator: it rules candidates in or out largely independent of absolute position
(the patent doublets have Δ≈61–63 cm⁻¹). Score = sum of normalized band-width distances
(0 = dead centre of every band). Returns **`ContaminantMatchResult`**: `observed_lines_cm`,
`splitting_cm`, `ranked` (list of `(name, score)` ascending), `verdict`, `evidence_level`
(≤2), and the top candidate's `source`.

**Verdict** ∈ {`tight_match`, `plausible_match`, `unmatched`}:
- `tight_match` — both lines and the splitting fall inside a candidate's cited ranges.
- `plausible_match` — within a documented tolerance (e.g. splitting matches, one line
  marginally outside its band); the specific tolerance is set in the plan.
- `unmatched` — no candidate within tolerance. Combined with metal–metal exclusion from
  `ir_signature.py`, this is the anomalous branch that would support the patent. Exercised
  by a synthetic test doublet so the screen is provably able to return it.

## Layer 2 — coupled-oscillator physics model

For whichever candidate ranks **top at runtime** (not pre-chosen), a worked closed-form
forward model. A symmetric XY₂/XY₃-type group's doublet is the symmetric/antisymmetric
split of two coupled equivalent bond stretches:

    ν± = 1302.8 · √((k ± k′) / μ)

with k the bond force constant, k′ the interaction (coupling) force constant, μ the reduced
mass of one oscillator. `coupled_stretch(k, k_int, mu) → (ν_sym, ν_asym)` forward;
`back_out_coupling(ν_lo, ν_hi, mu) → (k, k_int)` inverse. Applied to the top match's cited
μ, it reports whether the observed doublet implies **physical** k and k′ for that functional
group — a second, independent falsification lever. Deterministic and closed-form; reuses the
existing harmonic constant 1302.8. If the top match is not a symmetric two-oscillator group
(e.g. a single-band water bend), the model reports "not applicable — doublet is not a
coupled-stretch pair for this species," which is itself informative.

## Layer 0 (mandatory) — source-verification gate

**No band value enters `_CONTAMINANTS` from recollection.** Ordered before implementation:

1. `prior-art-cartographer` sources each candidate's IR band positions and characteristic
   splitting from primary references — Nakamoto, *Infrared and Raman Spectra of Inorganic
   and Coordination Compounds* (canonical for nitrate / carbonate / carboxylate metal-complex
   bands and their coordination-dependent splittings); Socrates, *Infrared and Raman
   Characteristic Group Frequencies* (organics, C–H, silicone); NIST Chemistry WebBook —
   recorded to `research-wiki/prior-art/ir-contaminant-bands.md` with page/table references.
2. `citation-auditor` verifies every number against its cited source before it is committed.
3. Each `_CONTAMINANTS` row carries an inline `source` comment.

If a candidate's bands cannot be sourced confidently, that candidate is dropped and the
omission recorded — honest absence over confident filler. This gate is the charter's
no-fabricated-citations floor expressed as a build step; the plan sequences it first.

## Web integration

Extend `irVerdict` in `web/patent_tests.js`: beneath the existing metal–metal exclusion
line, show the top contaminant match and its splitting comparison. Mirror `_CONTAMINANTS`
as a JS array (name + four band edges + two splitting edges + category). The parity test
`test_patent_web_parity.py` grows a case asserting the JS array equals the Python table
row-for-row, so the site cannot drift from the authoritative screen. The layer-2 physics
model stays Python/docs-only (not surfaced as a live widget) to bound web scope.

## Testing

- `test_ir_contaminant.py`: residual/score arithmetic on hand-worked bands; splitting-based
  discrimination (a candidate with the right Δ ranks above one with wrong Δ at equal
  position error); the patent doublets' ranked result and verdict; the synthetic `unmatched`
  doublet (falsification lever); coupled-oscillator forward/inverse round-trip against a
  hand-worked (k, k′, μ); the not-applicable branch; `evidence_level ≤ 2` on every verdict.
- `test_patent_web_parity.py`: JS `_CONTAMINANTS` mirror equals the Python table.

## Invariants preserved

Evidence ceiling 2 on every verdict; deterministic (no time/RNG/order-dependent iteration —
ranking sorts by a total key with a stable tiebreak on name); no network egress; loopback-only;
no telemetry; no fabricated citations (every band value carries a source comment and is
verified by the §4 gate before commit); neutral-outcomes discipline (ranking recorded only
after the screen runs, and the screen is provably able to return `unmatched`).

## Open items for the writing-plans step

- Exact `plausible_match` tolerance (band-width multiplier) and the score normalization
  constant.
- Whether the ranking tiebreak is name-alphabetical or category-then-name (default:
  category first — route-derived outranks standard at equal score — then name).
- Final candidate roster after the §4 gate (a candidate with unsourceable bands is dropped).
