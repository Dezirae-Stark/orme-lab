def test_parse_real_ir_projwfc_gives_five_d_occupations():
    from pathlib import Path
    from orme_lab.epw.parse_projwfc import parse_projwfc
    text = (Path(__file__).parent / "fixtures" / "sample.projwfc").read_text()
    occ = parse_projwfc(text)
    assert len(occ.per_atom) >= 1
    for atom in occ.per_atom:
        assert len(atom) == 5              # five d orbitals (l=2, m=-2..2)
        assert all(0.0 <= x <= 2.0 for x in atom)   # Löwdin occupations per (l,m), spin-summed
