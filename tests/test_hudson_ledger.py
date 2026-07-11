"""Tests for the Hudson Claim Ledger."""
from __future__ import annotations

from orme_lab.hudson_ledger import (
    ClaimRecord,
    ClaimStatus,
    HudsonClaimId,
    MeasuredEvidence,
    ReplicationEvidence,
    Route,
)


def test_status_ladder_is_ordered():
    assert ClaimStatus.CANDIDATE < ClaimStatus.LEAD < ClaimStatus.SUPPORTED < ClaimStatus.INDEPENDENTLY_REPLICATED


def test_claim_ids_cover_all_eight():
    assert [c.value for c in HudsonClaimId] == [f"HC-0{i}" for i in range(1, 9)]


def test_records_construct():
    r = ClaimRecord(HudsonClaimId.HC_07, "superconductivity", "R->0 + magnetic + thermo",
                    "ionic/percolation/artifact", ClaimStatus.LEAD, 2, Route.CONVENTIONAL, True, None, "note")
    assert r.status is ClaimStatus.LEAD and r.route is Route.CONVENTIONAL
    rep = ReplicationEvidence(3, 2, True, True, True)
    assert rep.n_batches == 3
    m = MeasuredEvidence()
    assert m.zero_resistance is False and m.optical_result is None
