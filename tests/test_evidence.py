"""Tests for the evidence hierarchy (charter)."""

from __future__ import annotations

from orme_lab.evidence import (
    EvidenceLevel,
    LAB_CEILING,
    badge,
    candidate_evidence_level,
    describe,
)


def test_levels_are_ordered_0_to_6():
    assert int(EvidenceLevel.SPECULATION) == 0
    assert int(EvidenceLevel.MULTIPLE_REPLICATIONS) == 6
    values = [int(l) for l in EvidenceLevel]
    assert values == sorted(values) == list(range(7))


def test_lab_ceiling_is_computational_simulation():
    # Nothing in this repo can exceed a computational-simulation artifact.
    assert LAB_CEILING == EvidenceLevel.COMPUTATIONAL_SIMULATION


def test_candidate_level_never_reaches_experiment():
    survives = candidate_evidence_level(ruled_out=False)
    ruled = candidate_evidence_level(ruled_out=True)
    # a survivor yields at most a laboratory PREDICTION, never an experiment
    assert survives == EvidenceLevel.LABORATORY_PREDICTION
    assert survives < EvidenceLevel.SINGLE_EXPERIMENT
    assert ruled == EvidenceLevel.COMPUTATIONAL_SIMULATION


def test_badge_format():
    b = badge(EvidenceLevel.COMPUTATIONAL_SIMULATION)
    assert b == "Level 2/6 — computational simulation"
    assert "computational simulation" in describe(EvidenceLevel.COMPUTATIONAL_SIMULATION)
