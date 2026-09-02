"""Shared fail-closed validation for NSESche's Eq. (16)--(20) control trace."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Mapping


G0_SEMANTICS_CONTRACT_SCHEMA = "eq14_eq16_eq19_semantics_v1"
OUTER_FEEDBACK_TRACE_SCHEMA = "eq16_eq19_control_path_v1"
STRICT_EQ15_CANDIDATES = frozenset({"formula", "ready_order", "ready_finish_tie"})
STRICT_FORMULA_ALIGNMENT = "paper_Eqs_1_20_strict_argmax"
STRICT_EQ15_SEMANTICS = "strict_argmax_with_current_node_preferred_on_numerical_ties"
REFERENCE_PRICE_BASIS = "immutable_window_baseline_prices"
FEEDBACK_NASH_PRICE_BASIS = "current_outer_adjusted_prices"
PRICE_FEEDBACK_UPDATE_BASIS = "immutable_window_baseline_prices_not_recursive"
NETWORK_BETA_SOURCE = "active_transfer_remaining_time_by_directed_link_proxy"
NETWORK_BETA_DOMAIN = "finite_beta_ge_1_unclipped_no_global_upper_bound"
GAP_WELFARE_BASIS = "final_assignment_evaluated_at_immutable_baseline_prices"
RUST_EPSILON = 1.0e-6


def _finite(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return math.nan
    converted = float(value)
    return converted if math.isfinite(converted) else math.nan


def _nested(value: Mapping[str, Any], *keys: str) -> Any:
    current: Any = value
    for key in keys:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


@dataclass
class FeedbackTraceValidation:
    """Validated reductions plus exact row-level failure evidence."""

    present: bool = False
    trace_rounds: int = 0
    feedback_applied_rounds: int = 0
    invalid_rows: int = 0
    control_gaps: list[float] = field(default_factory=list)
    gammas: list[float] = field(default_factory=list)
    price_multipliers: list[float] = field(default_factory=list)
    assignment_changes: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.present and self.invalid_rows == 0 and not self.errors


def validate_runtime_contract_config(
    event: Mapping[str, Any],
    *,
    expected_candidate: str | None = None,
    expected_r0: float | None = None,
) -> list[str]:
    """Return errors for a declared G0 semantics contract.

    Legacy streams that do not declare ``g0_semantics_contract_schema`` are
    intentionally outside this contract.  Callers decide whether declaration
    is mandatory for their stage.
    """

    errors: list[str] = []
    if event.get("g0_semantics_contract_schema") != G0_SEMANTICS_CONTRACT_SCHEMA:
        errors.append("invalid g0 semantics contract schema")
    if event.get("v") != 2 or event.get("kind") != "run_config":
        errors.append("invalid NSESche run_config envelope")
    if event.get("scheduler") != "sche_nash":
        errors.append("invalid NSESche run_config scheduler")

    candidate = event.get("operational_refinement")
    if expected_candidate is not None and candidate != expected_candidate:
        errors.append("run_config operational candidate differs from manifest")
    if candidate not in STRICT_EQ15_CANDIDATES:
        errors.append("corrected-runtime candidate is not strict Eq. (15)")
    if event.get("strict_best_response") is not True:
        errors.append("strict_best_response is not true")
    if event.get("formula_alignment") != STRICT_FORMULA_ALIGNMENT:
        errors.append("formula alignment is not strict Eqs. (1)--(20)")
    if event.get("eq15_selection_semantics") != STRICT_EQ15_SEMANTICS:
        errors.append("Eq. (15) selection semantics are not strict argmax")
    if event.get("utility_guard_relative_regret") is not None:
        errors.append("a bounded-regret utility guard is active")
    if event.get("outer_feedback_trace_schema") != OUTER_FEEDBACK_TRACE_SCHEMA:
        errors.append("invalid outer feedback trace schema")
    if event.get("reference_price_basis") != REFERENCE_PRICE_BASIS:
        errors.append("invalid offline reference price basis")
    if event.get("feedback_nash_welfare_price_basis") != FEEDBACK_NASH_PRICE_BASIS:
        errors.append("invalid feedback Nash-welfare price basis")
    if event.get("empirical_gap_price_basis") != REFERENCE_PRICE_BASIS:
        errors.append("invalid empirical-gap price basis")
    if event.get("price_feedback_update_basis") != PRICE_FEEDBACK_UPDATE_BASIS:
        errors.append("Eq. (19) price update is not bound to baseline prices")
    if event.get("network_beta_source") != NETWORK_BETA_SOURCE:
        errors.append("invalid Eq. (14) network-beta source")
    if event.get("network_beta_effective_domain") != NETWORK_BETA_DOMAIN:
        errors.append("invalid Eq. (14) network-beta effective domain")
    if event.get("network_proxy_is_physical_rtt") is not False:
        errors.append("network proxy is incorrectly represented as physical RTT")
    observed_r0 = _finite(event.get("r0"))
    if not math.isfinite(observed_r0) or observed_r0 < 0.0:
        errors.append("invalid Eq. (20) r0")
    elif expected_r0 is not None and not math.isclose(
        observed_r0, expected_r0, rel_tol=1.0e-6, abs_tol=1.0e-8
    ):
        errors.append("run_config Eq. (20) r0 differs from manifest")
    return errors


def validate_outer_feedback_event(
    event: Mapping[str, Any],
    *,
    require_contract_basis: bool = False,
    expected_r0: float | None = None,
) -> FeedbackTraceValidation:
    """Validate one window's loop-local Eq. (16)/(19) trace.

    The first outer round must use the immutable baseline prices.  Every
    applied update must reproduce ``1 + gamma * beta * gap``, and the next
    stable round must consume that exact multiplier.  Invalid rows are never
    repaired or silently omitted.
    """

    result = FeedbackTraceValidation()
    solver = event.get("solver")
    if not isinstance(solver, Mapping) or "outer_feedback_trace" not in solver:
        return result
    result.present = True
    raw_trace = solver.get("outer_feedback_trace")
    if not isinstance(raw_trace, list):
        result.invalid_rows = 1
        result.errors.append("outer_feedback_trace is not an array")
        return result

    if require_contract_basis:
        social = event.get("social")
        pricing = event.get("pricing")
        if not isinstance(social, Mapping):
            result.errors.append("window has no social object")
        else:
            if social.get("gap_welfare_basis") != GAP_WELFARE_BASIS:
                result.errors.append("invalid empirical-gap welfare basis")
            feedback_basis = social.get("feedback_gap_welfare_basis")
            if (
                not isinstance(feedback_basis, Mapping)
                or feedback_basis.get("reference")
                != "offline_estimate_at_immutable_baseline_prices"
                or feedback_basis.get("nash")
                != "inner_equilibrium_at_current_outer_adjusted_prices"
            ):
                result.errors.append("invalid feedback-gap welfare basis")
        if not isinstance(pricing, Mapping):
            result.errors.append("window has no pricing object")

    network_beta = _finite(_nested(event, "pricing", "network_beta"))
    global_load = _finite(_nested(event, "pricing", "global_load_g"))
    observed_r0 = _finite(_nested(event, "pricing", "price_adjustment_factor_r0"))
    if raw_trace and (not math.isfinite(network_beta) or network_beta < 1.0 - 1.0e-6):
        result.invalid_rows += 1
        result.errors.append("network beta is not finite and at least one")
    gamma_inputs_valid = (
        math.isfinite(global_load)
        and global_load >= 0.0
        and math.isfinite(observed_r0)
        and observed_r0 >= 0.0
    )
    if require_contract_basis and not gamma_inputs_valid:
        result.errors.append("window cannot revalidate Eq. (20) gamma")
    if (
        expected_r0 is not None
        and math.isfinite(observed_r0)
        and not math.isclose(observed_r0, expected_r0, rel_tol=1.0e-6, abs_tol=1.0e-8)
    ):
        result.errors.append("window Eq. (20) r0 differs from run_config")
    expected_gamma = (
        observed_r0 * math.tanh(global_load) if gamma_inputs_valid else math.nan
    )

    previous_hash: int | None = None
    previous_next_multiplier = math.nan
    for expected_round, raw_round in enumerate(raw_trace, start=1):
        if not isinstance(raw_round, Mapping):
            result.invalid_rows += 1
            result.errors.append(f"outer round {expected_round} is not an object")
            continue
        round_number = raw_round.get("outer_round")
        assignment_hash = raw_round.get("assignment_hash")
        applied = raw_round.get("feedback_applied")
        current_multiplier = _finite(
            raw_round.get("price_multiplier_for_current_round")
        )
        if not (
            isinstance(round_number, int)
            and not isinstance(round_number, bool)
            and round_number == expected_round
            and isinstance(assignment_hash, int)
            and not isinstance(assignment_hash, bool)
            and assignment_hash >= 0
            and isinstance(applied, bool)
            and math.isfinite(current_multiplier)
            and current_multiplier > 0.0
        ):
            result.invalid_rows += 1
            result.errors.append(f"outer round {expected_round} has invalid identity")
            continue
        if expected_round == 1 and not math.isclose(
            current_multiplier, 1.0, rel_tol=1.0e-5, abs_tol=1.0e-8
        ):
            result.invalid_rows += 1
            result.errors.append("first outer round does not use baseline prices")
            continue
        if math.isfinite(previous_next_multiplier) and not math.isclose(
            current_multiplier,
            previous_next_multiplier,
            rel_tol=1.0e-5,
            abs_tol=1.0e-8,
        ):
            result.invalid_rows += 1
            result.errors.append(
                f"outer round {expected_round} does not consume the prior multiplier"
            )
            continue

        reference = _finite(raw_round.get("reference_welfare_at_baseline_prices"))
        nash_welfare = _finite(raw_round.get("nash_welfare_at_current_prices"))
        gap = _finite(raw_round.get("feedback_gap"))
        expected_gap = math.nan
        if (
            math.isfinite(reference)
            and reference > RUST_EPSILON
            and math.isfinite(nash_welfare)
            and nash_welfare <= reference + RUST_EPSILON
        ):
            expected_gap = max(0.0, (reference - nash_welfare) / reference)
        if math.isfinite(expected_gap):
            if not (
                math.isfinite(gap)
                and math.isclose(gap, expected_gap, rel_tol=1.0e-5, abs_tol=1.0e-8)
            ):
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} has an invalid Eq. (16) gap"
                )
                continue
            result.control_gaps.append(gap)
        elif math.isfinite(gap):
            result.invalid_rows += 1
            result.errors.append(
                f"outer round {expected_round} has a gap without an eligible reference"
            )
            continue

        gamma = _finite(raw_round.get("gamma"))
        if math.isfinite(gamma):
            if gamma < 0.0:
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} has a negative gamma"
                )
                continue
            if math.isfinite(expected_gamma) and not math.isclose(
                gamma, expected_gamma, rel_tol=1.0e-5, abs_tol=1.0e-8
            ):
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} has an invalid Eq. (20) gamma"
                )
                continue
            result.gammas.append(gamma)
        next_multiplier = _finite(raw_round.get("price_multiplier_for_next_round"))
        if applied:
            if not (
                math.isfinite(gap)
                and math.isfinite(gamma)
                and math.isfinite(network_beta)
                and math.isfinite(next_multiplier)
                and next_multiplier > 0.0
            ):
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} has an incomplete Eq. (19) update"
                )
                continue
            expected_multiplier = 1.0 + gamma * network_beta * gap
            if not math.isclose(
                next_multiplier,
                expected_multiplier,
                rel_tol=1.0e-5,
                abs_tol=1.0e-8,
            ):
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} has an invalid Eq. (19) multiplier"
                )
                continue
            result.feedback_applied_rounds += 1
            previous_next_multiplier = next_multiplier
            result.price_multipliers.append(next_multiplier)
        else:
            if math.isfinite(next_multiplier):
                result.invalid_rows += 1
                result.errors.append(
                    f"outer round {expected_round} exposes an unapplied next multiplier"
                )
                continue
            previous_next_multiplier = math.nan

        result.price_multipliers.append(current_multiplier)
        if previous_hash is not None:
            result.assignment_changes.append(float(assignment_hash != previous_hash))
        previous_hash = assignment_hash
        result.trace_rounds += 1

    return result
