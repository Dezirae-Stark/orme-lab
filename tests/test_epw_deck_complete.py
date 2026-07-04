"""Deck-completeness regression tests. The structure asserted here is what a real
epw.x (5.8.1) requires and what the fcc-Pb reference validated end-to-end
(docs/epw-live-validation.md). These are text/structure checks -- no binaries."""
import os

from orme_lab.elements import get_element
from orme_lab.geometry import make_compact_cluster
from orme_lab.spin_states import low_spin_state
from orme_lab.epw.config import EPWConfig
from orme_lab.epw.approximant import build_approximant
from orme_lab.epw import qe_input as q
from orme_lab.epw.runner import collect_dvscf


def _ap(sym="Pd"):
    el = get_element(sym)
    return build_approximant(el, make_compact_cluster(el, 13), low_spin_state(el))


CFG = EPWConfig(k_coarse=(2, 2, 2), q_coarse=(2, 2, 2))


def test_real_atomic_mass_not_placeholder():
    # Phonon frequencies scale as 1/sqrt(mass); a placeholder mass is a real bug.
    for sym, mass in (("Pd", "106.42"), ("Ir", "192.22"), ("Au", "196.97")):
        deck = q.scf_input(_ap(sym), CFG, "p")
        assert f" {sym} {mass} " in deck
        assert " 1.0 " not in deck            # the old placeholder mass is gone


def test_nscf_uses_full_uniform_grid_not_automatic():
    # EPW needs the FULL uniform coarse grid, not the symmetry-reduced set.
    deck = q.nscf_input(_ap(), CFG, "p")
    assert "K_POINTS crystal" in deck
    assert "K_POINTS automatic" not in deck
    # 2x2x2 -> 8 explicit k-points with equal weights
    assert deck.count("1.25000000e-01") >= 1  # weight 1/8
    kpoint_lines = [ln for ln in deck.splitlines() if ln.strip().startswith("0.")]
    assert len(kpoint_lines) == 8


def test_ph_writes_dvscf_potentials():
    deck = q.ph_input(_ap(), CFG, "p")
    assert "fildvscf = 'dvscf'" in deck
    assert "tr2_ph" in deck
    assert "fildyn = 'p.dyn'" in deck        # {prefix}.dyn convention for collection


def test_epw_deck_has_wannier_and_a2f_block():
    deck = q.epw_input(_ap("Ir"), CFG, "p")
    for key in ("phonselfen = .true.", "wannierize = .true.", "nbndsub =",
                "proj(1) = 'Ir:d'", "proj(2) = 'Ir:s'", "dis_win_max",
                "dvscf_dir = './save'", "amass(1) = 192.22", "a2f = .true.",
                "fsthick", "degaussw"):
        assert key in deck, key


def test_collect_dvscf_gathers_potentials(tmp_path):
    # Mock a completed ph.x scratch dir (parallel/no-XML layout) and check the
    # collection produces the save/ files epw.x reads.
    wd = tmp_path / "run"
    ph0 = wd / "_ph0"
    phsave = ph0 / "p.phsave"
    (ph0 / "p.q_2").mkdir(parents=True)
    phsave.mkdir(parents=True)
    (phsave / "control_ph.xml").write_text(
        "<xml>\n<NUMBER_OF_Q_POINTS>\n2\n</NUMBER_OF_Q_POINTS>\n</xml>\n")
    (wd / "p.dyn1").write_text("dyn q1")
    (wd / "p.dyn2").write_text("dyn q2")
    (ph0 / "p.dvscf1").write_text("dvscf q1")           # q1 lives in _ph0
    (ph0 / "p.q_2" / "p.dvscf1").write_text("dvscf q2")  # q2 in _ph0/p.q_2

    collect_dvscf(str(wd), "p", EPWConfig())

    save = wd / "save"
    assert (save / "p.dvscf_q1").read_text() == "dvscf q1"
    assert (save / "p.dvscf_q2").read_text() == "dvscf q2"
    assert (save / "p.dyn_q1").exists() and (save / "p.dyn_q2").exists()
    assert (save / "p.phsave" / "control_ph.xml").exists()
