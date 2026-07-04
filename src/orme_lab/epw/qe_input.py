"""Quantum ESPRESSO + EPW input-deck writers for the approximant.

Deterministic text generation only -- no binaries touched. Decks pin every
cutoff/mesh from EPWConfig. spin_polarized approximants get nspin=2 +
starting_magnetization.

Validation status (see docs/epw-live-validation.md): the deck STRUCTURE was
exercised end-to-end against real QE 7.3.1 / EPW 5.8.1 via the fcc-Pb reference
(reproduced lambda = 1.19, Allen-Dynes Tc = 6.5 K at mu*=0.10 -- the known
values). The SCF/ph/nscf writers and the dvscf-collection stage are validated.
The EPW-stage Wannier inputs (nbndsub, projections, disentanglement windows) are
grounded PGM DEFAULTS that still need per-element tuning + convergence before any
computed lambda for an ORME approximant is trusted.
"""

from __future__ import annotations

from .approximant import PeriodicApproximant
from .config import EPWConfig

#: Standard atomic masses (amu). CRITICAL for phonons: frequencies scale as
#: 1/sqrt(mass), so a placeholder mass gives wrong phonons (and wrong lambda).
ATOMIC_MASS_AMU: dict[str, float] = {
    "Ru": 101.07, "Rh": 102.91, "Pd": 106.42, "Ag": 107.87,
    "Os": 190.23, "Ir": 192.22, "Pt": 195.08, "Au": 196.97,
}


def _cell(approx: PeriodicApproximant) -> str:
    lines = [f"    ibrav = {approx.ibrav}", f"    celldm(1) = {approx.a_bohr:.8f}"]
    if approx.c_over_a is not None:
        lines.append(f"    celldm(3) = {approx.c_over_a:.8f}")
    return "\n".join(lines)


def _system(approx: PeriodicApproximant, cfg: EPWConfig, *, nbnd: int | None = None) -> str:
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
    if nbnd is not None:
        lines.append(f"    nbnd = {nbnd}")
    if approx.spin_polarized:
        lines.append("    nspin = 2")
        lines.append(f"    starting_magnetization(1) = {approx.starting_magnetization}")
    lines.append("/")
    return "\n".join(lines)


def _atomic_mass(symbol: str) -> float:
    return ATOMIC_MASS_AMU.get(symbol, 1.0)


def _atomic_blocks(approx: PeriodicApproximant, cfg: EPWConfig) -> str:
    upf = cfg.pseudo_for(approx.element_symbol) or f"{approx.element_symbol}.upf"
    mass = _atomic_mass(approx.element_symbol)
    return (
        "ATOMIC_SPECIES\n"
        f" {approx.element_symbol} {mass} {upf}\n"
        "ATOMIC_POSITIONS crystal\n"
        f" {approx.element_symbol} 0.0 0.0 0.0\n"
    )


def _uniform_kpoints(nk: tuple[int, int, int]) -> str:
    """Full uniform Gamma-centred grid as an explicit crystal k-list with equal
    weights. EPW needs the FULL grid on the nscf step (not the symmetry-reduced
    'K_POINTS automatic' set) so its coarse Bloch grid matches nk1/nk2/nk3."""
    nx, ny, nz = nk
    n = nx * ny * nz
    w = 1.0 / n
    lines = ["K_POINTS crystal", f" {n}"]
    for i in range(nx):
        for j in range(ny):
            for k in range(nz):
                lines.append(f" {i / nx:.8f} {j / ny:.8f} {k / nz:.8f} {w:.8e}")
    return "\n".join(lines) + "\n"


def _control(calc: str, prefix: str, pd: str) -> str:
    return (
        "&control\n"
        f"    calculation = '{calc}'\n"
        f"    prefix = '{prefix}'\n"
        f"    pseudo_dir = '{pd}'\n"
        "    outdir = './'\n"
        "    tprnfor = .true.\n"
        "    tstress = .true.\n"
        "/\n"
    )


def scf_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    kx, ky, kz = cfg.k_coarse
    return (
        f"{_control('scf', prefix, cfg.resolved_pseudo_dir())}"
        f"{_system(approx, cfg)}\n"
        "&electrons\n    conv_thr = 1.0d-10\n    mixing_beta = 0.7\n/\n"
        f"{_atomic_blocks(approx, cfg)}"
        f"K_POINTS automatic\n {kx} {ky} {kz} 0 0 0\n"
    )


def _wannier_count(approx: PeriodicApproximant, cfg: EPWConfig) -> int:
    """Number of Wannier functions. Explicit nbndsub wins; else d+s = 6 for the
    PGMs (5 d + 1 s), the chemically-motivated default active space."""
    if cfg.nbndsub > 0:
        return cfg.nbndsub
    return 6


