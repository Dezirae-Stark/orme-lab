"""Superconductivity plausibility scoring.

This is the module most in danger of overclaiming, so it is built to make
overclaiming structurally hard.

The plausibility score is an **AND-gate of necessary conditions**, not a
weighted average. A bulk superconductor requires ALL of:

    1. nonzero inter-unit coupling        (hypotheses 4, 5)
    2. a sufficient carrier/coherence proxy (paired mobile carriers exist)
    3. magnetic-field tolerance            (survives a real field; hypothesis 7)
    4. structural stability                (the state persists long enough)
    5. a measurable predicted observable   (the claim is falsifiable at all)

If any gate fails, plausibility is 0 -- because these are *necessary* conditions
and no surplus in one can compensate for the absence of another. Only when all
gates pass does the module report a bounded, positive plausibility (the product
of the normalized margins). Even then the number is explicitly a "not ruled out"
score, NOT a probability that the material is superconducting.

    TODO(ab-initio): the only path to a real plausibility estimate runs through
    a computed electron-phonon coupling (EPW/Eliashberg) or an explicit pairing
    mechanism. This toy score cannot and does not establish superconductivity.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import ModelThresholds


@dataclass(frozen=True)
class PlausibilityGate:
    """Result of one necessary-condition gate."""

    name: str
    value: float
    threshold: float

    @property
    def passed(self) -> bool:
        return self.value >= self.threshold

    @property
    def margin(self) -> float:
        """Normalized headroom above the threshold, in [0, 1]. 0 if failed."""
        if not self.passed:
            return 0.0
        span = 1.0 - self.threshold
        if span <= 0:
            return 1.0
        return min((self.value - self.threshold) / span, 1.0)


@dataclass(frozen=True)
class PlausibilityResult:
    """Full outcome of the superconductivity plausibility evaluation."""

    gates: tuple[PlausibilityGate, ...]
    score: float

    @property
    def all_passed(self) -> bool:
        return all(g.passed for g in self.gates)

    @property
    def failed_gates(self) -> list[str]:
        return [g.name for g in self.gates if not g.passed]

    def explain(self) -> str:
        """Human-readable verdict, always hedged appropriately."""
        if not self.all_passed:
            return (
                f"RULED OUT as bulk SC candidate. Failed necessary condition(s): "
                f"{', '.join(self.failed_gates)}."
            )
        return (
            f"NOT RULED OUT (screening score={self.score:.3f} — a triage score, "
            f"not a probability). All necessary conditions met; this is a screening "
            f"signal, not evidence of superconductivity. Requires ab-initio + "
            f"experimental confirmation."
        )


def carrier_coherence_proxy(coupling_score: float, anisotropy_score: float) -> float:
    """Toy proxy for available paired/coherent carriers, in [0, 1].

    Rationale: mobile carriers need delocalization (tracked by coupling), but
    extreme density anisotropy (a 1D needle) tends to *localize* carriers and
    invite instabilities (Peierls, etc.). So the proxy rewards coupling and
    penalizes runaway anisotropy. A middling ('rice-bean') anisotropy is not
    penalized much; a needle is.
    """
    localization_penalty = max(0.0, anisotropy_score - 0.75)  # only needles hurt
    return max(0.0, coupling_score * (1.0 - localization_penalty))


def superconductivity_plausibility_score(
    coupling_score: float,
    carrier_proxy: float,
    field_suppression: float,
    structural_stability: float,
    observable_signal: float,
    thresholds: ModelThresholds,
) -> PlausibilityResult:
    """Evaluate the five necessary-condition gates and combine them.

    Parameters
    ----------
    coupling_score:
        Inter-unit coupling (from :mod:`orme_lab.coupling`).
    carrier_proxy:
        Carrier/coherence proxy (see :func:`carrier_coherence_proxy`).
    field_suppression:
        Field-survival factor in [0,1] (from :mod:`orme_lab.magnetic_field`).
    structural_stability:
        Structural-stability proxy in [0,1] (pipeline supplies this).
    observable_signal:
        Magnitude of the strongest predicted observable in [0,1].
    thresholds:
        The necessary-condition floors.

    Returns
    -------
    PlausibilityResult
        Contains every gate's pass/fail and the combined score. The score is the
        product of gate margins when all pass, else 0.0.
    """
    gates = (
        PlausibilityGate("coupling", coupling_score, thresholds.min_coupling_for_bulk),
        PlausibilityGate("carriers", carrier_proxy, thresholds.min_carrier_proxy),
        PlausibilityGate("field_tolerance", field_suppression, thresholds.min_field_tolerance),
        PlausibilityGate("structural_stability", structural_stability, thresholds.min_structural_stability),
        PlausibilityGate("observable_signal", observable_signal, thresholds.min_observable_signal),
    )

    if not all(g.passed for g in gates):
        return PlausibilityResult(gates=gates, score=0.0)

    # All necessary conditions met: combine margins multiplicatively so the
    # weakest link dominates. This can never exceed 1.0 and is only positive
    # when every gate passed.
    score = 1.0
    for g in gates:
        score *= g.margin
    return PlausibilityResult(gates=gates, score=score)
