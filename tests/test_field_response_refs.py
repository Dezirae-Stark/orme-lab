from orme_lab.field_response_refs import BENCHMARKS, CESII_ANCHOR, classifies_correctly


def test_all_benchmarks_classify_on_correct_side_of_pauli_boundary():
    # calibration: unconventional rows have R_Pauli>1, the Pauli-limited benchmark <=1
    assert len(BENCHMARKS) == 6
    for b in BENCHMARKS:
        assert classifies_correctly(b), f"{b.material} misclassified at R_Pauli=1"
    unconv = [b for b in BENCHMARKS if b.pairing_class == "unconventional"]
    pauli = [b for b in BENCHMARKS if b.pairing_class == "Pauli-limited"]
    assert unconv and pauli
    assert all(b.r_pauli > 1.0 for b in unconv)
    assert all(b.r_pauli <= 1.0 for b in pauli)


def test_every_benchmark_cites_a_source():
    for b in BENCHMARKS:
        assert b.citation and ("DOI" in b.citation or "PRL" in b.citation or "PRB" in b.citation
                               or "Science" in b.citation or "Nat" in b.citation)


def test_cesii_anchor_honest_scoping():
    t = CESII_ANCHOR.scoping.lower()
    assert "not" in t and "pgm" in t                # NOT a PGM system
    assert "not evidence" in t or "not a" in t       # not evidence for the ORME premise
    assert "240" in CESII_ANCHOR.conditions          # ~240 mK
    assert "gpa" in CESII_ANCHOR.conditions.lower()  # 6/7 GPa


def test_refs_never_score_a_pgm_candidate():
    # guardrail: the module exposes ONLY reference data + a classifier; no function takes or
    # returns a PGM CandidateRecord / score.
    import orme_lab.field_response_refs as m
    assert not hasattr(m, "score_candidate")
    for name in dir(m):
        obj = getattr(m, name)
        assert "CandidateRecord" not in getattr(obj, "__doc__", "" ) if callable(obj) else True
