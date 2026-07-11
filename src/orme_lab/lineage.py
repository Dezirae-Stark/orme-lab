"""Material lineage / provenance for the Hudson Claim Ledger.

A claim observed on a specimen attaches to a MATERIAL STATE, not automatically to the
precursor: after annealing / hydration / irradiation / field treatment the resulting state
is a new lineage node (a new processing_history entry + fingerprint). Integrated Hudson
evidence must come from ONE lineage (same specimen > same batch > same lineage), never from
unrelated specimens. At pure-simulation level each computational candidate is its own
singleton lineage; real lab evidence carries explicit IDs.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from enum import IntEnum


class IntegrationLevel(IntEnum):
    """Strength of the same-material claim, strongest first."""
    SAME_SPECIMEN = 3   # the exact physical aliquot received every test
    SAME_BATCH = 2      # aliquots of one homogeneous batch (minimum for integrated evidence)
    SAME_LINEAGE = 1    # independent batches, same recipe, matching fingerprints
    NONE = 0            # unrelated / unknown


@dataclass(frozen=True)
class MaterialLineage:
    material_family_id: str
    preparation_batch_id: str
    aliquot_id: str
    processing_history: tuple[str, ...] = ()
    characterization_fingerprint: str = ""
    integration_level: IntegrationLevel = IntegrationLevel.SAME_SPECIMEN


def singleton_lineage(candidate_id: str) -> MaterialLineage:
    """A computational candidate is its own singleton lineage (family = batch = aliquot)."""
    return MaterialLineage(candidate_id, candidate_id, candidate_id, (),
                           candidate_id, IntegrationLevel.SAME_SPECIMEN)


def lineage_key(lin: MaterialLineage) -> str:
    """Batch-level grouping key (the minimum acceptable for integrated evidence).

    Includes the PROCESSING STATE: a claim observed after annealing/hydration/irradiation/field
    treatment attaches to the RESULTING material state, not the precursor, so an aliquot with a
    non-empty processing_history keys to a DISTINCT lineage from the untreated batch — evidence
    from the precursor and the treated product must not be stitched together. Untreated aliquots
    (empty history) share the bare family/batch key so genuine same-batch aliquots still combine."""
    base = f"{lin.material_family_id}/{lin.preparation_batch_id}"
    if lin.processing_history:
        return base + "/" + ">".join(lin.processing_history)
    return base


def group_by_lineage(items: tuple[tuple[MaterialLineage, object], ...]) -> dict[str, list]:
    """Group (lineage, payload) pairs by batch-level key. Deterministic (sorted keys)."""
    groups: dict[str, list] = {}
    for lin, payload in items:
        groups.setdefault(lineage_key(lin), []).append(payload)
    return dict(sorted(groups.items()))


def after_treatment(lin: MaterialLineage, treatment: str, fingerprint: str) -> MaterialLineage:
    """The resulting material state after a treatment: a NEW lineage node with the treatment
    appended to processing_history and an updated fingerprint. The original is unchanged."""
    return replace(lin, processing_history=lin.processing_history + (treatment,),
                   characterization_fingerprint=fingerprint)
