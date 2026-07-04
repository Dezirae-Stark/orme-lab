"""The retireable-claim registry and per-hypothesis scope predicates.

Some hypotheses are element/geometry-specific truths, so a single binary switch
would wrongly retire them globally on the first counterexample. H1 and H3 are
split into scoped variants that retire independently. The scope boundary is the
real ``Element.d_shell_vacancies`` property (H1) / geometry kind (H3) -- grounded,
not invented: d_shell_vacancies exactly predicts the toy anisotropy class
(closed-shell d10 -> 0.0; open-shell -> 0.165-0.458).
"""

from __future__ import annotations

from ..elements import get_element
from .avenue import Avenue

#: The retireable claims. H1/H3 are element/geometry-scoped; the rest are global.
HYPOTHESES: tuple[str, ...] = (
    "H1-open-shell", "H1-closed-shell",
    "H2",
    "H3-cluster", "H3-monomer",
    "H4", "H5", "H6", "H7", "H12", "H16",
)


def _all_elements_open_shell(action) -> tuple[bool, str]:
    """H1-open-shell: every element must have an open d-shell (d_shell_vacancies > 0)."""
    if not action.elements:
        return False, "scope mismatch: H1-open-shell has no elements to classify"
    for sym in action.elements:
        if get_element(sym).d_shell_vacancies == 0:
            return False, (f"scope mismatch: H1-open-shell requires open-shell "
                           f"(d_shell_vacancies>0) elements, got closed-shell {sym}")
    return True, ""


def _all_elements_closed_shell(action) -> tuple[bool, str]:
    """H1-closed-shell: every element must be closed-shell (d10, d_shell_vacancies == 0)."""
    if not action.elements:
        return False, "scope mismatch: H1-closed-shell has no elements to classify"
    for sym in action.elements:
        if get_element(sym).d_shell_vacancies != 0:
            return False, (f"scope mismatch: H1-closed-shell requires closed-shell "
                           f"(d10) elements, got open-shell {sym}")
    return True, ""


def _all_geoms(kind: str):
    def _pred(action) -> tuple[bool, str]:
        if not action.geometry_kinds:
            return False, f"scope mismatch: requires geometry {kind!r}, got none"
        for g in action.geometry_kinds:
            if g != kind:
                return False, (f"scope mismatch: requires geometry {kind!r}, got {g!r}")
        return True, ""
    return _pred


#: scoped-hypothesis id -> predicate(action) -> (ok, reason). Absent id == unscoped.
SCOPE_PREDICATES: dict[str, callable] = {
    "H1-open-shell": _all_elements_open_shell,
    "H1-closed-shell": _all_elements_closed_shell,
    "H3-cluster": _all_geoms("compact_cluster"),
    "H3-monomer": _all_geoms("monomer"),
}


def validate_scope(avenue: Avenue) -> tuple[bool, str]:
    """Whether a scoped avenue's action matches its hypothesis's element/geometry
    class. Unscoped hypotheses always pass. A scoped variant with a reason string
    on mismatch is skipped honestly by the loop (never run)."""
    pred = SCOPE_PREDICATES.get(avenue.targeted_hypothesis)
    if pred is None:
        return True, ""
    ok, reason = pred(avenue.action)
    if not ok and avenue.targeted_hypothesis not in reason:
        reason = f"{avenue.targeted_hypothesis}: {reason}"
    return ok, reason
