"""Static tautology oracle over ``CandidateRecord`` fields.

The superconductivity AND-gate consumes five inputs — coupling, carrier proxy,
field suppression, structural stability, observable signal — each a deterministic
function of a small set of upstream quantities. Any predictor drawn only from
this closure is, by construction, re-derivable from the gate's own inputs: a
'finding' expressed in those terms is a tautology. Genuinely off-gate signals
today are the EPW electron-phonon block (an external computation) and the
EM-coherence channel (a distinct physical signal, independent of the SC gate).

This set is PINNED. If the model changes so the gate consumes a new field, the
golden test in ``test_closure.py`` breaks loudly — which is the point.
"""

from __future__ import annotations

#: Fields inside the AND-gate's transitive input closure (gate inputs + the
#: quantities they are computed from + the observables that feed observable_signal).
GATE_INPUT_CLOSURE: frozenset[str] = frozenset({
    # the five gate inputs
    "coupling", "carrier_proxy", "field_suppression",
    "structural_stability", "observable_signal",
    # upstream feeders (see pipeline.evaluate_candidate)
    "anisotropy", "is_ricebean", "spin_polarization",
    "meissner_screening", "susceptibility", "resistance_regime",
    # derived gate outputs
    "sc_plausibility", "ruled_out",
})

#: Fields NOT reachable from the gate inputs — genuinely independent signal.
#: The EPW electron-phonon block and the EM-coherence channel.
OFF_GATE_INVARIANTS: frozenset[str] = frozenset({
    "sc_tc_kelvin", "sc_lambda", "sc_omega_log_k", "sc_gap_mev", "sc_mu_star",
    # Electromagnetic-coherence channel (H12/H16): a distinct, independent signal
    # from the SC AND-gate. This is what makes H12/H16 genuinely (not formally)
    # testable in the lab loop.
    "em_coherence_score", "em_regime", "em_rabi_ev", "em_lifetime_fs",
    # Phase-identity gate (G_identity): established by an external characterization
    # witness (XRD/XPS/ICP-MS/EXAFS), NOT re-derivable from the SC AND-gate's inputs.
    # (`credited_sc_lead` is a composite of gate ∧ identity and is deliberately in
    # neither set.)
    "identity_verdict", "identity_established",
    # Hudson optical-coherence channel (Branch B): a distinct, independent signal
    # from the SC AND-gate — the resonantly-accessible hybrid light-matter mode, its
    # persistence, and its claim-level ladder. Never re-derivable from the gate inputs.
    "hudson_regime", "hudson_photon_fraction", "hudson_persistence",
    "hudson_highest_claim", "hudson_supported_levels",
})


def is_independent(predictor_invariants) -> bool:
    """True iff the predictors reference at least one off-gate invariant.

    An avenue that passes this is claiming something not definitionally implied
    by the AND-gate's own inputs. An avenue that fails is tautological.
    """
    return bool(OFF_GATE_INVARIANTS.intersection(predictor_invariants))
