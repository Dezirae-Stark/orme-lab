"""Tests for the material-lineage / provenance model."""
from __future__ import annotations

from orme_lab.lineage import (
    IntegrationLevel,
    MaterialLineage,
    after_treatment,
    group_by_lineage,
    lineage_key,
    singleton_lineage,
)


def test_singleton_lineage_is_its_own_family_batch_aliquot():
    lin = singleton_lineage("Ir/compact13/high_spin")
    assert lin.material_family_id == lin.preparation_batch_id == lin.aliquot_id == "Ir/compact13/high_spin"
    assert lin.integration_level is IntegrationLevel.SAME_SPECIMEN
    assert lin.processing_history == ()


def test_group_by_lineage_groups_aliquots_of_one_batch():
    a = MaterialLineage("famA", "batch1", "aliquot1", (), "fpA", IntegrationLevel.SAME_BATCH)
    b = MaterialLineage("famA", "batch1", "aliquot2", (), "fpA", IntegrationLevel.SAME_BATCH)
    c = MaterialLineage("famA", "batch2", "aliquot3", (), "fpB", IntegrationLevel.SAME_BATCH)
    groups = group_by_lineage(((a, "x"), (b, "y"), (c, "z")))
    assert groups["famA/batch1"] == ["x", "y"]      # same batch grouped
    assert groups["famA/batch2"] == ["z"]           # different batch separate
    assert list(groups.keys()) == sorted(groups.keys())   # deterministic order


def test_after_treatment_appends_history_and_is_a_new_state():
    lin = singleton_lineage("Ir/mono/hs")
    treated = after_treatment(lin, "anneal-600C", "fp-annealed")
    assert treated.processing_history == ("anneal-600C",)
    assert treated.characterization_fingerprint == "fp-annealed"
    assert lin.processing_history == ()             # original unchanged (frozen)


def test_treated_state_is_a_distinct_lineage_not_merged_with_precursor():
    # a claim on the treated product must NOT be stitched to the untreated precursor
    lin = singleton_lineage("Ir/mono/hs")
    treated = after_treatment(lin, "anneal-600C", "fp2")
    assert lineage_key(lin) != lineage_key(treated)
    groups = group_by_lineage(((lin, "precursor"), (treated, "product")))
    assert len(groups) == 2                          # two distinct material states, not merged
