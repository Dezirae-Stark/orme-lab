def test_candidate_record_carries_branch_b_fields():
    from orme_lab.config import DEFAULT_CONFIG
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate

    el = get_element("Au")                                     # Branch B is ON by default
    rec = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                             high_spin_state(el), DEFAULT_CONFIG)
    # Branch B fields present and independent of the SC verdict
    assert rec.hudson_regime in ("weak", "strong", "ultrastrong")
    assert isinstance(rec.hudson_supported_levels, tuple)
    assert rec.hudson_highest_claim >= 0
    # default (no lab inputs): transport (5) and magnetism (7) cannot be supported
    assert 5 not in rec.hudson_supported_levels
    assert 7 not in rec.hudson_supported_levels
    # csv row renders the new fields without error
    row = rec.as_csv_row()
    assert "hudson_regime" in row and "hudson_supported_levels" in row


def test_branch_b_can_be_disabled():
    # Branch B is central and ON by default; setting compute_hudson_optical=False recovers
    # the lightweight SC-only path (Branch-B fields left at their record defaults).
    from dataclasses import replace
    from orme_lab.config import DEFAULT_CONFIG
    from orme_lab.elements import get_element
    from orme_lab.geometry import make_compact_cluster
    from orme_lab.spin_states import high_spin_state
    from orme_lab.pipeline import evaluate_candidate

    cfg = replace(DEFAULT_CONFIG, compute_hudson_optical=False)
    el = get_element("Au")
    rec = evaluate_candidate(el, make_compact_cluster(el, 13), "high_spin",
                             high_spin_state(el), cfg)
    assert rec.hudson_regime is None and rec.hudson_supported_levels == ()
