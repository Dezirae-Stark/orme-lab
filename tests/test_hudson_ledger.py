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


from orme_lab.config import DEFAULT_CONFIG
from orme_lab.hudson_ledger import (
    HudsonIdentity,
    NONMETALLIC_ELEMENTAL,
    assess_hc01,
    g_identity_established,
)
from orme_lab.identity import IdentityWitness

TH = DEFAULT_CONFIG.thresholds


def test_identity_established_is_phase_agnostic():
    # a fully-characterized METAL is "established" (we know what it is) even though it is NOT Hudson's state
    metal = IdentityWitness("Ir", "metallic", "bulk", 0.0, ())
    assert g_identity_established(metal) is True
    hc01 = assess_hc01(metal, "Ir", TH)
    assert hc01.status.name in ("CANDIDATE",)            # metallic -> HC-01 not supported (ruled against)


def test_hc01_supported_only_for_nonmetallic_elemental():
    hud = IdentityWitness("Ir", NONMETALLIC_ELEMENTAL, "monatomic", 0.0, ())
    hc01 = assess_hc01(hud, "Ir", TH)
    assert hc01.status >= __import__("orme_lab.hudson_ledger", fromlist=["ClaimStatus"]).ClaimStatus.PROVISIONALLY_SUPPORTED
    # an oxide/salt is the ruled-out mundane alternative
    oxide = IdentityWitness("IrO2", "oxide", "nanoparticle", 4.0, ())
    assert assess_hc01(oxide, "Ir", TH).status.name == "CANDIDATE"


def test_identity_unresolved_when_uncharacterized():
    blank = IdentityWitness(None, None, None, None, ())
    assert g_identity_established(blank) is False
