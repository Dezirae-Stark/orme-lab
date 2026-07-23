from orme_lab.epw.qe_input import scf_input, ph_input, epw_input
from orme_lab.epw.config import EPWConfig
from orme_lab.epw.approximant import PeriodicApproximant


def _cfg():
    return EPWConfig(pseudopotentials=(("Os", "Os.upf"),))


def _fcc():
    return PeriodicApproximant("Au", "fcc", 4.0, None, False, 0.0, "Au-fcc-compact13")


def _hcp_polarized():
    return PeriodicApproximant("Os", "hcp", 2.7, 1.6329931619, True, 0.4, "Os-hcp-compact13")


def test_scf_has_required_namelists_and_ibrav():
    deck = scf_input(_fcc(), _cfg(), "orme_Au")
    assert "&control" in deck and "&system" in deck and "&electrons" in deck
    assert "ibrav = 2" in deck
    assert "calculation = 'scf'" in deck


def test_spin_polarized_sets_nspin_and_magnetization():
    deck = scf_input(_hcp_polarized(), _cfg(), "orme_Os")
    assert "nspin = 2" in deck
    assert "starting_magnetization(1) = 0.4" in deck
    assert "ibrav = 4" in deck and "celldm(3)" in deck


def test_non_polarized_omits_nspin():
    deck = scf_input(_fcc(), _cfg(), "orme_Au")
    assert "nspin" not in deck


def test_ph_and_epw_reference_prefix_and_meshes():
    ph = ph_input(_hcp_polarized(), _cfg(), "orme_Os")
    assert "orme_Os" in ph and "4 4 4" in ph          # q_coarse
    epw = epw_input(_hcp_polarized(), _cfg(), "orme_Os")
    assert "orme_Os" in epw and "nkf1" in epw and "a2f" in epw.lower()


def test_all_four_decks_share_one_prefix():
    ap = _hcp_polarized(); cfg = _cfg(); p = "orme_shared_prefix"
    from orme_lab.epw.qe_input import scf_input, nscf_input, ph_input, epw_input
    for deck in (scf_input(ap, cfg, p), nscf_input(ap, cfg, p), ph_input(ap, cfg, p), epw_input(ap, cfg, p)):
        assert p in deck


def test_projwfc_input_has_namelist_and_prefix():
    from orme_lab.epw.qe_input import projwfc_input
    deck = projwfc_input(_fcc(), _cfg(), "orme")
    assert "&projwfc" in deck.lower()
    assert "prefix" in deck and "orme" in deck
    assert "filproj" in deck
