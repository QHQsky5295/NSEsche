# P5 simulation-field completeness correction preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `second_pre_result_technical_correction_frozen`

## 1. Trigger and retained failure evidence

After the adapter allowlist audit commit `44e24ff`, the corrected source-bound
instance attempted only the first fixed tape key. All three automatic attempts
passed workload-profile verification and launched the simulator, then failed
before reset or simulation with the identical traceback:

`KeyError: 'dag_type'` in `serverless_adapter._full_config`.

The 19-file, 67,936-byte failed capture tree is retained. Its four-event
ledger has SHA-256
`1cee3018fcf35415a3c54753653788e975d6af6b239108efc9d2fd85c3ecd6a6`
and tip
`49fb5024eaca86c941798034ac6818ea134b64f7759118ff239de939ed8c8c7b`.
There is no tape catalog, workload tape, summary, canonical capture, algorithm
result, rank, or metric. The other eight keys were not attempted.

## 2. Complete root cause

`_bind_p5_contract` replaced the base run's complete `simulation` object with
the new dynamic-terminal fields. The replacement unintentionally omitted all
three nonterminal fields consumed by `_full_config`:

- `dag_type="mix"`;
- `cold_start="high"`; and
- `fn_type="cpu"`.

These are exactly the frozen values in `default_protocol.json` and the base E1
run from which every P5 run is derived. The first missing dictionary access
masked the next two; source inspection establishes the complete missing set
before any further launch.

## 3. Sole authorized correction

Add those exact three inherited values to `P5_SIMULATION`. Do not change any
dynamic-terminal field, workload profile, load, seed, method, topology,
admission/drain rule, scheduler, HPA, reference, metric, gate, or result
policy.

Add tests proving that:

1. every P5 run freezes all three exact values;
2. `_full_config` materializes a complete reset payload for a P5 run without a
   missing-field exception; and
3. manifest mutation of any one of the three fields fails closed.

## 4. Refreeze and retry boundary

After directed and full protocol regression pass, create a new source commit,
dedicated release identity, exact zero-result manifest, and correction audit.
Both earlier source-bound failure workspaces remain exhausted and immutable.

Only after the new audit commit may its new workspace begin one fixed-order
input-capture pass. This is not a retry of either exhausted run identity.
References, online methods, duplicate replay, analysis, figures, and claims
remain blocked.
