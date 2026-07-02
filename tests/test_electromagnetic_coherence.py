"""Tests for the electromagnetic-coherence module (H12 / H16).

These encode the module's core commitments:

* plasmon energy is a sensible few-eV scale for metal-like densities,
* anisotropy splits the plasmon into longitudinal (down) and transverse (up),
* strong light-matter coupling is required for any coherence score,
* a coherent result is explicitly NOT a superconductivity claim.
"""

from __future__ import annotations

import math

from orme_lab.config import ModelThresholds
from orme_lab.electromagnetic_coherence import (
    ElectromagneticMode,
    anisotropic_plasmon_energies,
    coupling_regime,
    evaluate_em_coherence,
    is_strong_coupling,
    plasmon_energy_ev,
    polariton_coherence_score,
)

TH = ModelThresholds()


def test_plasmon_energy_metal_scale():
    # Metal-like carrier density -> bulk plasmon in the ~1-30 eV range.
    e = plasmon_energy_ev(6.0e28)
    assert 1.0 < e < 30.0


def test_plasmon_energy_zero_for_no_carriers():
    assert plasmon_energy_ev(0.0) == 0.0


def test_anisotropy_splits_plasmon_longitudinal_down_transverse_up():
    base = 5.0
    lo, hi = anisotropic_plasmon_energies(base, anisotropy_score=0.6)
    assert lo < base < hi          # longitudinal red-shifts, transverse blue-shifts
    lo0, hi0 = anisotropic_plasmon_energies(base, anisotropy_score=0.0)
    assert lo0 == base == hi0      # isotropic -> single resonance


def test_strong_coupling_requires_rabi_beating_losses():
    strong = ElectromagneticMode(mode_energy_ev=5.0, coupling_energy_ev=0.5,
                                 cavity_loss_ev=0.1, matter_loss_ev=0.1)
    weak = ElectromagneticMode(mode_energy_ev=5.0, coupling_energy_ev=0.01,
                               cavity_loss_ev=0.5, matter_loss_ev=0.5)
    assert is_strong_coupling(strong)
    assert not is_strong_coupling(weak)


def test_weak_regime_scores_zero():
    weak = ElectromagneticMode(mode_energy_ev=5.0, coupling_energy_ev=0.01,
                               cavity_loss_ev=0.5, matter_loss_ev=0.5)
    assert coupling_regime(weak, TH) == "weak"
    assert polariton_coherence_score(weak, TH) == 0.0


def test_coherence_score_bounded_and_positive_in_strong_coupling():
    strong = ElectromagneticMode(mode_energy_ev=5.0, coupling_energy_ev=0.6,
                                 cavity_loss_ev=0.05, matter_loss_ev=0.05)
    s = polariton_coherence_score(strong, TH)
    assert 0.0 < s <= 1.0
    assert coupling_regime(strong, TH) in ("strong", "ultrastrong")


def test_cooperativity_and_lifetime_positive():
    m = ElectromagneticMode(mode_energy_ev=5.0, coupling_energy_ev=0.3,
                            cavity_loss_ev=0.1, matter_loss_ev=0.05)
    assert m.cooperativity > 0
    assert m.rabi_splitting_ev == 0.6
    assert m.coherence_lifetime_fs > 0
    assert math.isfinite(m.quality_factor)


def test_evaluate_result_is_not_a_superconductivity_claim():
    res = evaluate_em_coherence(
        number_density_m3=6.0e28,
        anisotropy_score=0.5,
        thresholds=TH,
        coupling_fraction=0.08,
        cavity_loss_ev=0.05,
        matter_loss_ev=0.05,
    )
    # anisotropy split present as a predicted optical observable
    obs = res.predicted_observables
    assert obs["plasmon_longitudinal_ev"] < obs["plasmon_transverse_ev"]
    # the verdict must never assert superconductivity
    verdict = res.explain()
    assert "NOT evidence of superconductivity" in verdict or "WEAK" in verdict
