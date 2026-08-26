"""Result-blind execution protocol for the reviewer experiments."""

from .formal_e1_shard import (
    derive_formal_e1_heterogeneous_shard,
    derive_formal_e1_homogeneous_shard,
)
from .formal_e2_shard import derive_formal_e2_weak_scaling_shard
from .formal_e2_nsesche_overlay import derive_formal_e2_nsesche_overlay
from .formal_e3_e4_extension_shard import derive_formal_e3_e4_ci_extension_shard
from .formal_e3_e4_shard import derive_formal_e3_e4_initial_shard
from .formal_e5_e6_extension_shard import derive_formal_e5_e6_ci_extension_shard
from .formal_e5_e6_e7_shard import derive_formal_e5_e6_e7_initial_shard
from .matrix import build_manifest, load_protocol_config
from .qc import QCReport, evaluate_attempt
from .runner import ProtocolRunner
from .schema import ProtocolValidationError, validate_manifest
from .sla import freeze_sla_targets, inspect_pilot_metric
from .sla_pilots import run_isolated_sla_pilots
from .smoke_shard import derive_integration_smoke_shard
from .technical_timeout_recovery import (
    E2_ORIGINAL_RUNTIME_IDENTITY,
    TechnicalTimeoutRecoveryError,
    TechnicalTimeoutRecoveryRunner,
    build_recovery_manifest,
    merge_timeout_recovery,
    plan_timeout_recovery,
    plan_timeout_recovery_tier2,
    validate_timeout_recovery_plan,
)

__all__ = [
    "ProtocolRunner",
    "ProtocolValidationError",
    "QCReport",
    "E2_ORIGINAL_RUNTIME_IDENTITY",
    "TechnicalTimeoutRecoveryError",
    "TechnicalTimeoutRecoveryRunner",
    "build_manifest",
    "build_recovery_manifest",
    "derive_formal_e1_heterogeneous_shard",
    "derive_formal_e1_homogeneous_shard",
    "derive_formal_e2_weak_scaling_shard",
    "derive_formal_e2_nsesche_overlay",
    "derive_formal_e3_e4_ci_extension_shard",
    "derive_formal_e3_e4_initial_shard",
    "derive_formal_e5_e6_ci_extension_shard",
    "derive_formal_e5_e6_e7_initial_shard",
    "derive_integration_smoke_shard",
    "evaluate_attempt",
    "freeze_sla_targets",
    "inspect_pilot_metric",
    "load_protocol_config",
    "merge_timeout_recovery",
    "plan_timeout_recovery",
    "plan_timeout_recovery_tier2",
    "run_isolated_sla_pilots",
    "validate_manifest",
    "validate_timeout_recovery_plan",
]
