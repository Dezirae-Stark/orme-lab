import math
import pytest
from orme_lab.elements import get_element
from orme_lab.geometry import make_monomer, make_compact_cluster
from orme_lab.spin_states import high_spin_state, low_spin_state
from orme_lab.epw.approximant import build_approximant, ApproximantUndefined


def test_monomer_raises_approximant_undefined():
    au = get_element("Au")
    with pytest.raises(ApproximantUndefined):
        build_approximant(au, make_monomer(au), high_spin_state(au))


def test_fcc_element_lattice_constant_from_nn():
    au = get_element("Au")
    geom = make_compact_cluster(au, 13)
    d = geom.nearest_neighbor_distance
    ap = build_approximant(au, geom, high_spin_state(au))
    assert ap.bravais == "fcc" and ap.ibrav == 2
    assert math.isclose(ap.a_angstrom, d * math.sqrt(2), rel_tol=1e-9)
    assert ap.c_over_a is None


def test_hcp_element_uses_ideal_c_over_a():
    os_el = get_element("Os")
    geom = make_compact_cluster(os_el, 13)
    ap = build_approximant(os_el, geom, high_spin_state(os_el))
    assert ap.bravais == "hcp" and ap.ibrav == 4
    assert math.isclose(ap.c_over_a, 1.6329931619, rel_tol=1e-9)


def test_high_spin_is_polarized_low_spin_is_not():
    os_el = get_element("Os")
    geom = make_compact_cluster(os_el, 13)
    hi = build_approximant(os_el, geom, high_spin_state(os_el))
    lo = build_approximant(os_el, geom, low_spin_state(os_el))
    assert hi.spin_polarized is True and hi.starting_magnetization > 0.0
    assert lo.spin_polarized is (low_spin_state(os_el).unpaired_electrons > 0)
    assert 0.0 <= hi.starting_magnetization <= 1.0
