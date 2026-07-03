import math
from pathlib import Path
from orme_lab.epw.parse import parse_a2f, MEV_TO_KELVIN
from orme_lab.epw.spectral import EliashbergFunction

FIX = Path(__file__).parent / "fixtures" / "sample.a2f"


def test_parses_11_columns_and_converts_to_kelvin():
    ef = parse_a2f(FIX.read_text(), column=5)
    assert isinstance(ef, EliashbergFunction)
    assert len(ef.omega) == 5
    # 25.850 meV -> ~300 K; spike position is the third grid point
    assert math.isclose(ef.omega[2], 25.850 * MEV_TO_KELVIN, rel_tol=1e-6)
    assert ef.a2f[2] == 1.0 and ef.a2f[0] == 0.0


def test_skips_comment_and_lambda_lines():
    ef = parse_a2f(FIX.read_text(), column=5)
    # 'lambda : 0.7736' and the '#' header must not become data rows
    assert all(math.isfinite(w) for w in ef.omega)


def test_column_selection_out_of_range_raises():
    import pytest
    with pytest.raises(ValueError):
        parse_a2f(FIX.read_text(), column=11)   # only 10 smearing columns (2..11 -> 1..10)


def test_parse_a2f_forwards_omega_min_and_unstable_tol():
    ef = parse_a2f(FIX.read_text(), column=5, omega_min=2.5, unstable_tol=0.2)
    assert ef.omega_min == 2.5 and ef.unstable_tol == 0.2
