"""Cluster geometry construction and descriptors.

Hypothesis 3 says the "rice-bean" shape may reflect *cluster geometry* rather
than single-atom electron density. So we need a lightweight way to build small
metal clusters (monomer, dimer, trimer, small compact aggregates) and measure
descriptors that later modules consume:

* nearest-neighbour distance  -> drives inter-unit coupling (geometry.py -> coupling.py)
* mean coordination number    -> drives structural-stability proxy
* radius of gyration + shape  -> feeds density-anisotropy discussion

This is pure geometry (points in space). No energetics. A real workflow would
relax these geometries with ASE + a DFT or interatomic-potential calculator;
here we just place atoms on idealized lattices.

    TODO(ase): expose ``to_ase_atoms()`` returning an ``ase.Atoms`` object so
    geometries can be handed straight to a real optimizer / calculator.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from .elements import Element


@dataclass(frozen=True)
class ClusterGeometry:
    """A rigid arrangement of identical atoms.

    Positions are in angstrom. ``label`` names the motif (e.g. "dimer",
    "fcc13") for reporting. All atoms are the same element in this toy model —
    mixed clusters are future work.
    """

    element: Element
    positions: tuple[tuple[float, float, float], ...]
    label: str = ""

    @property
    def n_atoms(self) -> int:
        return len(self.positions)

    def _pairwise_distances(self) -> list[float]:
        dists: list[float] = []
        pts = self.positions
        for i in range(len(pts)):
            for j in range(i + 1, len(pts)):
                dx = pts[i][0] - pts[j][0]
                dy = pts[i][1] - pts[j][1]
                dz = pts[i][2] - pts[j][2]
                dists.append(math.sqrt(dx * dx + dy * dy + dz * dz))
        return dists

    @property
    def nearest_neighbor_distance(self) -> float:
        """Shortest interatomic distance (angstrom).

        Returns ``inf`` for a monomer: a single atom has *no* neighbour, which
        is exactly the "isolated unit" limit of hypothesis 5 — a monomer can
        never provide an inter-unit coupling channel to itself."""
        dists = self._pairwise_distances()
        return min(dists) if dists else math.inf

    @property
    def mean_coordination(self) -> float:
        """Average number of neighbours within 1.25x the nearest-neighbour
        distance. A rough compactness / bonding-density measure."""
        if self.n_atoms < 2:
            return 0.0
        nn = self.nearest_neighbor_distance
        cutoff = 1.25 * nn
        pts = self.positions
        total = 0
        for i in range(len(pts)):
            for j in range(len(pts)):
                if i == j:
                    continue
                dx = pts[i][0] - pts[j][0]
                dy = pts[i][1] - pts[j][1]
                dz = pts[i][2] - pts[j][2]
                if math.sqrt(dx * dx + dy * dy + dz * dz) <= cutoff:
                    total += 1
        return total / self.n_atoms

    @property
    def radius_of_gyration(self) -> float:
        """RMS distance of atoms from the cluster centroid (angstrom)."""
        n = self.n_atoms
        if n == 0:
            return 0.0
        cx = sum(p[0] for p in self.positions) / n
        cy = sum(p[1] for p in self.positions) / n
        cz = sum(p[2] for p in self.positions) / n
        sq = sum(
            (p[0] - cx) ** 2 + (p[1] - cy) ** 2 + (p[2] - cz) ** 2
            for p in self.positions
        )
        return math.sqrt(sq / n)


def make_monomer(element: Element) -> ClusterGeometry:
    """A single atom at the origin — the electronically isolated limit."""
    return ClusterGeometry(element, ((0.0, 0.0, 0.0),), label="monomer")


def make_dimer(element: Element, bond_length_ang: float | None = None) -> ClusterGeometry:
    """A two-atom cluster along x. Default spacing = 2x covalent radius."""
    d = bond_length_ang if bond_length_ang is not None else 2.0 * element.covalent_radius_ang
    return ClusterGeometry(element, ((0.0, 0.0, 0.0), (d, 0.0, 0.0)), label="dimer")


def make_linear_chain(element: Element, n: int, spacing_ang: float | None = None) -> ClusterGeometry:
    """A linear chain of ``n`` atoms — a 1D anisotropic motif (needle-like)."""
    if n < 1:
        raise ValueError("chain needs at least one atom")
    d = spacing_ang if spacing_ang is not None else 2.0 * element.covalent_radius_ang
    pts = tuple((i * d, 0.0, 0.0) for i in range(n))
    return ClusterGeometry(element, pts, label=f"chain{n}")


def make_compact_cluster(element: Element, n: int, spacing_ang: float | None = None) -> ClusterGeometry:
    """A compact (roughly spherical) aggregate of ``n`` atoms on a simple-cubic
    grid, filling shells outward from the origin. Not a relaxed structure — a
    stand-in for a nanocluster until a real optimizer is attached.
    """
    if n < 1:
        raise ValueError("cluster needs at least one atom")
    d = spacing_ang if spacing_ang is not None else 2.0 * element.covalent_radius_ang
    # Generate simple-cubic grid points, sort by distance from origin, take n.
    reach = 1
    grid: list[tuple[float, float, float]] = []
    while len(grid) < n:
        grid = []
        for i in range(-reach, reach + 1):
            for j in range(-reach, reach + 1):
                for k in range(-reach, reach + 1):
                    grid.append((i * d, j * d, k * d))
        reach += 1
    grid.sort(key=lambda p: (p[0] ** 2 + p[1] ** 2 + p[2] ** 2, p))
    return ClusterGeometry(element, tuple(grid[:n]), label=f"compact{n}")
