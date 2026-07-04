import dataclasses
from orme_lab.config import DEFAULT_CONFIG
from orme_lab.pipeline import run_screen
from orme_lab.elements import get_element


def _au_records(compute_em):
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_em_coherence=compute_em)
    return run_screen(elements=[get_element("Au")], config=cfg)


def test_em_absent_by_default():
    for r in run_screen(elements=[get_element("Au")]):
        assert r.em_coherence_score is None
        assert r.em_regime is None


def test_em_present_when_flag_on():
    recs = _au_records(True)
    # a connected Au geometry has carriers -> em fields populated (not None)
    assert any(r.em_coherence_score is not None for r in recs)
    for r in recs:
        if r.em_coherence_score is not None:
            assert 0.0 <= r.em_coherence_score <= 1.0
            assert r.em_regime in ("weak", "strong", "ultrastrong")


def test_em_is_deterministic():
    a = [(r.element, r.geometry, r.em_coherence_score) for r in _au_records(True)]
    b = [(r.element, r.geometry, r.em_coherence_score) for r in _au_records(True)]
    assert a == b


def test_palladium_em_is_dark_when_flag_on():
    cfg = dataclasses.replace(DEFAULT_CONFIG, compute_em_coherence=True)
    for r in run_screen(elements=[get_element("Pd")], config=cfg):
        # n=0 -> plasmon 0 -> weak regime -> coherence 0.0 (dark), never None here
        assert r.em_coherence_score == 0.0
        assert r.em_regime == "weak"
