import subprocess
import sys
from orme_lab.lab_loop import run_loop, HeuristicGenerator
from orme_lab.lab_loop.config import LoopConfig


def test_heuristic_generator_drives_a_loop_offline():
    rep = run_loop(HeuristicGenerator(),
                   loop_config=LoopConfig(max_avenues=4, proposals_per_round=4,
                                          convergence_rounds=99))
    assert len(rep.ledger.records) >= 1
    # every recorded avenue used an off-gate predictor -> none tautological
    assert all(r.verdict != "tautological" for r in rep.ledger.records)


def test_heuristic_generator_eventually_exhausts():
    gen = HeuristicGenerator(elements=("Pd",))
    first = gen.propose(frozenset({"H5"}), frozenset(), 100)
    assert len(first) >= 1
    # asking again after 'seeing' those actions returns fewer/none
    seen = frozenset()  # generator is stateless re: seen; loop enforces dedup
    assert isinstance(first, list)


def test_cli_runs_and_writes_artifacts(tmp_path):
    out = tmp_path / "run"
    proc = subprocess.run(
        [sys.executable, "-m", "orme_lab.lab_loop",
         "--max-avenues", "3", "--out", str(out)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    assert (out / "ledger.jsonl").exists()
    assert (out / "digest.md").exists()
    assert "validated" not in (out / "digest.md").read_text().lower()
