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
from .avenue import Avenue, METRIC_RANGES

_GEOMETRY_BUILDERS = {
    "monomer": lambda el: make_monomer(el),
    "dimer": lambda el: make_dimer(el),
    "linear_chain": lambda el: make_linear_chain(el, 4),
    "compact_cluster": lambda el: make_compact_cluster(el, 13),
}


def validate_runnable(avenue: Avenue) -> tuple[bool, str]:
    """Check an avenue can be run WITHOUT raising: known falsification metric,
    resolvable element symbols, known geometry kinds.

    The production generator is an untrusted LLM subagent; a hallucinated element
    ("Nb"), geometry ("hypercube"), or metric name would otherwise raise deep in
    the run and abort the whole loop. The loop calls this at proposal intake and
    skips (never runs) an avenue that fails, so one bad proposal can't discard the
    in-progress session. Returns (ok, reason)."""
    m = avenue.falsification.metric
    if m not in METRIC_RANGES:
        return False, f"unknown falsification metric {m!r}"
    for sym in avenue.action.elements:
        try:
            get_element(sym)
        except Exception:
            return False, f"unknown element {sym!r}"
    for kind in avenue.action.geometry_kinds:
        if kind not in _GEOMETRY_BUILDERS:
            return False, f"unknown geometry kind {kind!r}"
    return True, ""


@dataclass(frozen=True)
class AvenueResult:
    avenue: Avenue
    records: tuple[CandidateRecord, ...]
    metrics: dict[str, float]
    epw_status: str = "not_requested"


_METRIC_KEYS = (
    "max_sc_plausibility", "max_coupling", "max_field_suppression", "n_survivors",
    "max_sc_tc_kelvin", "max_sc_lambda",
    # Real screen quantities exposed so falsifiers can faithfully test the
    # anisotropy/stability/carrier/isolation hypotheses (H1/H2/H3/H5/H6), not
    # just the SC-gate aggregate. All are toy-model quantities → Level-2 triage.
    "max_anisotropy", "max_structural_stability", "max_carrier_proxy", "n_isolated",
    "max_em_coherence_score",
)


def _metrics(records: tuple[CandidateRecord, ...]) -> dict[str, float]:
    if not records:
        return {k: 0.0 for k in _METRIC_KEYS}

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
        "max_anisotropy": _max("anisotropy"),
        "max_structural_stability": _max("structural_stability"),
        "max_carrier_proxy": _max("carrier_proxy"),
        "n_isolated": float(sum(1 for r in records if r.isolated)),
        "max_em_coherence_score": _max("em_coherence_score"),
    }


def run_avenue(
    avenue: Avenue,
    config: LabConfig = DEFAULT_CONFIG,
    backend=None,
    screen_fn=run_screen,
    epw_backend=None,
) -> AvenueResult:
    """Run ``avenue``'s action grid through the screen and compute its metrics.

    The avenue's field/temperature override the base ``config``. ``screen_fn`` is
    injectable so tests can stub the screen; it defaults to the real pipeline.
    """
    action = avenue.action
    run_config = replace(
        config,
        applied_field_t=action.applied_field_t,
        temperature_k=action.temperature_k,
        compute_em_coherence=action.use_em,
    )
    elements = [get_element(sym) for sym in action.elements]

    def geometry_factory(el):
        return [_GEOMETRY_BUILDERS[k](el) for k in action.geometry_kinds]

    use_epw = avenue.action.use_epw
    effective_backend = backend
    epw_available = False
    if use_epw and epw_backend is not None:
        epw_available = epw_backend.available()
        if epw_available:
            effective_backend = epw_backend

    # Restrict spin states to those named in the action (the screen computes both;
    # we keep only the requested subset).
    wanted = set(action.spin_labels)
    records = [
        r for r in screen_fn(
            elements=elements, config=run_config,
            geometry_factory=geometry_factory, backend=effective_backend,
        )
        if r.spin_label in wanted
    ]
    records_t = tuple(records)
    # A genuine EPW computation carries source "epw" (Tc computed) or
    # "epw:unstable" (real moments, Tc nulled) -- both produced an alpha^2 F.
    # "epw:failed" is an errored run and must NOT read as success; "n/a"/"toy"
    # mean EPW never ran (binaries absent / geometry not applicable).
    if not use_epw:
        epw_status = "not_requested"
    elif any(r.sc_source in ("epw", "epw:unstable") for r in records_t):
        epw_status = "ran"
    elif any(r.sc_source == "epw:failed" for r in records_t):
        epw_status = "failed"
    else:
        epw_status = "unavailable"
    return AvenueResult(avenue=avenue, records=records_t, metrics=_metrics(records_t), epw_status=epw_status)
