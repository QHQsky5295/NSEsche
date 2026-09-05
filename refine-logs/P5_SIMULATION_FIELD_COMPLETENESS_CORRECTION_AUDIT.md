# P5 simulation-field completeness correction audit

Date: 2026-09-05 (Asia/Shanghai)

Correction preregistration commit: `14bffe2`

Correction implementation commit: `11e682f1dca08285ef592f7e9762bdf85ccbd031`

Status: `complete_fields_zero_result_protocol_frozen_tape_capture_authorized`

## 1. Exhausted instances remain closed

The `5bd817e` reviewer-v3-only-adapter instance and the `3de688c`
simulation-field-incomplete instance each retain exactly three quarantined
attempts and a terminal `capture_blocked` event. Neither contains a tape,
catalog, summary, canonical capture, online result, rank, or metric. Neither
may be resumed, promoted, or used as input.

For the second instance, the retained 19-file, 67,936-byte failure tree has a
3,270-byte ledger with SHA-256
`1cee3018fcf35415a3c54753653788e975d6af6b239108efc9d2fd85c3ecd6a6`
and tip
`49fb5024eaca86c941798034ac6818ea134b64f7759118ff239de939ed8c8c7b`.
All failures occurred after server launch but before reset, at the same missing
`dag_type` dictionary access.

## 2. Exact correction and verification

Commit `11e682f` restores the three complete inherited simulation fields to
the P5 run and marker identity:

- `dag_type="mix"`;
- `cold_start="high"`; and
- `fn_type="cpu"`.

These equal the frozen base E1/default protocol values. No other run field,
source path, Rust code, method, NSESche equation/parameter, admission/drain
rule, metric, QC rule, or analyzer condition changed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/p5_common_platform.py` | 12,666 | `cddc50265f330c0b0ca995d21b4c03c5205dd0118d46d676a07eede777fb1295` |
| `protocol/schema.py` | 306,377 | `8d364643666fbd95ed798b8277846c4b1be88aeb992679cf762505120bb76bdb` |
| `protocol/tests/test_p5_common_platform.py` | 10,530 | `490d00d0fa0bc1fd93b970ff56cd3c9b6f6e7c2572053a7207398027f15a157a` |
| `protocol/tests/test_serverless_adapter.py` | 7,576 | `ad868433cb05805465081e4c26a86e5d473db16ee18c515d2ff5944d46698dfc` |
| correction preregistration | 2,524 | `22e31f632e841f2a49d06ebfe640c15b0a22b8c4a6da746605ac18fb5f5c05dc` |

Directed P5/adapter/analyzer tests pass 19/19 in 7.417 s. The full protocol
suite passes 286/286 in 778.251 s. Tests prove the complete reset payload,
exact three-field identity on every P5 run, and fail-closed rejection when any
one field changes. Python formatting/compilation and `git diff --check` pass.
The Rust and analysis implementation is otherwise byte-identical to the
earlier P5 audit and retains its P5 9/9, NSESche 61/61, and analysis 221/221
evidence.

## 3. Complete-fields release and zero-result manifest

The source-bound release is:

- path:
  `serverless_sim/target_p5_common_platform_complete_fields_impl/release/serverless_sim.exe`;
- source commit: `11e682f1dca08285ef592f7e9762bdf85ccbd031`;
- bytes: 5,013,504; and
- SHA-256:
  `128f895f97b2de7f255ed533762e3fd74acfabb152caf3db80d277100fe43a8d`.

The new zero-result manifest is:

`runs/tscv1_p5_common_platform_p5p01_p5p03_11e682f_20260905/p5_common_platform.manifest.json`

- bytes: 2,224,993;
- file SHA-256:
  `64c39bd96422dc725e4b609864940f81be062a3a51418041953f65a9d851562c`;
- canonical object hash:
  `bd08b507a57559aa005bd049c5336832bb0e27fe452537fb75ac41aa7f767412`;
- 90 unique run IDs/specs, nine unique tape keys, and 90 unique references;
- manifest and every run bind `mix/high/cpu`;
- tape, FaaSRank, and reference bindings all remain false;
- generic, dedicated P5, and static JSON Schema validation pass; and
- its directory contains only the manifest.

The manifest has no tape, reference, result, rank, selection, metric, or
paper-eligible row.

## 4. Authorization boundary

After this audit commit, exactly nine input-only tapes may be captured from
the `11e682f` manifest in a new workspace, one key at a time in fixed
low--middle--high, then P5P01--P5P03 order. The first QC-valid capture for each
key is canonical. Both prior workspaces remain closed.

After all nine tapes are independently validated and hash-bound, the existing
FaaSRank artifact may be bound only after proving training/evaluation tape
disjointness. Reference construction, online methods, duplicate replay,
analysis, figures, and claims remain blocked pending a committed input audit.
