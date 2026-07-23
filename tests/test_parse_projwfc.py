def test_parse_real_ir_projwfc_gives_five_d_occupations():
    from pathlib import Path
    from orme_lab.epw.parse_projwfc import parse_projwfc
    text = (Path(__file__).parent / "fixtures" / "sample.projwfc").read_text()
    occ = parse_projwfc(text)
    assert len(occ.per_atom) >= 1
    for atom in occ.per_atom:
        assert len(atom) == 5              # five d orbitals (l=2, m=-2..2)
        assert all(0.0 <= x <= 2.0 for x in atom)   # Löwdin occupations per (l,m), spin-summed
    # value-level: the real Ir fixture atom, spin-summed and reordered to _D_LABELS
    # (dz2, dxz, dyz, dxy, dx2y2). A dxy<->dx2y2 reorder bug or a spin-sum regression MUST fail
    # here, not slip through the length/bounds check above. Ground truth read from the fixture's
    # "Lowdin Charges" block (spin up + spin down): dz2/dx2y2 = 0.8446*2, t2g = ~0.7412*2.
    import pytest
    assert occ.per_atom[0] == pytest.approx((1.6892, 1.4823, 1.4823, 1.4823, 1.6892), abs=1e-3)
