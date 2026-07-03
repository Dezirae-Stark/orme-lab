"""Ab-initio backend interfaces (placeholder extension points).

Every physics module in this package ships a *toy* model and marks, in its
docstring, the ``TODO(<backend>)`` seam where a real ab-initio calculation would
replace it. This module turns those seams into concrete, typed extension points:
a :class:`DFTBackend` interface plus named adapter stubs for the tools named in
the project spec — ASE, PySCF, GPAW, ORCA, NWChem, Quantum ESPRESSO, EPW.

Nothing here is wired to a real calculation yet — every seam method raises
``NotImplementedError``. That is deliberate and honest: the adapters exist so a
future contributor has a well-defined place (and signature) to plug a backend
in, and so the pipeline can *optionally* consult one and fall back to the toy
model when a capability is absent. With no backend supplied, behavior is
identical to before (the toy path).

Design
------
* A backend advertises **declared capabilities** (what tool X is *meant* to
  compute) and reports **availability** (is the package importable / binary on
  ``PATH``?). Neither implies the seam is wired.
* A seam is *actually* wired only when a subclass overrides the corresponding
  method and marks it with :func:`implemented`. :meth:`DFTBackend.provides`
  returns ``True`` only then. The pipeline checks ``provides(...)`` before using
  a backend value, so an unimplemented (stub) capability never changes results.

    Everything this package produces remains a Level-2/3 artifact (see
    ``docs/CHARTER.md``) until a backend is implemented *and* independently
    validated — a wired backend does not by itself raise the evidence level.
"""

from __future__ import annotations

import importlib.util
import shutil
from enum import Enum
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # avoid import cycles — these are annotation-only
    from .elements import Element
    from .geometry import ClusterGeometry
    from .spin_states import SpinState
    from .epw.result import EPWResult


class Capability(Enum):
    """The ab-initio seams, one per ``TODO(<backend>)`` marker in the package."""

    RELAX_GEOMETRY = "relax_geometry"          # geometry.py TODO(ase)
    ELECTRON_CONFIG = "electron_configuration"  # elements.py TODO(dft)
    SPIN_STATE = "spin_state"                   # spin_states.py TODO(dft)
    DENSITY_ANISOTROPY = "density_anisotropy"   # electron_density.py TODO(dft)
    INTER_UNIT_COUPLING = "inter_unit_coupling"  # coupling.py TODO(dft/tb)
    FIELD_RESPONSE = "critical_field"           # magnetic_field.py TODO(physics)
    SUSCEPTIBILITY = "susceptibility"           # observables.py TODO(dft/epw)
    SC_GAP = "superconducting_gap"              # superconductivity.py TODO(ab-initio)
    DIELECTRIC_FUNCTION = "plasmon_energy"      # electromagnetic_coherence.py TODO(dft/rpa)
    DENSITY_CUBE = "density_cube"               # emit a Gaussian .cube for the web renderer


def implemented(capability: Capability) -> Callable:
    """Mark a backend method as a *real* implementation of ``capability``.

    An override without this decorator is treated as still-a-stub, so
    :meth:`DFTBackend.provides` reports ``False`` and the pipeline keeps using
    the toy model. Decorate an override only when it genuinely computes the
    quantity.
    """

    def _decorate(fn: Callable) -> Callable:
        fn._orme_capability = capability  # type: ignore[attr-defined]
        return fn

    return _decorate


