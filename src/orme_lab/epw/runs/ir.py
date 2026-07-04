"""Pinned Ir per-element EPW run parameters.

The reference lattice is a COUNTERFACTUAL: a = d*sqrt(2) with d = 2*covalent_radius
= 2.82 A (cluster nearest-neighbour), giving a = 3.988 A -- larger than experimental
fcc Ir (3.839 A). This is the charter's imposed close-packed approximant, NOT real Ir
metal, so no external Ir lambda is comparable to it.

Every ORME-relevant Ir spin state is MAGNETIC (d7): high-spin -> 3 unpaired
(nspin=2, starting_magnetization=0.3); low-spin -> 1 unpaired (still nspin=2). The
'none' spin is an ARTIFICIAL unpaired=0 non-magnetic reference used only to calibrate
the Wannier recipe + validate the pipeline for a d-electron metal.
"""
from __future__ import annotations

from ...elements import get_element
from ...geometry import make_compact_cluster
from ...spin_states import SpinState, high_spin_state, low_spin_state
from ..approximant import PeriodicApproximant, build_approximant
from ..config import EPWConfig

IR_CLUSTER_N = 13
_SPINS = ("none", "low", "high")


def ir_approximant(spin: str) -> PeriodicApproximant:
    if spin not in _SPINS:
        raise ValueError(f"spin must be one of {_SPINS}, got {spin!r}")
    ir = get_element("Ir")
    geom = make_compact_cluster(ir, IR_CLUSTER_N)
    state = {
        "high": high_spin_state(ir),
        "low": low_spin_state(ir),
        "none": SpinState(ir, 0, is_high_spin=False),
    }[spin]
    return build_approximant(ir, geom, state)


def ir_config(pseudo_dir: str, upf: str,
              *, ecutwfc_ry: float = 60.0, ecutrho_ry: float = 480.0) -> EPWConfig:
    # ecutwfc/ecutrho default to the Pb-tuned 60/480; CONFIRM against the SSSP
    # recommendation for the chosen Ir UPF at provision time and override if needed.
    #
    # dis_* are FERMI-RELATIVE offsets (eV): the deck writer adds E_F (parsed from
    # nscf) so the disentanglement window brackets the bands. Empirically fixed on
    # the first live Ir run -- the absolute default [-8,20] landed entirely below
    # E_F=21.5 eV and Wannier90 failed "fewer states than target WFs". These offsets
    # (outer [-12,+20], frozen [-2,+1] around E_F) got EPW past Wannierization into
    # the elph sum on real epw.x. Still a per-element default; confirm the Wannier
    # band match by hand before trusting the lambda.
    return EPWConfig(
        pseudo_dir=pseudo_dir,
        pseudopotentials=(("Ir", upf),),
        ecutwfc_ry=ecutwfc_ry,
        ecutrho_ry=ecutrho_ry,
        k_coarse=(8, 8, 8),
        q_coarse=(4, 4, 4),
        k_fine=(20, 20, 20),
        q_fine=(20, 20, 20),
        nbndsub=6,              # 5 d + 1 s explicit active space
        dis_win_min_ev=-12.0,   # relative to E_F (added by epw_input via --fermi)
        dis_win_max_ev=20.0,
        dis_froz_min_ev=-2.0,
        dis_froz_max_ev=1.0,
        mu_star=0.10,
    )
