"""Generic per-element PGM run config (Ir, Pt, Os, ...).

The one genuinely per-element quantity is the number of deep semicore bands EPW
must skip (`exclude_bands`): the trustworthy norm-conserving pseudos keep a
5s/5p (or 4s/4p) semicore, so the d+s Wannier manifold cannot hold all the
valence electrons and `efermig` fails unless the semicore is excluded. That count
is not guessed -- it is computed from the pseudo's own Z_valence and the element's
d+s valence:

    n_semicore_bands = (Z_valence - (d_electrons + s_electrons)) / 2

Verified against the SG15 ONCV scalar-relativistic pseudos: Ir (Z=17, d+s=9) -> 4
(skip 5s5p); Pt (Z=16, d+s=10) -> 3 (skip 5p only). Everything else (lattice from
the cluster NN, Fermi-referenced windows, nbndsub=6 d+s) is element-independent.
"""
from __future__ import annotations

import os
import re

from ...elements import get_element
from ...geometry import make_compact_cluster
from ...spin_states import SpinState, high_spin_state, low_spin_state
from ..approximant import PeriodicApproximant, build_approximant
from ..config import EPWConfig

CLUSTER_N = 13
_SPINS = ("none", "low", "high")


def parse_z_valence(upf_path: str) -> float:
    """Read the pseudopotential's Z_valence from its UPF header."""
    with open(upf_path, encoding="latin-1") as fh:
        txt = fh.read()
    m = re.search(r'z_valence\s*=?\s*"?\s*([0-9.]+)', txt, re.IGNORECASE)
    if not m:
        raise ValueError(f"no z_valence found in {upf_path}")
    return float(m.group(1))


def n_semicore_bands(symbol: str, z_valence: float) -> int:
    """Semicore bands to exclude = (Z_valence - (d+s valence)) / 2."""
    el = get_element(symbol)
    n = round((z_valence - (el.d_electrons + el.s_electrons)) / 2)
    if n < 0:
        raise ValueError(
            f"{symbol}: negative semicore count from Z_valence={z_valence} "
            f"and d+s={el.d_electrons + el.s_electrons}"
        )
    return n


def semicore_for_pseudo(symbol: str, pseudo_dir: str, upf: str) -> int:
    """Compute the semicore-band count directly from the pseudo file."""
    return n_semicore_bands(symbol, parse_z_valence(os.path.join(pseudo_dir, upf)))


def pgm_approximant(symbol: str, spin: str) -> PeriodicApproximant:
    if spin not in _SPINS:
        raise ValueError(f"spin must be one of {_SPINS}, got {spin!r}")
    el = get_element(symbol)
    geom = make_compact_cluster(el, CLUSTER_N)
    state = {
        "high": high_spin_state(el),
        "low": low_spin_state(el),
        "none": SpinState(el, 0, is_high_spin=False),
    }[spin]
    return build_approximant(el, geom, state)


def pgm_config(symbol: str, pseudo_dir: str, upf: str, *,
               n_semicore_per_atom: int, n_atoms: int = 1,
               ecutwfc_ry: float = 60.0, ecutrho_ry: float = 480.0) -> EPWConfig:
    """Element-generic EPW config. The Wannier count (d+s = 6 per atom) and the
    semicore-skip count both scale with the number of atoms in the cell -- so an
    hcp 2-atom cell gets nbndsub=12 and exclude_bands=1:(2*per-atom). ``n_semicore_
    per_atom`` comes from ``semicore_for_pseudo``; dis_* are Fermi-relative offsets."""
    return EPWConfig(
        pseudo_dir=pseudo_dir,
        pseudopotentials=((symbol, upf),),
        ecutwfc_ry=ecutwfc_ry,
        ecutrho_ry=ecutrho_ry,
        k_coarse=(8, 8, 8),
        q_coarse=(4, 4, 4),
        k_fine=(20, 20, 20),
        q_fine=(20, 20, 20),
        nbndsub=6 * n_atoms,
        dis_win_min_ev=-12.0,
        dis_win_max_ev=20.0,
        dis_froz_min_ev=-2.0,
        dis_froz_max_ev=1.0,
        n_semicore_bands=n_semicore_per_atom * n_atoms,
        mu_star=0.10,
    )
