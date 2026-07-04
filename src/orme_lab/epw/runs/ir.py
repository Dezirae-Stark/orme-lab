"""Pinned Ir per-element EPW run parameters (thin wrappers over ``pgm``).

The reference lattice is a COUNTERFACTUAL: a = d*sqrt(2) with d = 2*covalent_radius
= 2.82 A (cluster nearest-neighbour), giving a = 3.988 A -- larger than experimental
fcc Ir (3.839 A). This is the charter's imposed close-packed approximant, NOT real Ir
metal, so no external Ir lambda is comparable to it.

Every ORME-relevant Ir spin state is MAGNETIC (d7): high-spin -> 3 unpaired
(nspin=2, starting_magnetization=0.3); low-spin -> 1 unpaired (still nspin=2). The
'none' spin is an ARTIFICIAL unpaired=0 non-magnetic reference used only to calibrate
the Wannier recipe + validate the pipeline for a d-electron metal.

Ir SG15 ONCV scalar-relativistic pseudo is Z_valence=17 -> 4 semicore bands (5s5p).
"""
from __future__ import annotations

from ..approximant import PeriodicApproximant
from ..config import EPWConfig
from .pgm import pgm_approximant, pgm_config

IR_CLUSTER_N = 13
IR_SEMICORE_BANDS = 4          # SG15 Ir Z=17, d+s=9 -> (17-9)/2 = 4 (skip 5s5p)


def ir_approximant(spin: str) -> PeriodicApproximant:
    return pgm_approximant("Ir", spin)


def ir_config(pseudo_dir: str, upf: str,
              *, ecutwfc_ry: float = 60.0, ecutrho_ry: float = 480.0) -> EPWConfig:
    return pgm_config("Ir", pseudo_dir, upf, n_semicore_per_atom=IR_SEMICORE_BANDS,
                      n_atoms=1, ecutwfc_ry=ecutwfc_ry, ecutrho_ry=ecutrho_ry)
