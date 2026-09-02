"""Result-blind execution protocol for the reviewer experiments."""

from .formal_e1_shard import (
    derive_formal_e1_heterogeneous_shard,
    derive_formal_e1_homogeneous_shard,
)
from .formal_e2_shard import derive_formal_e2_weak_scaling_shard
from .formal_e3_e4_extension_shard import derive_formal_e3_e4_ci_extension_shard
from .formal_e3_e4_shard import derive_formal_e3_e4_initial_shard
from .formal_e5_e6_extension_shard import derive_formal_e5_e6_ci_extension_shard
from .formal_e5_e6_e7_shard import derive_formal_e5_e6_e7_initial_shard
from .matrix import build_manifest, load_protocol_config
from .m1_development import (
    build_m1_development_manifest,
    derive_m1_candidate_screen_shard,
)
from .m1_completion_guard import (
    analyze_m1_completion_guard_screen,
    build_m1_completion_guard_manifest,
    derive_m1_completion_guard_qualification_shard,
    derive_m1_completion_guard_screen_shard,
)
from .m1_diagnosis import derive_m1_mechanism_diagnosis_shard
from .m1_qualification import (
    analyze_m1_candidate_screen,
    derive_m1_qualification_shard,
)
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
    "build_m1_completion_guard_manifest",
    "build_m1_development_manifest",
    "build_recovery_manifest",
    "analyze_m1_candidate_screen",
    "analyze_m1_completion_guard_screen",
    "derive_formal_e1_heterogeneous_shard",
    "derive_formal_e1_homogeneous_shard",
    "derive_formal_e2_weak_scaling_shard",
    "derive_formal_e3_e4_ci_extension_shard",
    "derive_formal_e3_e4_initial_shard",
    "derive_formal_e5_e6_ci_extension_shard",
    "derive_formal_e5_e6_e7_initial_shard",
    "derive_integration_smoke_shard",
    "derive_m1_candidate_screen_shard",
    "derive_m1_completion_guard_qualification_shard",
    "derive_m1_completion_guard_screen_shard",
    "derive_m1_mechanism_diagnosis_shard",
    "derive_m1_qualification_shard",
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
