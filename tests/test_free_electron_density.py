from orme_lab.electromagnetic_coherence import free_electron_density, plasmon_energy_ev
from orme_lab.elements import get_element


def test_gold_density_in_metal_range():
    n = free_electron_density(get_element("Au"))
    assert 5e28 < n < 2e29           # textbook metal free-electron density
    # and it yields a physically sane bulk plasmon energy
    assert 4.0 < plasmon_energy_ev(n) < 15.0


def test_palladium_is_dark_no_conduction_electrons():
    # Pd is [Kr]4d10 -> s_electrons == 0 -> free-electron model gives n = 0.
    assert free_electron_density(get_element("Pd")) == 0.0


def test_density_is_positive_for_s1_metals():
    for sym in ("Ag", "Pt", "Ir", "Os", "Rh", "Ru"):
        assert free_electron_density(get_element(sym)) > 0.0
