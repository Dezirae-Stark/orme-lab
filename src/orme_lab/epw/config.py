"""EPWConfig -- deterministic parameters for the EPW backend.

Owned by EPWBackend at construction (kept out of LabConfig). All meshes/cutoffs
are pinned so a run is reproducible up to the external solver's own
MPI/BLAS-level nondeterminism (see the spec's O5 -- sc_* columns are not
byte-reproducible).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


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
    scratch_root: str = "/tmp/orme-epw"
    timeout_s: int = 86400

    def resolved_pseudo_dir(self) -> str:
        return self.pseudo_dir or os.environ.get("ESPRESSO_PSEUDO", "")

    def pseudo_for(self, symbol: str) -> str | None:
        for sym, upf in self.pseudopotentials:
            if sym == symbol:
                return upf
        return None
