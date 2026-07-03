import os
from orme_lab.epw.config import EPWConfig


def test_defaults():
    c = EPWConfig()
    assert c.mu_star == 0.10 and c.smearing_column == 5 and c.epw_x == "epw.x"


def test_pseudo_for_lookup():
    c = EPWConfig(pseudopotentials=(("Os", "Os.upf"), ("Au", "Au.upf")))
    assert c.pseudo_for("Au") == "Au.upf"
    assert c.pseudo_for("Pt") is None


def test_resolved_pseudo_dir_env_fallback(monkeypatch):
    monkeypatch.setenv("ESPRESSO_PSEUDO", "/opt/pseudo")
    assert EPWConfig().resolved_pseudo_dir() == "/opt/pseudo"
    assert EPWConfig(pseudo_dir="/explicit").resolved_pseudo_dir() == "/explicit"
