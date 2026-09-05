"""Timing- and diagnostic-neutral P5 policy-action semantics."""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from typing import Any

from .util import object_hash


P5_POLICY_ACTION_DECISION_FIELDS = (
    "initial_assignment_hash",
    "assignment_hash",
    "complete_assignment",
    "assigned_players",
    "assigned_node_count",
    "commands_prepared",
    "commands_sent",
    "scale_ups_prepared",
    "scale_ups_sent",
    "dispatch_channel_failed",
    "invalid_assignments",
    "no_feasible_players",
    "waiting_for_candidate_nodes",
)


def p5_policy_action_payload(decision: Mapping[str, Any]) -> dict[str, Any]:
    """Return only fields that determine or attest the emitted policy action."""

    return {field: decision.get(field) for field in P5_POLICY_ACTION_DECISION_FIELDS}


def update_p5_policy_action_digest(
    digest: Any,
    window_ordinal: int,
    decision: Mapping[str, Any],
) -> None:
    if window_ordinal <= 0:
        raise ValueError("P5 policy window ordinal must be positive")
    digest.update(
        f"{window_ordinal}:{object_hash(p5_policy_action_payload(decision))}\n".encode(
            "ascii"
        )
    )


def p5_policy_action_sequence_hash(
    decisions: Iterable[Mapping[str, Any]],
) -> str:
    digest = hashlib.sha256()
    count = 0
    for count, decision in enumerate(decisions, start=1):
        update_p5_policy_action_digest(digest, count, decision)
    if count == 0:
        raise ValueError("P5 policy action sequence is empty")
    return digest.hexdigest()
