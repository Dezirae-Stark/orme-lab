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
    assert int(EvidenceLevel.CONCEPT) == 0
    assert int(EvidenceLevel.ESTABLISHED_PHENOMENON) == 6
    values = [int(l) for l in EvidenceLevel]
    assert values == sorted(values) == list(range(7))


def test_lab_ceiling_is_simulation_candidate():
    # Nothing in this repo can exceed a simulation-candidate artifact.
    assert LAB_CEILING == EvidenceLevel.SIMULATION_CANDIDATE


def test_candidate_level_never_reaches_observation():
    survives = candidate_evidence_level(ruled_out=False)
    ruled = candidate_evidence_level(ruled_out=True)
    # a survivor yields at most a laboratory PREDICTION, never an observation
    assert survives == EvidenceLevel.LABORATORY_PREDICTION
    assert survives < EvidenceLevel.INITIAL_OBSERVATION
    assert ruled == EvidenceLevel.SIMULATION_CANDIDATE


def test_badge_format():
    b = badge(EvidenceLevel.SIMULATION_CANDIDATE)
    assert b == "Level 2/6 — simulation candidate"
    assert "simulation candidate" in describe(EvidenceLevel.SIMULATION_CANDIDATE)
