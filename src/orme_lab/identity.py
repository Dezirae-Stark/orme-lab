"""Phase-identity gate (G_identity) — a hard upstream precondition.

No candidate may be credited as a superconductivity lead until phase identity is
established:

    G_identity = G_composition ∧ G_phase ∧ G_morphology ∧ G_oxidation

A "zero resistance" or "diamagnetic" reading cannot be attributed to a superconducting
phase of the metal until characterization shows the specimen actually IS the metal (and
not an oxide / hydroxide / salt / ligand complex / contaminated phase). This lab has no
real specimens, so the gate **default-blocks**: it is discharged only by an injected
``IdentityWitness`` carrying instrumented composition / phase / morphology / oxidation —
mirroring the ``.cube`` bridge (inject real data, else stay honest about the limit).

See ``docs/validation_tests.md`` §6 (G_identity). This is an *off-gate* signal: it is not
re-derivable from the superconductivity AND-gate's inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

_OX_TOL = 0.5  # |oxidation state| above this implies a compound, not the metal
_SUBGATES = ("composition", "phase", "morphology", "oxidation")


class IdentityVerdict(str, Enum):
    ESTABLISHED = "established"        # all four sub-gates witnessed as the target metal
    UNESTABLISHED = "unestablished"   # default / partial: blocked, route to characterization
    CONTRADICTED = "contradicted"     # a witness shows it is NOT the target metal -> hard fail


@dataclass(frozen=True)
class IdentityWitness:
    """An instrumented characterization record that can discharge G_identity.

    Each descriptor is None until a real measurement supplies it; ``instruments`` names
    the methods that established the record (a witness with no instrument is not a witness).
    """
    composition: str | None          # e.g. "Ir" (target) | "IrO2" | "IrCl3"
    phase: str | None                # "metallic" | "oxide" | "hydroxide" | "salt" | "complex"
    morphology: str | None           # "monatomic" | "sub-nm-cluster" | "nanoparticle" | "bulk"
    oxidation_state: float | None    # 0 for the metal; >0 implies a compound
    instruments: tuple[str, ...]     # e.g. ("XRD", "XPS", "ICP-MS", "EXAFS")


@dataclass(frozen=True)
class IdentityResult:
    verdict: IdentityVerdict
    established: bool
    missing: tuple[str, ...]         # sub-gates still lacking a witness
    note: str


def evaluate_identity(target_metal: str, witness: IdentityWitness | None) -> IdentityResult:
    """Evaluate G_identity for a candidate whose target material is ``target_metal``."""
    if witness is None or not witness.instruments:
        return IdentityResult(
            IdentityVerdict.UNESTABLISHED, False, _SUBGATES,
            "no characterization witness — establish phase identity "
            "(XRD/XPS/ICP-MS/EXAFS/…) before crediting superconductivity",
        )

    # Affirmative evidence that the specimen is NOT the target metal -> hard fail.
    contradictions = []
    if witness.composition is not None and witness.composition != target_metal:
        contradictions.append(f"composition {witness.composition} ≠ {target_metal}")
    if witness.phase is not None and witness.phase != "metallic":
        contradictions.append(f"phase '{witness.phase}' is not metallic")
    if witness.oxidation_state is not None and abs(witness.oxidation_state) > _OX_TOL:
        contradictions.append(f"oxidation state {witness.oxidation_state:g} implies a compound")
    if contradictions:
        return IdentityResult(
            IdentityVerdict.CONTRADICTED, False, (),
            "specimen is not the target metal: " + "; ".join(contradictions),
        )

    # No contradiction: are all four sub-gates positively witnessed as the metal?
    missing = []
    if witness.composition != target_metal:
        missing.append("composition")
    if witness.phase != "metallic":
        missing.append("phase")
    if witness.morphology is None:
        missing.append("morphology")
    if witness.oxidation_state is None:
        missing.append("oxidation")

    if not missing:
        return IdentityResult(
            IdentityVerdict.ESTABLISHED, True, (),
            f"phase identity established as metallic {target_metal} "
            f"via {', '.join(witness.instruments)}",
        )
    return IdentityResult(
        IdentityVerdict.UNESTABLISHED, False, tuple(missing),
        "partial witness — missing: " + ", ".join(missing),
    )