class DFTBackend:
    """Optional ab-initio replacement for the toy models.

    Subclass and override the seam methods you can compute, decorating each with
    :func:`implemented`. Every method returns the *same shape* as the toy
    function it replaces, so it is a drop-in at the pipeline seam. Unimplemented
    methods raise ``NotImplementedError``.
    """

    name: str = "abstract"
    description: str = "abstract base — implements nothing"
    #: What a full implementation of this backend is intended to provide.
    declared_capabilities: frozenset[Capability] = frozenset()
    #: Python modules that must be importable for the backend to run.
    python_requires: tuple[str, ...] = ()
    #: Executables that must be on PATH for the backend to run.
    binary_requires: tuple[str, ...] = ()

    # -- discovery ----------------------------------------------------------
    @classmethod
    def available(cls) -> bool:
        """Whether this backend's dependencies are present on this machine.

        ``False`` for the abstract base (no requirements). Availability says
        nothing about whether a seam is *implemented* — use :meth:`provides`."""
        if not (cls.python_requires or cls.binary_requires):
            return False
        for mod in cls.python_requires:
            if importlib.util.find_spec(mod) is None:
                return False
        for exe in cls.binary_requires:
            if shutil.which(exe) is None:
                return False
        return True

    def provides(self, capability: Capability) -> bool:
        """True only if this instance genuinely implements ``capability``
        (an override decorated with :func:`implemented`)."""
        method = getattr(type(self), capability.value, None)
        return getattr(method, "_orme_capability", None) is capability

    def capabilities(self) -> frozenset[Capability]:
        """The set of capabilities actually implemented (not merely declared)."""
        return frozenset(c for c in Capability if self.provides(c))

    def _nyi(self, capability: Capability):
        raise NotImplementedError(
            f"The {self.name!r} backend does not implement {capability.name}. "
            f"Subclass {type(self).__name__} and override {capability.value}(), "
            f"decorating it with @implemented(Capability.{capability.name})."
        )

    # -- seams (mirror the toy function outputs; stubs until implemented) ----
    def relax_geometry(self, geometry: "ClusterGeometry") -> "ClusterGeometry":
        """Return a relaxed cluster geometry (replaces the idealized lattice)."""
        self._nyi(Capability.RELAX_GEOMETRY)

    def electron_configuration(self, element: "Element") -> dict:
        """Effective valence occupation for the element in-situ (not gas-phase)."""
        self._nyi(Capability.ELECTRON_CONFIG)

    def spin_state(self, element: "Element", high_spin: bool) -> "SpinState":
        """Computed spin state (broken-symmetry / unrestricted DFT)."""
        self._nyi(Capability.SPIN_STATE)

    def density_anisotropy(self, state: "SpinState") -> float:
        """Charge/spin-density anisotropy in [0,1] from the real density tensor."""
        self._nyi(Capability.DENSITY_ANISOTROPY)

    def inter_unit_coupling(self, geometry: "ClusterGeometry") -> float:
        """Inter-unit coupling score in [0,1] from real transfer integrals."""
        self._nyi(Capability.INTER_UNIT_COUPLING)

    def critical_field(self, spin_polarization: float, coupling: float) -> float:
        """Critical field (tesla) from orbital + paramagnetic pair-breaking."""
        self._nyi(Capability.FIELD_RESPONSE)

    def susceptibility(self, state: "SpinState", temperature_k: float) -> float:
        """Computed magnetic susceptibility (replaces the Curie-law proxy)."""
        self._nyi(Capability.SUSCEPTIBILITY)

    def superconducting_gap(self, element: "Element", geometry: "ClusterGeometry",
                            spin_state: "SpinState") -> "EPWResult":
        """Electron-phonon Eliashberg Tc for a periodic approximant of the
        candidate (Capability.SC_GAP). PHONON-CHANNEL, SPIN-SINGLET Tc of an
        IMPOSED reference lattice -- NOT a superconductivity estimate for the
        ORME claim; a returned Tc is not evidence the material superconducts.
        Level 2."""
        self._nyi(Capability.SC_GAP)

    def plasmon_energy(self, number_density_m3: float) -> float:
        """Plasmon energy (eV) from a computed dielectric function eps(q, w)."""
        self._nyi(Capability.DIELECTRIC_FUNCTION)

    def density_cube(self, element: "Element", geometry: "ClusterGeometry",
                     spin_state: "SpinState") -> str:
        """Gaussian ``.cube`` text for the computed charge density (or an orbital).

        This is the bridge to the web renderer's DFT-cube path (``web/cube.js``):
        a real backend computes the density on a grid and serializes it to the
        standard cube format, which the interactive lab loads and isosurfaces
        through the same pipeline as the analytic eigenstate. See
        ``tools/eigenstate_to_cube.py`` for the format (generated from the
        analytic model until a real backend is wired)."""
        self._nyi(Capability.DENSITY_CUBE)


# ---------------------------------------------------------------------------
# Named adapter stubs — the concrete places a real integration goes.
# Each declares its intended capabilities and its dependency, and reports
# availability by probing the environment. None implement a seam yet.
# ---------------------------------------------------------------------------
class ASEBackend(DFTBackend):
    name = "ase"
    description = "Atomic Simulation Environment — structure handling and relaxation"
    declared_capabilities = frozenset({Capability.RELAX_GEOMETRY})
    python_requires = ("ase",)


