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
    """Standing of a claim, from concept to independently replicated fact."""

    SPECULATION = 0             # speculation / concept
    MATHEMATICAL_CONSISTENCY = 1  # internally consistent math
    COMPUTATIONAL_SIMULATION = 2  # reproduced in simulation
    LABORATORY_PREDICTION = 3     # a concrete, measurable prediction
    SINGLE_EXPERIMENT = 4         # one reproducible experiment
    INDEPENDENT_REPLICATION = 5   # replicated by an independent lab
    MULTIPLE_REPLICATIONS = 6     # multiple independent replications + peer scrutiny


_LABELS = {
    EvidenceLevel.SPECULATION: "speculation / concept",
    EvidenceLevel.MATHEMATICAL_CONSISTENCY: "mathematical consistency",
    EvidenceLevel.COMPUTATIONAL_SIMULATION: "computational simulation",
    EvidenceLevel.LABORATORY_PREDICTION: "laboratory prediction",
    EvidenceLevel.SINGLE_EXPERIMENT: "single reproducible experiment",
    EvidenceLevel.INDEPENDENT_REPLICATION: "independent laboratory replication",
    EvidenceLevel.MULTIPLE_REPLICATIONS: "multiple independent replications with peer scrutiny",
}

MAX_LEVEL = EvidenceLevel.MULTIPLE_REPLICATIONS

#: The highest level anything this repository can produce. The toy pipeline is a
#: computational-simulation artifact; reaching higher requires a real lab.
LAB_CEILING = EvidenceLevel.COMPUTATIONAL_SIMULATION


def describe(level: EvidenceLevel) -> str:
    """Human-readable label for a level."""
    return _LABELS[EvidenceLevel(level)]


def badge(level: EvidenceLevel) -> str:
    """Compact status string, e.g. 'Level 2/6 — computational simulation'."""
    lvl = EvidenceLevel(level)
    return f"Level {int(lvl)}/{int(MAX_LEVEL)} — {describe(lvl)}"


def candidate_evidence_level(ruled_out: bool) -> EvidenceLevel:
    """Evidence level for a screened candidate.

    A ruled-out candidate rests on computational simulation (Level 2): the model
    has shown, in simulation, that a necessary condition fails. A surviving
    ('not ruled out') candidate additionally yields a **laboratory prediction**
    (Level 3) — it tells you which measurement would be decisive — but it asserts
    nothing at Level 4+; that requires a real experiment and, ultimately,
    independent replication.
    """
    return EvidenceLevel.LABORATORY_PREDICTION if not ruled_out else EvidenceLevel.COMPUTATIONAL_SIMULATION
