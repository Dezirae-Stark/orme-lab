from orme_lab.lab_loop.hypotheses import HYPOTHESES, validate_scope
from orme_lab.lab_loop.avenue import (
    Avenue, ActionSpec, Tier, FalsificationCondition, Comparator,
)


def _av(hyp, elements=("Ir",), geoms=("dimer",)):
    return Avenue(
        id="x", tier=Tier.TIER1, description="d", targeted_hypothesis=hyp,
        action=ActionSpec(elements, geoms, ("high_spin",), 0.0, 298.15, False, False, None),
        falsification=FalsificationCondition("max_anisotropy", Comparator.LT, 0.05),
        predictor_invariants=("sc_lambda",), provenance="t",
    )


def test_registry_has_scoped_variants_not_bare_h1_h3():
    for h in ("H1-open-shell", "H1-closed-shell", "H3-cluster", "H3-monomer"):
        assert h in HYPOTHESES
    assert "H1" not in HYPOTHESES
    assert "H3" not in HYPOTHESES
    for h in ("H2", "H4", "H5", "H6", "H7", "H12", "H16"):
        assert h in HYPOTHESES


def test_h1_element_scope():
    assert validate_scope(_av("H1-open-shell", elements=("Ir",)))[0] is True
    assert validate_scope(_av("H1-open-shell", elements=("Os", "Pt", "Rh", "Ru")))[0] is True
    assert validate_scope(_av("H1-open-shell", elements=("Pd",)))[0] is False        # closed
    assert validate_scope(_av("H1-closed-shell", elements=("Pd", "Au", "Ag")))[0] is True
    assert validate_scope(_av("H1-closed-shell", elements=("Ir",)))[0] is False       # open


def test_h1_mixed_panel_fails_not_all_match():
    ok, reason = validate_scope(_av("H1-open-shell", elements=("Ir", "Pd")))
    assert ok is False and "Pd" in reason


def test_h3_geometry_scope():
    assert validate_scope(_av("H3-cluster", geoms=("compact_cluster",)))[0] is True
    assert validate_scope(_av("H3-cluster", geoms=("monomer",)))[0] is False
    assert validate_scope(_av("H3-monomer", geoms=("monomer",)))[0] is True
    assert validate_scope(_av("H3-monomer", geoms=("dimer",)))[0] is False


def test_unscoped_hypothesis_always_passes():
    assert validate_scope(_av("H5", elements=("Pd",), geoms=("monomer",))) == (True, "")


def test_reason_present_on_mismatch():
    ok, reason = validate_scope(_av("H1-closed-shell", elements=("Ir",)))
    assert ok is False and reason and "H1-closed-shell" in reason
