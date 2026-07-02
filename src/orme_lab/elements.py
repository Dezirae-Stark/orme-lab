"""Platinum-group metals (PGM) and coinage-metal reference data.

The ORME/PGM claims center on a specific set of heavy transition metals. This
module encodes the ground-state atomic data we actually need for the toy models:
atomic number, ground-state valence configuration, and the number of valence
``d`` and ``s`` electrons (these drive the spin and density heuristics).

Data limitations
----------------
The valence configurations below are the accepted *gas-phase atomic* ground
states (e.g. platinum is [Xe] 4f14 5d9 6s1, an exception to naive Aufbau). They
are textbook values, not computed here. In a real cluster or solid the effective
configuration shifts — that is precisely what a DFT backend would resolve.

    TODO(dft): replace hand-entered valence counts with configurations pulled
    from an ab-initio calculation (PySCF/ORCA) once a backend is wired in.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Element:
    """Minimal atomic record for a candidate metal.

    Attributes
    ----------
    symbol, name, atomic_number:
        Standard identifiers.
    period, group:
        Position in the periodic table (group in the modern 1-18 convention).
    valence_config:
        Human-readable gas-phase ground-state valence configuration.
    d_electrons, s_electrons:
        Valence d- and s-electron counts. These feed the spin-polarization and
        density-anisotropy toy models. A high d-count with a partially filled
        shell is the precondition for a high-spin state.
    covalent_radius_ang:
        Single-bond covalent radius (angstrom), used as a crude nearest-neighbour
        distance estimate when a cluster geometry is generated from scratch.
    """

    symbol: str
    name: str
    atomic_number: int
    period: int
    group: int
    valence_config: str
    d_electrons: int
    s_electrons: int
    covalent_radius_ang: float

    @property
    def valence_electrons(self) -> int:
        return self.d_electrons + self.s_electrons

    @property
    def d_shell_vacancies(self) -> int:
        """Empty slots in the valence d shell (max 10). Zero means a full,
        low-spin-favouring shell; larger means more room for unpaired spins."""
        return 10 - self.d_electrons


# The core screening set requested: Au, Pt, Pd, Ir, Rh, Os.
# Ru and Ag are included as useful neighbours for comparison / control.
_ELEMENTS: dict[str, Element] = {
    "Ru": Element("Ru", "Ruthenium", 44, 5, 8, "[Kr] 4d7 5s1", 7, 1, 1.46),
    "Rh": Element("Rh", "Rhodium", 45, 5, 9, "[Kr] 4d8 5s1", 8, 1, 1.42),
    "Pd": Element("Pd", "Palladium", 46, 5, 10, "[Kr] 4d10", 10, 0, 1.39),
    "Ag": Element("Ag", "Silver", 47, 5, 11, "[Kr] 4d10 5s1", 10, 1, 1.45),
    "Os": Element("Os", "Osmium", 76, 6, 8, "[Xe] 4f14 5d6 6s2", 6, 2, 1.44),
    "Ir": Element("Ir", "Iridium", 77, 6, 9, "[Xe] 4f14 5d7 6s2", 7, 2, 1.41),
    "Pt": Element("Pt", "Platinum", 78, 6, 10, "[Xe] 4f14 5d9 6s1", 9, 1, 1.36),
    "Au": Element("Au", "Gold", 79, 6, 11, "[Xe] 4f14 5d10 6s1", 10, 1, 1.36),
}

#: The elements explicitly named in the screening spec.
CORE_SCREEN_SYMBOLS: tuple[str, ...] = ("Au", "Pt", "Pd", "Ir", "Rh", "Os")


def get_element(symbol: str) -> Element:
    """Look up an element by chemical symbol (case-sensitive standard form)."""
    try:
        return _ELEMENTS[symbol]
    except KeyError as exc:  # pragma: no cover - defensive
        known = ", ".join(sorted(_ELEMENTS))
        raise KeyError(f"Unknown element {symbol!r}. Known: {known}") from exc


def all_elements() -> list[Element]:
    """Return every registered element, ordered by atomic number."""
    return sorted(_ELEMENTS.values(), key=lambda e: e.atomic_number)


def core_screen_elements() -> list[Element]:
    """Return the six elements named in the screening spec, in spec order."""
    return [get_element(s) for s in CORE_SCREEN_SYMBOLS]
