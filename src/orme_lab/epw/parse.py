"""Parse the raw EPW PREFIX.a2f file into an EliashbergFunction.

The raw file is 11 columns: column 1 is omega in meV, columns 2-11 are
alpha^2F(omega) at 10 phonon-smearing (degaussq) values. We select one smearing
column and convert omega from meV to Kelvin so the moments come out in Kelvin.

Column semantics come from EPW docs/forum and MUST be re-verified against the
installed EPW version's a2f.f90 (format can change across releases) -- G-A2F.
"""

from __future__ import annotations

from .spectral import EliashbergFunction

MEV_TO_KELVIN = 11.604518          # 1 meV in Kelvin (1/k_B)
_N_SMEARING = 10                   # columns 2..11


def parse_a2f(text: str, column: int = 5) -> EliashbergFunction:
    if not (1 <= column <= _N_SMEARING):
        raise ValueError(f"smearing column {column} out of range 1..{_N_SMEARING}")
    omega: list[float] = []
    a2f: list[float] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.lower().startswith("lambda"):
            continue
        parts = s.split()
        if len(parts) < 1 + _N_SMEARING:
            continue
        try:
            w_mev = float(parts[0])
            val = float(parts[column])          # parts[1] is smearing col 1
        except ValueError:
            continue
        omega.append(w_mev * MEV_TO_KELVIN)
        a2f.append(val)
    return EliashbergFunction(omega=tuple(omega), a2f=tuple(a2f))
