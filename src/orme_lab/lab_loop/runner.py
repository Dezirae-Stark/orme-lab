"""Deterministically execute one avenue through the existing screen and reduce
its records to the scalar metrics the falsification condition and objective use.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from ..config import DEFAULT_CONFIG, LabConfig
from ..elements import get_element
from ..geometry import (
    make_compact_cluster, make_dimer, make_linear_chain, make_monomer,
)
from ..pipeline import CandidateRecord, run_screen
from .avenue import Avenue

_GEOMETRY_BUILDERS = {
    "monomer": lambda el: make_monomer(el),
    "dimer": lambda el: make_dimer(el),
    "linear_chain": lambda el: make_linear_chain(el, 4),
    "compact_cluster": lambda el: make_compact_cluster(el, 13),
}


@dataclass(frozen=True)
class AvenueResult:
    avenue: Avenue
    records: tuple[CandidateRecord, ...]
    metrics: dict[str, float]


def _metrics(records: tuple[CandidateRecord, ...]) -> dict[str, float]:
    if not records:
        return {
            "max_sc_plausibility": 0.0, "max_coupling": 0.0,
            "max_field_suppression": 0.0, "n_survivors": 0.0,
            "max_sc_tc_kelvin": 0.0, "max_sc_lambda": 0.0,
        }

    def _max(attr: str) -> float:
        vals = [getattr(r, attr) for r in records if getattr(r, attr) is not None]
        return float(max(vals)) if vals else 0.0

    return {
        "max_sc_plausibility": _max("sc_plausibility"),
        "max_coupling": _max("coupling"),
        "max_field_suppression": _max("field_suppression"),
        "n_survivors": float(sum(1 for r in records if not r.ruled_out)),
        "max_sc_tc_kelvin": _max("sc_tc_kelvin"),
        "max_sc_lambda": _max("sc_lambda"),
    }


def run_avenue(
    avenue: Avenue,
    config: LabConfig = DEFAULT_CONFIG,
    backend=None,
    screen_fn=run_screen,
) -> AvenueResult:
    """Run ``avenue``'s action grid through the screen and compute its metrics.

    The avenue's field/temperature override the base ``config``. ``screen_fn`` is
    injectable so tests can stub the screen; it defaults to the real pipeline.
    """
    action = avenue.action
    run_config = replace(
        config, applied_field_t=action.applied_field_t, temperature_k=action.temperature_k,
    )
    elements = [get_element(sym) for sym in action.elements]

    def geometry_factory(el):
        return [_GEOMETRY_BUILDERS[k](el) for k in action.geometry_kinds]

    # Restrict spin states to those named in the action.
    from ..pipeline import _spin_states  # reuse the canonical spin builders

    wanted = set(action.spin_labels)
    records = [
        r for r in screen_fn(
            elements=elements, config=run_config,
            geometry_factory=geometry_factory, backend=backend,
        )
        if r.spin_label in wanted
    ]
    records_t = tuple(records)
    return AvenueResult(avenue=avenue, records=records_t, metrics=_metrics(records_t))
