"""Quantum ESPRESSO + EPW input-deck writers for the approximant.

Deterministic text generation only -- no binaries touched. Decks pin every
cutoff/mesh from EPWConfig. spin_polarized approximants get nspin=2 +
starting_magnetization.
"""

from __future__ import annotations

from .approximant import PeriodicApproximant
from .config import EPWConfig


def _cell(approx: PeriodicApproximant) -> str:
    lines = [f"    ibrav = {approx.ibrav}", f"    celldm(1) = {approx.a_bohr:.8f}"]
    if approx.c_over_a is not None:
        lines.append(f"    celldm(3) = {approx.c_over_a:.8f}")
    return "\n".join(lines)


def _system(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    lines = [
        "&system",
        _cell(approx),
        "    nat = 1",
        "    ntyp = 1",
        f"    ecutwfc = {cfg.ecutwfc_ry}",
        f"    ecutrho = {cfg.ecutrho_ry}",
        "    occupations = 'smearing'",
        "    smearing = 'mp'",
        "    degauss = 0.02",
    ]
    if approx.spin_polarized:
        lines.append("    nspin = 2")
        lines.append(f"    starting_magnetization(1) = {approx.starting_magnetization}")
    lines.append("/")
    return "\n".join(lines)


def _atomic_blocks(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    upf = cfg.pseudo_for(approx.element_symbol) or f"{approx.element_symbol}.upf"
    return (
        "ATOMIC_SPECIES\n"
        f" {approx.element_symbol} 1.0 {upf}\n"
        "ATOMIC_POSITIONS crystal\n"
        f" {approx.element_symbol} 0.0 0.0 0.0\n"
    )


def _pw(approx: PeriodicApproximant, cfg: EPWConfig, calc: str,
        kmesh: tuple[int, int, int], prefix: str) -> str:
    pd = cfg.resolved_pseudo_dir()
    kx, ky, kz = kmesh
    return (
        "&control\n"
        f"    calculation = '{calc}'\n"
        f"    prefix = '{prefix}'\n"
        f"    pseudo_dir = '{pd}'\n"
        "    outdir = './'\n"
        "/\n"
        f"{_system(approx, cfg)}\n"
        "&electrons\n"
        "    conv_thr = 1.0d-10\n"
        "/\n"
        f"{_atomic_blocks(approx, cfg)}"
        f"K_POINTS automatic\n {kx} {ky} {kz} 0 0 0\n"
    )


def scf_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    return _pw(approx, cfg, "scf", cfg.k_coarse, prefix)


def nscf_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    return _pw(approx, cfg, "nscf", cfg.k_fine, prefix)


def ph_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    # `approx` is intentionally unused here: real ph.x reads cell/species from
    # the prefix save files written by scf, not from this deck.
    qx, qy, qz = cfg.q_coarse
    return (
        f"phonons for {prefix}\n"
        "&inputph\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        "    fildyn = 'dyn'\n"
        "    ldisp = .true.\n"
        f"    nq1 = {qx}\n    nq2 = {qy}\n    nq3 = {qz}\n"
        f"    ! q_coarse = {qx} {qy} {qz}\n"
        "/\n"
    )


def epw_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    # `approx` is intentionally unused here: real epw.x reads cell/species from
    # the prefix save files written by scf/nscf, not from this deck.
    kf = cfg.k_fine
    qf = cfg.q_fine
    kc = cfg.k_coarse
    qc = cfg.q_coarse
    return (
        "&inputepw\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        "    elph = .true.\n"
        "    epwwrite = .true.\n"
        "    a2f = .true.\n"
        f"    nkf1 = {kf[0]}\n    nkf2 = {kf[1]}\n    nkf3 = {kf[2]}\n"
        f"    nqf1 = {qf[0]}\n    nqf2 = {qf[1]}\n    nqf3 = {qf[2]}\n"
        f"    nk1 = {kc[0]}\n    nk2 = {kc[1]}\n    nk3 = {kc[2]}\n"
        f"    nq1 = {qc[0]}\n    nq2 = {qc[1]}\n    nq3 = {qc[2]}\n"
        "/\n"
    )