class PySCFBackend(DFTBackend):
    name = "pyscf"
    description = "PySCF — Gaussian-basis DFT / post-HF for clusters"
    declared_capabilities = frozenset({
        Capability.ELECTRON_CONFIG,
        Capability.SPIN_STATE,
        Capability.DENSITY_ANISOTROPY,
        Capability.SUSCEPTIBILITY,
        Capability.DENSITY_CUBE,
    })
    python_requires = ("pyscf",)


class GPAWBackend(DFTBackend):
    name = "gpaw"
    description = "GPAW — real-space / PAW DFT (needs libxc, MPI)"
    declared_capabilities = frozenset({
        Capability.DENSITY_ANISOTROPY,
        Capability.DIELECTRIC_FUNCTION,
        Capability.DENSITY_CUBE,
    })
    python_requires = ("gpaw",)


class ORCABackend(DFTBackend):
    name = "orca"
    description = "ORCA — molecular DFT / post-HF (external binary, license required)"
    declared_capabilities = frozenset({
        Capability.SPIN_STATE,
        Capability.DENSITY_ANISOTROPY,
        Capability.FIELD_RESPONSE,
    })
    binary_requires = ("orca",)


class NWChemBackend(DFTBackend):
    name = "nwchem"
    description = "NWChem — molecular/periodic DFT (external binary, MPI)"
    declared_capabilities = frozenset({
        Capability.ELECTRON_CONFIG,
        Capability.SPIN_STATE,
    })
    binary_requires = ("nwchem",)


class QuantumEspressoBackend(DFTBackend):
    name = "quantum-espresso"
    description = "Quantum ESPRESSO — plane-wave DFT for periodic solids"
    declared_capabilities = frozenset({
        Capability.INTER_UNIT_COUPLING,
        Capability.DIELECTRIC_FUNCTION,
    })
    binary_requires = ("pw.x",)


class EPWBackend(DFTBackend):
    name = "epw"
    description = "EPW — ab-initio electron-phonon / Eliashberg Tc (with Quantum ESPRESSO)"
    declared_capabilities = frozenset({Capability.SC_GAP})   # G-CAP: NOT INTER_UNIT_COUPLING
    binary_requires = ("pw.x", "ph.x", "epw.x")              # G-GATE: all three

    def __init__(self, config=None, runner=None):
        from .epw.config import EPWConfig
        from .epw.runner import LiveEPWRunner
        self.config = config or EPWConfig()
        self.runner = runner or LiveEPWRunner()

    @implemented(Capability.SC_GAP)
    def superconducting_gap(self, element, geometry, spin_state):
        from .epw.approximant import build_approximant, ApproximantUndefined
        from .epw.parse import parse_a2f
        from .epw.result import EPWResult
        from .epw.runner import EPWError
        from .epw.spectral import EliashbergFunction

        try:
            approx = build_approximant(element, geometry, spin_state)
        except ApproximantUndefined as exc:
            return EPWResult.not_applicable(str(exc))
        try:
            raw = self.runner.run(approx, self.config)
        except EPWError as exc:
            return EPWResult.failed(str(exc))
        ef = raw if isinstance(raw, EliashbergFunction) else parse_a2f(raw, self.config.smearing_column)
        return EPWResult.from_eliashberg(ef, self.config.mu_star, approx.label)


#: Registry of the named backend adapters, by short name.
BACKENDS: dict[str, type[DFTBackend]] = {
    cls.name: cls
    for cls in (
        ASEBackend, PySCFBackend, GPAWBackend, ORCABackend,
        NWChemBackend, QuantumEspressoBackend, EPWBackend,
    )
}


def list_backends() -> list[type[DFTBackend]]:
    """All registered backend adapter classes."""
    return list(BACKENDS.values())


def get_backend(name: str, **kwargs) -> DFTBackend:
    """Instantiate a named backend adapter (e.g. ``get_backend("pyscf")``)."""
    try:
        return BACKENDS[name](**kwargs)
    except KeyError as exc:  # pragma: no cover - defensive
        known = ", ".join(sorted(BACKENDS))
        raise KeyError(f"Unknown backend {name!r}. Known: {known}") from exc


def available_backends() -> list[str]:
    """Names of backends whose dependencies are actually present here (usually
    empty in a lightweight environment — installing the tool flips this)."""
    return [name for name, cls in BACKENDS.items() if cls.available()]
