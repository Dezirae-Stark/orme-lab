"""Evidence hierarchy (ORME Lab charter).

Every claim about a candidate carries an explicit evidence level, so a promising
simulation is never presented as an experimental fact and a single positive
experiment is never treated as established science until it is independently
reproduced. See ``docs/CHARTER.md``.

The unit of confidence is an **independent, instrumented, reproducible
observation** — the witness is a calibrated instrument (ESR, SQUID, XRD, Raman,
neutron scattering, calorimetry), and the requirement is that another laboratory
with comparable equipment reproduces the result under the same conditions.
"""

from __future__ import annotations

from enum import IntEnum


class EvidenceLevel(IntEnum):
    """Standing of a claim, from concept to established phenomenon (the lab's
    signature 0-6 evidence ladder; see ``docs/CHARTER.md``)."""

    CONCEPT = 0                    # concept
    MATHEMATICAL_CONSISTENCY = 1   # internally consistent math
    SIMULATION_CANDIDATE = 2       # a candidate reproduced in simulation
    LABORATORY_PREDICTION = 3      # a concrete, measurable prediction
    INITIAL_OBSERVATION = 4        # first laboratory observation
    INDEPENDENT_REPLICATION = 5    # replicated by an independent lab
    ESTABLISHED_PHENOMENON = 6     # established phenomenon (peer-scrutinized)


_LABELS = {
    EvidenceLevel.CONCEPT: "concept",
    EvidenceLevel.MATHEMATICAL_CONSISTENCY: "mathematical consistency",
    EvidenceLevel.SIMULATION_CANDIDATE: "simulation candidate",
    EvidenceLevel.LABORATORY_PREDICTION: "laboratory prediction",
    EvidenceLevel.INITIAL_OBSERVATION: "initial observation",
    EvidenceLevel.INDEPENDENT_REPLICATION: "independent replication",
    EvidenceLevel.ESTABLISHED_PHENOMENON: "established phenomenon",
}

MAX_LEVEL = EvidenceLevel.ESTABLISHED_PHENOMENON

#: The highest level anything this repository can produce. The toy pipeline is a
#: simulation-candidate artifact; reaching higher requires a real lab.
LAB_CEILING = EvidenceLevel.SIMULATION_CANDIDATE


def describe(level: EvidenceLevel) -> str:
    """Human-readable label for a level."""
    return _LABELS[EvidenceLevel(level)]


def badge(level: EvidenceLevel) -> str:
    """Compact status string, e.g. 'Level 2/6 — computational simulation'."""
    lvl = EvidenceLevel(level)
    return f"Level {int(lvl)}/{int(MAX_LEVEL)} — {describe(lvl)}"


def candidate_evidence_level(ruled_out: bool) -> EvidenceLevel:
    """Evidence level for a screened candidate.

    A ruled-out candidate rests on simulation (Level 2 — simulation candidate):
    the model has shown, in simulation, that a necessary condition fails. A
    surviving ('not ruled out') candidate additionally yields a **laboratory
    prediction** (Level 3) — it tells you which measurement would be decisive —
    but it asserts nothing at Level 4+; that requires a real observation and,
    ultimately, independent replication.

    Note: this function may return LABORATORY_PREDICTION (Level 3), but the
    pipeline clamps the recorded ``evidence_level`` to ``LAB_CEILING``
    (Level 2) via ``min(...)`` — see ``pipeline.evaluate_candidate``.
    """
    return EvidenceLevel.LABORATORY_PREDICTION if not ruled_out else EvidenceLevel.SIMULATION_CANDIDATE
