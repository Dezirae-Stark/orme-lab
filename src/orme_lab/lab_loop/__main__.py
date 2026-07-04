"""CLI: python -m orme_lab.lab_loop --max-avenues N [--out DIR].

Runs the loop offline with the HeuristicGenerator and writes ledger.jsonl +
digest.md. The creative (subagent) generator is wired in at the harness level,
not here."""

from __future__ import annotations

import argparse
import os

from .config import LoopConfig
from .loop import HeuristicGenerator, run_loop


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="orme_lab.lab_loop")
    p.add_argument("--max-avenues", type=int, default=20)
    p.add_argument("--out", default="experiments/ledger")
    args = p.parse_args(argv)

    rep = run_loop(HeuristicGenerator(), loop_config=LoopConfig(max_avenues=args.max_avenues))
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "ledger.jsonl"), "w", encoding="utf-8") as fh:
        fh.write(rep.ledger.to_jsonl())
    with open(os.path.join(args.out, "digest.md"), "w", encoding="utf-8") as fh:
        fh.write(rep.digest)
    print(rep.digest)
    print(f"\n[{len(rep.ledger.records)} avenues run, "
          f"{len(rep.ledger.proposals)} quarantined; stopped: {rep.stopped_reason}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