def nscf_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    # nbnd headroom: enough bands to span the Wannier subspace + conduction slack.
    nbnd = _wannier_count(approx, cfg) + 8
    return (
        f"{_control('nscf', prefix, cfg.resolved_pseudo_dir())}"
        f"{_system(approx, cfg, nbnd=nbnd)}\n"
        "&electrons\n    conv_thr = 1.0d-10\n    mixing_beta = 0.7\n/\n"
        f"{_atomic_blocks(approx, cfg)}"
        f"{_uniform_kpoints(cfg.k_coarse)}"
    )


def ph_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str) -> str:
    # ph.x reads cell/species from the scf save files; this deck drives the DFPT.
    # fildvscf is REQUIRED -- it writes the phonon perturbation potentials EPW
    # later reads (missing it silently starves the EPW stage). The grid comment
    # keeps the q_coarse "qx qy qz" string for the structural test.
    qx, qy, qz = cfg.q_coarse
    return (
        f"phonons for {prefix} (q_coarse = {qx} {qy} {qz})\n"
        "&inputph\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        f"    fildyn = '{prefix}.dyn'\n"
        "    fildvscf = 'dvscf'\n"
        f"    tr2_ph = {cfg.tr2_ph}\n"
        "    ldisp = .true.\n"
        f"    nq1 = {qx}\n    nq2 = {qy}\n    nq3 = {qz}\n"
        "/\n"
    )


def epw_input(approx: PeriodicApproximant, cfg: EPWConfig, prefix: str,
              *, fermi_ev: float | None = None) -> str:
    """Full &inputepw for an elph -> a2f run. STRUCTURE validated vs real EPW
    (fcc Pb). The Wannier block (nbndsub/proj/dis windows) uses PGM defaults that
    need per-element tuning -- documented in the module docstring and the wiki.

    Disentanglement windows: QE reports ABSOLUTE eigenvalues, and a transition
    metal's E_F sits well above 0 (Ir: 21.5 eV), so a window written on a
    Fermi-referenced assumption lands entirely below the bands and Wannier90 fails
    with "Energy window contains fewer states than number of target WFs". When
    ``fermi_ev`` is given, the cfg dis_* values are treated as offsets RELATIVE to
    E_F (win = fermi_ev + offset); when None they are absolute (the legacy Pb path).
    """
    kf, qf, kc, qc = cfg.k_fine, cfg.q_fine, cfg.k_coarse, cfg.q_coarse
    el = approx.element_symbol
    nw = _wannier_count(approx, cfg)
    mass = _atomic_mass(el)
    shift = fermi_ev if fermi_ev is not None else 0.0
    win_min = cfg.dis_win_min_ev + shift
    win_max = cfg.dis_win_max_ev + shift
    froz_min = cfg.dis_froz_min_ev + shift
    froz_max = cfg.dis_froz_max_ev + shift
    return (
        "&inputepw\n"
        f"    prefix = '{prefix}'\n"
        "    outdir = './'\n"
        f"    amass(1) = {mass}\n"
        "    elph = .true.\n"
        "    epbwrite = .true.\n    epbread = .false.\n"
        "    epwwrite = .true.\n    epwread = .false.\n"
        "    phonselfen = .true.\n"
        "    elecselfen = .false.\n"
        "    a2f = .true.\n"
        # --- Wannierization (PGM defaults: d + s active space) ---
        "    wannierize = .true.\n"
        f"    nbndsub = {nw}\n"
        f"    num_iter = {cfg.wann_num_iter}\n"
        f"    proj(1) = '{el}:d'\n    proj(2) = '{el}:s'\n"
        f"    dis_win_min = {win_min}\n    dis_win_max = {win_max}\n"
        f"    dis_froz_min = {froz_min}\n    dis_froz_max = {froz_max}\n"
        # --- a2f / Eliashberg sampling ---
        f"    fsthick = {cfg.fsthick_ev}\n"
        f"    degaussw = {cfg.degaussw_ev}\n"
        f"    temps = {cfg.temps_k}\n"
        f"    dvscf_dir = './{cfg.dvscf_dir}'\n"
        # --- grids ---
        f"    nkf1 = {kf[0]}\n    nkf2 = {kf[1]}\n    nkf3 = {kf[2]}\n"
        f"    nqf1 = {qf[0]}\n    nqf2 = {qf[1]}\n    nqf3 = {qf[2]}\n"
        f"    nk1 = {kc[0]}\n    nk2 = {kc[1]}\n    nk3 = {kc[2]}\n"
        f"    nq1 = {qc[0]}\n    nq2 = {qc[1]}\n    nq3 = {qc[2]}\n"
        "/\n"
    )
