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
    rank1_fraction: float       # fraction of draws where this candidate ranked #1
    rank_p5: float
    rank_p95: float
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

    out: list[ScoreDistribution] = []
    for k, sv in scores.items():
        ss = sorted(sv)
        rv = ranks[k]
        rr = sorted(rv)
        out.append(ScoreDistribution(
            key=k,
            mean=statistics.fmean(sv),
            std=statistics.pstdev(sv) if len(sv) > 1 else 0.0,
            p5=_pct(ss, 0.05), p50=_pct(ss, 0.50), p95=_pct(ss, 0.95),
            rank1_fraction=sum(1 for x in rv if x == 1) / len(rv),
            rank_p5=_pct([float(x) for x in rr], 0.05),
            rank_p95=_pct([float(x) for x in rr], 0.95),
            n=len(sv), seed=seed,
        ))
    out.sort(key=lambda d: (-d.mean, d.key))
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
    return (base - delta, base + delta)
