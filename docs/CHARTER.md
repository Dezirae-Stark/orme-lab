# ORME Lab — Charter

> **ORME Lab is an open computational research laboratory dedicated to translating
> extraordinary claims into testable scientific hypotheses. We do not begin by
> assuming claims are true or false. We construct models, derive predictions,
> perform simulations, design reproducible experiments, and follow the evidence
> wherever it leads.**

Most discussion of ORME/PGM high-spin superconductivity is trapped between
unquestioning belief and blanket dismissal. This lab deliberately occupies the
rigorous middle ground: a hypothesis is a starting point, not a conclusion, and
its standing is set by evidence — not by how remarkable or how fringe it sounds.

## Principles

- **Hypotheses are welcome.** Extraordinary claims are admitted as hypotheses to
  be modeled, not gatekept out of the conversation.
- **Evidence is required.** A hypothesis earns standing only by clearing
  evidence levels (below). Confidence is not evidence.
- **Negative results are valuable.** Ruling a pathway out under known physics is
  a real result and is recorded as such, not buried.
- **Unexpected results are investigated rigorously**, not amplified. A surprise
  raises the bar for scrutiny, it does not lower it.
- **Reproducibility is the standard for confidence.** The unit of belief is an
  **independent, instrumented, reproducible observation** — see below.

## Independent, instrumented, reproducible observations

Earlier framings of this project spoke of "physical eyewitness reproducibility."
The correct, broader standard is **independent, instrumented, reproducible
observations**. Most of the phenomena that would matter here are not visible to
the eye — the witness is a *calibrated instrument*, and the requirement is that
another laboratory, using comparable equipment, reproduces the same result under
the same conditions. Representative instrumented witnesses:

- Electron spin resonance (ESR/EPR)
- SQUID magnetometry (Meissner screening, susceptibility)
- X-ray diffraction (phase / structure — rule out oxide/hydroxide/salt)
- Raman spectroscopy
- Neutron scattering
- Specific-heat calorimetry (the thermodynamic transition at T_c)

## Evidence hierarchy

Every hypothesis, and every claim about a candidate, carries an explicit level.
A promising simulation is not presented as an experimental fact; a single
positive experiment is not treated as established science until others reproduce
it.

| Level | Evidence |
|:-----:|----------|
| 0 | Concept |
| 1 | Mathematical consistency |
| 2 | Simulation candidate |
| 3 | Laboratory prediction |
| 4 | Initial observation |
| 5 | Independent replication |
| 6 | Established phenomenon |

**Where this lab currently sits: Level 2 (simulation candidate) — and, for the
toy models, the low end of it.** Everything the pipeline emits is a Level-2
artifact at most. The `superconductivity` gate producing "NOT RULED OUT" moves a
candidate from Level 0/1 toward a Level-3 *laboratory prediction* (which
measurement to run), but it never asserts anything at Level 4+. Reaching Levels
4–6 requires leaving this repository for a real laboratory and independent
replication.

The evidence level is encoded in `src/orme_lab/evidence.py` and surfaced in the
pipeline verdicts and the interactive lab, so the current status of any result is
never ambiguous. See also `hypothesis_matrix.md` (every claim as a falsifiable
hypothesis) and `validation_tests.md` (the discriminating experiments).
