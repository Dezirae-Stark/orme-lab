"""Uncertainty propagation + rank stability for candidate scores.

Single deterministic scores can make a poorly-constrained candidate look more precise
than it is. This module wraps the screen over the *tunable thresholds*: it perturbs each
``ModelThresholds`` floor within a documented plausible range and re-scores, so every
candidate carries ``score ± interval`` and a **rank-stability** figure (how often it holds
its rank) instead of a bare point value.

Two legs, per the design:
- **Seeded Monte Carlo (primary)** — ``propagate_mc`` draws N seeded threshold samples,
  re-runs the screen, and aggregates the ``sc_plausibility`` distribution + rank stats.
  A fixed default seed makes the whole thing byte-reproducible (determinism charter).
- **Analytic interval (cross-check)** — ``analytic_interval`` does first-order sensitivity
  (central differences summed in quadrature) as a sanity leg against the MC spread.

Plus a **missing-data penalty**: a candidate scored only by the toy proxies (no ab-initio
EPW value) is less constrained, so its interval is widened rather than read as sharp.

Every threshold range is an *assumption* (default ±30% of the floor's value), documented
here and carried in the output.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass, replace
from random import Random

from .config import DEFAULT_CONFIG, LabConfig, ModelThresholds
from .elements import Element
from .pipeline import CandidateRecord, run_screen

#: Fractional half-width of each threshold's plausible range (assumption; documented).
DEFAULT_RANGE_FRAC = 0.30

#: The tunable decision floors that carry uncertainty (the SC gates + geometry heuristics).
PERTURBED_FIELDS: tuple[str, ...] = (
    "min_coupling_for_bulk", "min_carrier_proxy", "min_field_tolerance",
    "min_structural_stability", "min_observable_signal",
    "anisotropy_ricebean_low", "anisotropy_ricebean_high", "coupling_distance_scale_ang",
)


def _key(r: CandidateRecord) -> tuple[str, str, str]:
    return (r.element, r.geometry, r.spin_label)


def _perturb(th: ModelThresholds, rng: Random, frac: float) -> ModelThresholds:
    return replace(th, **{f: getattr(th, f) * (1.0 + rng.uniform(-frac, frac)) for f in PERTURBED_FIELDS})


def _pct(sorted_vals: list[float], q: float) -> float:
    if not sorted_vals:
        return 0.0
    i = min(len(sorted_vals) - 1, max(0, round(q * (len(sorted_vals) - 1))))
    return sorted_vals[i]


@dataclass(frozen=True)
class ScoreDistribution:
    key: tuple[str, str, str]
    mean: float
    std: float
    p5: float
    p50: float
    p95: float
    penalty: float              # missing-data widening factor applied to the interval
    p5_widened: float           # p5/p95 after the missing-data penalty (the interval to trust)
    p95_widened: float
    rank1_fraction: float       # fraction of draws where this candidate ranked #1
    rank_p5: float
    rank_p95: float
    separated_from_next: bool   # True iff this candidate's widened interval clears the
    #                             next-ranked candidate's — i.e. it is ROBUSTLY ahead. When
    #                             False, a high rank1_fraction is a tie-break artifact, not a
    #                             real lead, and must not be read as robustness.
    n: int
    seed: int


def missing_data_penalty(record: CandidateRecord) -> float:
    """Interval-widening factor for an under-constrained candidate. A candidate scored
    purely by the toy proxies (no ab-initio EPW value) is less constrained than one with a
    real ``sc_tc_kelvin``, so its uncertainty interval is widened (read as *less* precise,
    not falsely sharp)."""
    return 1.5 if (record.sc_source == "toy" or record.sc_tc_kelvin is None) else 1.0


def propagate_mc(elements: list[Element] | None = None, config: LabConfig = DEFAULT_CONFIG,
                 n: int = 256, seed: int = 0, frac: float = DEFAULT_RANGE_FRAC) -> list[ScoreDistribution]:
    """Seeded Monte-Carlo over the tunable thresholds → per-candidate score distribution +
    rank stability. Deterministic: same (elements, config, n, seed, frac) → identical output."""
    rng = Random(seed)
    # Base (unperturbed) screen: the per-candidate record supplies the missing-data penalty.
    penalties = {_key(r): missing_data_penalty(r) for r in run_screen(elements=elements, config=config)}

    scores: dict[tuple, list[float]] = {}
    ranks: dict[tuple, list[int]] = {}
    for _ in range(n):
        cfg = replace(config, thresholds=_perturb(config.thresholds, rng, frac))
        recs = run_screen(elements=elements, config=cfg)
        ranked = sorted(recs, key=lambda r: (-r.sc_plausibility, _key(r)))
        for pos, r in enumerate(ranked, start=1):
            k = _key(r)
            scores.setdefault(k, []).append(r.sc_plausibility)
            ranks.setdefault(k, []).append(pos)

    # First pass: per-candidate stats + the penalty-widened interval.
    rows = []
    for k, sv in scores.items():
        ss = sorted(sv)
        rv = ranks[k]
        rr = sorted([float(x) for x in rv])
        mean = statistics.fmean(sv)
        p5, p50, p95 = _pct(ss, 0.05), _pct(ss, 0.50), _pct(ss, 0.95)
        pen = penalties.get(k, 1.0)
        rows.append({
            "key": k, "mean": mean,
            "std": statistics.pstdev(sv) if len(sv) > 1 else 0.0,
            "p5": p5, "p50": p50, "p95": p95, "penalty": pen,
            # Widen [p5, p95] outward by the penalty about the MEDIAN (always inside the
            # interval, unlike the mean for a skewed distribution) so the widened interval
            # always contains [p5, p95]. An under-constrained candidate reads as LESS
            # precise, never falsely sharp. Score is >= 0.
            "p5_widened": max(0.0, p50 - pen * (p50 - p5)),
            "p95_widened": p50 + pen * (p95 - p50),
            "rank1_fraction": sum(1 for x in rv if x == 1) / len(rv),
            "rank_p5": _pct(rr, 0.05), "rank_p95": _pct(rr, 0.95),
            "n": len(sv),
        })
    rows.sort(key=lambda d: (-d["mean"], d["key"]))

    # Second pass: a candidate is 'separated' only if its widened interval clears the
    # NEXT-ranked candidate's — otherwise a high rank1_fraction is just the tie-break.
    out: list[ScoreDistribution] = []
    for i, d in enumerate(rows):
        nxt = rows[i + 1] if i + 1 < len(rows) else None
        separated = nxt is None or d["p5_widened"] > nxt["p95_widened"]
        out.append(ScoreDistribution(
            key=d["key"], mean=d["mean"], std=d["std"],
            p5=d["p5"], p50=d["p50"], p95=d["p95"],
            penalty=d["penalty"], p5_widened=d["p5_widened"], p95_widened=d["p95_widened"],
            rank1_fraction=d["rank1_fraction"], rank_p5=d["rank_p5"], rank_p95=d["rank_p95"],
            separated_from_next=separated, n=d["n"], seed=seed,
        ))
    return out


def analytic_interval(key: tuple[str, str, str], config: LabConfig = DEFAULT_CONFIG,
                      elements: list[Element] | None = None,
                      frac: float = DEFAULT_RANGE_FRAC) -> tuple[float, float]:
    """First-order sensitivity interval for one candidate's ``sc_plausibility`` — central
    differences over each threshold summed in quadrature. A deterministic cross-check on the
    MC spread, not the primary estimate."""
    def score_for(cfg: LabConfig) -> float:
        for r in run_screen(elements=elements, config=cfg):
            if _key(r) == key:
                return r.sc_plausibility
        return 0.0

    base = score_for(config)
    var = 0.0
    for f in PERTURBED_FIELDS:
        d = getattr(config.thresholds, f) * frac
        up = score_for(replace(config, thresholds=replace(config.thresholds, **{f: getattr(config.thresholds, f) + d})))
        dn = score_for(replace(config, thresholds=replace(config.thresholds, **{f: getattr(config.thresholds, f) - d})))
        var += ((up - dn) / 2.0) ** 2
    delta = var ** 0.5
    return (max(0.0, base - delta), base + delta)   # sc_plausibility is >= 0
