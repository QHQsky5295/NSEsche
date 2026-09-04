# P5 adapter version-allowlist correction preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `pre_result_technical_correction_frozen`

## 1. Trigger and retained failure evidence

After commit `24985f6`, the first authorized input-only capture was invoked for
`steady.low.homogeneous.mixed.P5P01.2dd3147eb8b8`. The generic capture stage
used its fixed maximum of three automatic technical attempts. All three were
quarantined with exit code 2 before the simulator launched, with the identical
adapter message:

`formal adapter requires simulator protocol_version=reviewer-v3`

Attempt durations were 1.578, 1.610, and 1.734 seconds. The immutable ledger
contains three `capture_quarantined` events followed by
`capture_blocked`. There is no tape catalog, workload-tape file, summary,
canonical capture, algorithm result, rank, or metric observation. The other
eight tape keys were not attempted.

## 2. Root cause

The Rust runtime, manifest/schema validator, QC, and P5 tests intentionally
accept the new `reviewer-v4` protocol. The Python adapter's workload-profile
preflight still contains the historical equality check
`protocol_version == reviewer-v3`. This is an integration allowlist omission,
not a scheduler, admission, workload, reference, metric, or statistical
failure.

## 3. Sole authorized correction

Change `_verify_workload_frequency_profile` in
`protocol/serverless_adapter.py` so the exact accepted set is
`{reviewer-v3, reviewer-v4}`. Preserve all workload-profile identity, load,
path, SHA-256, profile-ID, profile-set, and DAG-frequency checks unchanged.
Continue rejecting every other protocol version.

Add directed tests proving:

1. an otherwise valid `reviewer-v4` binding is accepted;
2. an otherwise valid `reviewer-v3` binding remains accepted; and
3. an unknown version is rejected before runtime launch.

No other source, manifest field, seed, tape key, execution order, attempt
policy, admission rule, drain rule, method, NSESche equation/parameter, QC
condition, metric, analyzer gate, or result policy may change.

## 4. Refreeze and retry boundary

After implementation and regression tests, create a new source commit, a new
dedicated release identity, and a new zero-result manifest whose run IDs/specs
bind that corrected source. Preserve the failed `5bd817e` capture tree as
technical provenance; do not edit, delete, promote, or retry it.

Only after a committed correction audit may the new manifest make one fresh
fixed-order capture pass in a new workspace. This is a new source-bound
technical protocol instance, not a fourth attempt on the exhausted old run.
Reference construction, online methods, duplicate replay, analysis, figures,
and claims remain blocked.
