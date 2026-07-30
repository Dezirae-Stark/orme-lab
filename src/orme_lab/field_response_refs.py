"""Heavy-fermion Hc2 / Pauli-limit benchmark references — calibration anchors for the field-response
discriminator's R_Pauli=1 singlet/unconventional boundary. GROUNDING ONLY: these are real external
superconductors used to document where the boundary sits; they NEVER contribute a score to any PGM
candidate. All citations audit-verified (research-wiki/prior-art/heavy-fermion-hc2-pauli-limit.md).
Level 2 — a grounded threshold is not a raised evidence level."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldResponseBenchmark:
    material: str
    r_pauli: float                 # published Hc2(0)/Bp (representative)
    clean: bool
    pairing_class: str             # "unconventional" | "Pauli-limited"
    citation: str


BENCHMARKS: "tuple[FieldResponseBenchmark, ...]" = (
    FieldResponseBenchmark("CeSiI", 5.5, True, "unconventional",
        "Shi, Cheng et al., Nat. Phys. (2026), DOI 10.1038/s41567-026-03392-3 — Hc2 4-7x Pauli, "
        "6 GPa dome / 7 GPa QCP, Tc~240 mK [TEMPLATE]"),
    FieldResponseBenchmark("CeSb2 (high-p)", 8.0, True, "unconventional",
        "Squire et al., PRL 131, 026001 (2023) — ~8x Pauli limit"),
    FieldResponseBenchmark("CeCoIn5", 5.0, True, "unconventional",
        "Miclea et al., PRL 96, 117001 (2006) — FFLO, clean, alpha~5"),
    FieldResponseBenchmark("CeRh2As2", 4.0, True, "unconventional",
        "Khim et al., Science 373, 1012 (2021), DOI 10.1126/science.abe7518 — field-induced SC transition"),
    FieldResponseBenchmark("LiFeAs", 0.9, True, "Pauli-limited",
        "Khim et al., PRB 84, 104502 (2011) — clean, Pauli-limited benchmark"),
    # theory anchor row (Pauli-limited reference behaviour; coefficient origin cited)
    FieldResponseBenchmark("BCS Pauli limit (theory)", 1.0, True, "Pauli-limited",
        "Clogston PRL 9,266 (1962) / Chandrasekhar APL 1,7 (1962); general Hc2 theory "
        "Schossmann & Carbotte PRB 39, 4210 (1989)"),
)


@dataclass(frozen=True)
class MethodologyAnchor:
    material: str
    conditions: str
    concept: str
    scoping: str
    citation: str


CESII_ANCHOR = MethodologyAnchor(
    material="CeSiI",
    conditions="Ce 4f heavy-fermion; pressure-tuned QCP; ~240 mK; 6 GPa (SC dome max) / 7 GPa (QCP)",
    concept=("superconductivity emerges when antiferromagnetic order is suppressed at a pressure-tuned "
             "quantum critical point — the peer-reviewed, cryogenic form of the 'latent SC deconfined "
             "by a perturbation' conceptual template (NO specific Baskaran citation is encoded here; "
             "recorded as a conceptual framing pending verification)"),
    scoping=("METHODOLOGY / CONCEPTUAL-TEMPLATE REFERENCE ONLY. NOT a PGM single-atom system, NOT room "
             "temperature, NOT evidence for the ORME premise — a different material class (Ce 4f) at "
             "millikelvin under GPa pressure. Used to calibrate the Hc2/Pauli-limit discriminator and "
             "seed its decisive-measurement spec, never to score a PGM candidate."),
    citation="Shi, Cheng et al., Nat. Phys. (2026), DOI 10.1038/s41567-026-03392-3",
)


def classifies_correctly(b: "FieldResponseBenchmark") -> bool:
    """The R_Pauli=1 boundary: unconventional rows sit above 1, Pauli-limited at/below 1."""
    return (b.r_pauli > 1.0) == (b.pairing_class == "unconventional")
