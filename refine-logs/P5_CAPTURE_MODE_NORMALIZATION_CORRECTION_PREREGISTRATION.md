# P5 capture-mode normalization correction preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `third_pre_result_technical_correction_frozen`

## 1. Trigger and retained failure evidence

After the complete-fields audit commit `2b66b17`, the `11e682f`
source-bound instance attempted only the first fixed input key. All three
automatic attempts passed the adapter checks and reached Rust reset
validation, then failed before simulation with the identical error:

`admission-enabled performance/reference runs require workload replay`

The 19-file, 66,013-byte failed input tree is retained. Its four-event ledger
has SHA-256
`3e45c5abec94219631430a2315a7082f8847248e3e8c9b624a051f76b7e79fcf`
and tip
`174bcb94b2b3e7cbf7e9505f7e9b6666bdf53b01131ec6baae5f2cb272fed1b3`.
There is no tape, catalog, summary, canonical capture, algorithm result, rank,
or metric. The other eight fixed keys were not attempted.

## 2. Complete root cause

The generic `capture_base_tapes` stage deep-copies a manifest run and changes
its workload mode from replay to capture. For a P5 source run, however, it
leaves `protocol_version=reviewer-v4` and the method-neutral FCFS admission
layer enabled. Rust deliberately permits that admission layer only for replay
runs and separately requires it for every formal reviewer-v4 run. The
resulting capture-only payload is therefore internally contradictory.

Admission is an online population-control and terminal-measurement mechanism;
it cannot influence the exogenous arrival events being captured. Historical
base-tape capture uses the reviewer-v3, admission-disabled input-generation
contract, and later formal runs replay and bind the resulting tape under their
own protocol version and admission contract.

## 3. Sole authorized correction

When, and only when, `capture_base_tapes` materializes a capture-only clone of
a reviewer-v4 source run:

1. set the clone's `simulator_experiment.protocol_version` to `reviewer-v3`;
2. replace the clone's admission object with the exact Rust-default disabled
   contract:
   `enabled=false`, `policy="disabled"`,
   `drain_cpu_work_multiplier=4.0`, `minimum_drain_frames=1000`, and
   `stop_when_drained=true`; and
3. record the source protocol version and capture protocol version in the
   capture attempt metadata and receipt so the normalization is explicit.

The P5 manifest and every later replay/reference/online run remain
`reviewer-v4` with the frozen FCFS admission and bounded-drain contract. Do not
change any seed, key, workload profile, arrival horizon, method, topology,
simulation identity, scheduler, HPA, reference identity, metric, gate, result
policy, or NSESche source/equation/parameter.

Add tests proving that reviewer-v4 capture clones normalize exactly as above,
reviewer-v3 capture behavior is unchanged, source runs are not mutated, and
every P5 manifest run remains reviewer-v4 with admission enabled.

## 4. Refreeze and retry boundary

After directed and full protocol regression pass, create a new source commit,
dedicated release identity, exact zero-result manifest, and correction audit.
All three earlier source-bound failure workspaces remain exhausted and
immutable.

Only after the new audit commit may its new workspace begin one fixed-order
input-capture pass. This is not a fourth attempt under any exhausted run
identity. References, online methods, duplicate replay, analysis, figures,
and claims remain blocked.
