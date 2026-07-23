"""EPWConfig -- deterministic parameters for the EPW backend.

Owned by EPWBackend at construction (kept out of LabConfig). All meshes/cutoffs
are pinned so a run is reproducible up to the external solver's own
MPI/BLAS-level nondeterminism (see the spec's O5 -- sc_* columns are not
byte-reproducible).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class EPWConfig:
    mu_star: float = 0.10
    ecutwfc_ry: float = 60.0
    ecutrho_ry: float = 480.0
    k_coarse: tuple[int, int, int] = (8, 8, 8)
    q_coarse: tuple[int, int, int] = (4, 4, 4)
    k_fine: tuple[int, int, int] = (20, 20, 20)
    q_fine: tuple[int, int, int] = (20, 20, 20)
    smearing_column: int = 5          # 1..10 -> which degaussq column of the .a2f
    omega_min_k: float = 1.0
    unstable_tol: float = 0.05
    pseudo_dir: str = ""
    pseudopotentials: tuple[tuple[str, str], ...] = ()
    pw_x: str = "pw.x"
    ph_x: str = "ph.x"
    epw_x: str = "epw.x"
    projwfc_x: str = "projwfc.x"
    scratch_root: str = "/tmp/orme-epw"
    timeout_s: int = 86400
    tr2_ph: str = "1.0d-14"          # DFPT self-consistency threshold (ph.x)
    # --- EPW Wannier / a2f knobs (structure validated vs QE 7.3.1/EPW 5.8.1 on
    # fcc Pb, lam=1.19; the per-element PGM projection/windows below are DEFAULTS
    # that need tuning + convergence against real epw.x before any lam is trusted).
    nbndsub: int = 0                 # 0 = auto (d+s Wannier count from valence)
    n_semicore_bands: int = 0        # >0 -> emit bands_skipped='exclude_bands=1:N';
                                     # EPW ignores dis_win_min for exclusion and needs
                                     # this explicit skip (Ir SG15 NC: 5s+5p = 4 bands)
    wann_num_iter: int = 300
    dis_win_min_ev: float = -8.0
    dis_win_max_ev: float = 20.0
    dis_froz_min_ev: float = -8.0
    dis_froz_max_ev: float = 10.0
    fsthick_ev: float = 6.0
    degaussw_ev: float = 0.05
    temps_k: float = 0.3
    dvscf_dir: str = "save"          # collected phonon-potential dir EPW reads
    lifc: bool = True                # crystal ASR via real-space IFCs read from the
    asr_typ: str = "crystal"         # q2r.x-generated <dvscf_dir>/ifc.q2r file (the
                                     # pipeline's q2r stage writes it). Zeroes the
                                     # Gamma acoustic modes; without it EPW's 'simple'
                                     # sum rule left them imaginary and the a2f/lambda
                                     # collapsed (Pt Tier-0). asr_typ applies iff lifc.

    def resolved_pseudo_dir(self) -> str:
        return self.pseudo_dir or os.environ.get("ESPRESSO_PSEUDO", "")

    def pseudo_for(self, symbol: str) -> str | None:
        for sym, upf in self.pseudopotentials:
            if sym == symbol:
                return upf
        return None
