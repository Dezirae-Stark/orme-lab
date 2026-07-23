"""Parse QE projwfc.x stdout ("Lowdin Charges" block) into per-atom d-orbital occupations.

Format ground-truthed against the REAL fixture `tests/fixtures/sample.projwfc`
(live projwfc.x v.7.3.1 run on an Ir compact-cluster approximant, Task 1 of the
orbital-order-descriptor plan) -- NOT the QE manual. The relevant block looks
like (one repeat per atom):

    Lowdin Charges:

         Atom #   1: total charge =  16.8000, s =  2.9767, p =  5.9979, d =  7.8254,
                     spin up      =   8.4002, s =  1.4884,
                     spin up      =   8.4002, p =  2.9989, pz=  0.9996, px=  0.9996, py=  0.9996,
                     spin up      =   8.4002, d =  3.9128, dz2=  0.8446, dxz=  0.7412, dyz=  0.7412, dx2-y2=  0.8446, dxy=  0.7412,
                     spin down    =   8.3999, s =  1.4884,
                     spin down    =   8.3999, p =  2.9989, pz=  0.9996, px=  0.9996, py=  0.9996,
                     spin down    =   8.3999, d =  3.9125, dz2=  0.8446, dxz=  0.7411, dyz=  0.7411, dx2-y2=  0.8446, dxy=  0.7411,
                     polarization =   0.0003, s =  0.0000, p =  0.0000, d =  0.0003,
         Spilling Parameter:   0.0118

Observed columns per "spin up"/"spin down" d-line, in this EXACT order:
dz2, dxz, dyz, dx2-y2, dxy. Each is the Lowdin occupation for that (l=2, m)
orbital in ONE spin channel (range roughly 0..1). Per-atom, per-orbital
occupations used downstream (`orbital_order.py` / `_D_LABELS`) are SPIN-SUMMED
(spin up + spin down), giving values in [0, 2], and reordered to the
`_D_LABELS = ("dz2", "dxz", "dyz", "dxy", "dx2y2")` convention (dxy and dx2-y2
swapped relative to the raw QE print order above).

For a non-spin-polarized run (no "spin up"/"spin down" lines), the plain
"d =" line's dz2/dxz/dyz/dx2-y2/dxy values are already spin-summed totals and
are used directly.
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# QE print order for the d sub-line; NOTE dx2-y2 precedes dxy here, which is
# the opposite of orbital_order._D_LABELS -- reordered on the way out.
_QE_D_ORDER = ("dz2", "dxz", "dyz", "dx2-y2", "dxy")
# Target order matching orbital_order._D_LABELS = (dz2, dxz, dyz, dxy, dx2y2).
_OUT_ORDER = ("dz2", "dxz", "dyz", "dxy", "dx2-y2")

_ATOM_HEADER_RE = re.compile(r"Atom\s*#\s*\d+:")
_D_LINE_RE = re.compile(
    r"d\s*=\s*[-\d.]+,\s*"
    r"dz2\s*=\s*([-\d.]+),\s*"
    r"dxz\s*=\s*([-\d.]+),\s*"
    r"dyz\s*=\s*([-\d.]+),\s*"
    r"dx2-y2\s*=\s*([-\d.]+),\s*"
    r"dxy\s*=\s*([-\d.]+),"
)


@dataclass(frozen=True)
class OrbitalOccupations:
    """Per-atom five d-orbital (l=2, m) Löwdin occupations, spin-summed, m-ordered
    to match `orbital_order._D_LABELS` = (dz2, dxz, dyz, dxy, dx2y2)."""
    per_atom: "tuple[tuple[float, ...], ...]"


def parse_projwfc(text: str) -> OrbitalOccupations:
    """Extract per-atom spin-summed d-orbital occupations from projwfc.x stdout.

    Walks the "Lowdin Charges:" block. Each atom contributes either one plain
    "d =" line (non-polarized) or two "d =" lines tagged "spin up"/"spin down"
    (spin-polarized, summed here). Lines outside an "Atom #" record are
    ignored, so the routine is robust to the surrounding eigenvalue-projection
    dump that precedes the charges block in the fixture.
    """
    lowdin_start = text.find("Lowdin Charges")
    block = text[lowdin_start:] if lowdin_start != -1 else text

    per_atom: list[tuple[float, ...]] = []
    current: dict[str, float] | None = None

    for line in block.splitlines():
        if _ATOM_HEADER_RE.search(line):
            if current is not None:
                per_atom.append(_finalize(current))
            current = {}
            continue
        if current is None:
            continue
        m = _D_LINE_RE.search(line)
        if m:
            vals = dict(zip(_QE_D_ORDER, (float(g) for g in m.groups())))
            for k, v in vals.items():
                current[k] = current.get(k, 0.0) + v

    if current is not None:
        per_atom.append(_finalize(current))

    return OrbitalOccupations(per_atom=tuple(per_atom))


def _finalize(d: "dict[str, float]") -> "tuple[float, ...]":
    return tuple(d.get(k, 0.0) for k in _OUT_ORDER)
