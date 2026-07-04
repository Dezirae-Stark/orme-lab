"""The executable experiment spec an avenue is, plus its falsification condition.

An ``Avenue`` is a *proposal* the creative generator emits and the deterministic
core judges. It carries everything needed to run one experiment and to decide,
before running, whether it is falsifiable and non-tautological. Data + validation
only; no execution lives here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum


class Tier(IntEnum):
    """Action-space tier. Tier 3 (auto-prototype new mechanisms) is walled off."""

    TIER1 = 1  # vary existing model inputs + EPW/EM toggles
    TIER2 = 2  # + sanctioned coupling channels
    TIER3 = 3  # + auto-prototype a new mechanism (quarantined, not run)


class Comparator(Enum):
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="


#: Achievable range of each metric the falsification condition may reference.
#: ``max_sc_tc_kelvin`` is capped at a generous toy ceiling so "fireable" is
#: decidable; the EPW toy path never exceeds it.
METRIC_RANGES: dict[str, tuple[float, float]] = {
    "max_sc_plausibility": (0.0, 1.0),
    "max_coupling": (0.0, 1.0),
    "max_field_suppression": (0.0, 1.0),
    "n_survivors": (0.0, 1000.0),
    "max_sc_tc_kelvin": (0.0, 1000.0),
    "max_sc_lambda": (0.0, 10.0),
    # Real screen quantities (toy-model, gate-internal) exposed for faithful
    # falsification of the anisotropy/stability/carrier/isolation hypotheses.
    "max_anisotropy": (0.0, 1.0),
    "max_structural_stability": (0.0, 1.0),
    "max_carrier_proxy": (0.0, 1.0),
    "n_isolated": (0.0, 1000.0),
    "max_em_coherence_score": (0.0, 1.0),
}


@dataclass(frozen=True)
class FalsificationCondition:
    """A declarative, serializable falsification predicate on one run metric.

    Declarative (metric/comparator/threshold) rather than an arbitrary callable
    so that (a) it can be checked for *fireability* without running anything and
    (b) it round-trips through the ledger JSON.
    """

    metric: str
    comparator: Comparator
    threshold: float

    def fireable(self) -> bool:
        """True iff the threshold lies strictly inside the metric's range, so the
        condition can come out both true and false over the action space. A
        condition that can never fire is a 'validation that cannot fail'."""
        if self.metric not in METRIC_RANGES:
            raise ValueError(f"unknown metric: {self.metric!r}")
        lo, hi = METRIC_RANGES[self.metric]
        return lo < self.threshold < hi

    def evaluate(self, metrics: dict[str, float]) -> bool:
        """Whether the condition FIRES given a run's metric values."""
        if self.metric not in metrics:
            raise ValueError(f"metric {self.metric!r} not in run metrics")
        v = metrics[self.metric]
        t = self.threshold
        return {
            Comparator.LT: v < t,
            Comparator.LE: v <= t,
            Comparator.GT: v > t,
            Comparator.GE: v >= t,
        }[self.comparator]


@dataclass(frozen=True)
class ActionSpec:
    """The knobs one avenue varies. All fields are inert data."""

    elements: tuple[str, ...]
    geometry_kinds: tuple[str, ...]        # {monomer, dimer, linear_chain, compact_cluster}
    spin_labels: tuple[str, ...]           # {high_spin, low_spin}
    applied_field_t: float
    temperature_k: float
    use_epw: bool
    use_em: bool
    coupling_channel: str | None           # tier-2: {nanocluster, josephson, oxide_salt, light_matter}


@dataclass(frozen=True)
class Avenue:
    """A single proposed experiment."""

    id: str
    tier: Tier
    description: str
    targeted_hypothesis: str
    action: ActionSpec
    falsification: FalsificationCondition
    predictor_invariants: tuple[str, ...]
    provenance: str


@dataclass(frozen=True)
class MechanismProposal:
    """A tier-3 proposal. NEVER a finding — quarantined pending human review."""

    id: str
    description: str
    rationale: str
    provenance: str
    status: str = "pending operator + red-team review"
