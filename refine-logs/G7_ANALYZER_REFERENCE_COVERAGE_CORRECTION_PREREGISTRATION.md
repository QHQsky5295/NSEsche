# G7 analyzer reference-coverage correction preregistration

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Base commit: `54fd50524dabf9899c780eb35d800a6dba920393`  
Status: first analyzer invocation retained as failed; one reporting-only
correction is authorized

## Trigger and retained product

All five fixed D71--D75 G7 online runs completed on attempt 1, passed protocol
QC, and were canonicalized. The append-only ledger validates with 12 events.
No simulator retry, seed substitution, or result deletion occurred.

The first and only invocation of the frozen analyzer exited 1 before writing
`g7.selection.json`:

```text
protocol error: G6 reference state key is not a nonnegative integer
```

The error text is inherited from a G6 helper. Read-only structural inspection
found that it was caused by valid JSON `null`, not a malformed integer. The
active-window reference shapes are:

| Seed | Active windows | Offline-table hits | `not_requested`/null windows |
|---|---:|---:|---:|
| D71 | 992 | 992 | 0 |
| D72 | 988 | 981 | 7 |
| D73 | 987 | 984 | 3 |
| D74 | 993 | 991 | 2 |
| D75 | 993 | 991 | 2 |

Each null row has `reference_source="not_requested"`,
`reference_state_key=null`, `reference=null`, and no cache hit. The 14-row
shortfall exactly equals active windows minus the matching offline-reference
table records. The scheduler requests the reference only after a stable inner
solve, so these rows are a real absence of required offline-reference coverage.
No throughput, QPR, latency, completion, cost, solve-time, or frontier result
was used to define the correction.

Frozen product receipts:

| Artifact | SHA-256 |
|---|---|
| `g7.ready.json` | `4e285e025a1612480177ad1b2bcab52f4a0fe28886abca2186441cf75bd39567` |
| `online/ledger.jsonl` | `b16dc654f8070074df454e1deeb3b22b1e270d84b8661d3d0e3b5c512bb6aa81` |
| pre-correction `g7_frontier_warm.py` | `7447321c4677279c54c566ffb901e498553775e533f95424f08973c8935c8136` |
| pre-correction G7 tests | `2d3d2d29962f34768fbf72970a787ec85958d81a135259a3c7320bacc1a03c29` |

`g7.selection.json` did not exist at freeze time.

## Frozen correction

The correction may change only G7 analysis/reporting code and directed tests:

1. Every active window still must have a complete assignment, exact
   assigned/prepared/sent counts, zero invalid assignments, and no dispatch
   channel failure.
2. A covered window must have `reference_source="offline_table"`, a
   nonnegative integer state key, and a finite reference value.
3. The only noncovered shape accepted for counting is exactly
   `reference_source="not_requested"` with null state key and null reference,
   false cache hit, and false feedback eligibility. Any missing field,
   different source, partial reference, or inconsistent flag still raises a
   protocol error.
4. Candidate rows will report `active_window_count`,
   `offline_reference_hit_windows`, and
   `unreferenced_active_window_count`.
5. The gate will add an explicit per-seed condition requiring hits to equal
   active windows and unreferenced count to equal zero. Therefore the observed
   14-window deficit is guaranteed to fail; the correction cannot turn it into
   a pass.
6. Existing frontier, warm-start, performance, completion, latency, runtime,
   dispatch, formula, source-binding, seed, and all-retained gates remain
   byte-for-byte or semantically unchanged.

Directed tests must cover a fully referenced pass, exact `not_requested` rows
as a reported gate failure, and malformed/mismatched reference shapes as
fail-closed errors. G6 and general protocol regressions must still pass.

## Authorization boundary

After the correction and tests are separately audited and committed, exactly
one analyzer retry is authorized on the unchanged five canonical G7 runs and
the unchanged 50 frozen G3 controls. No simulator/reference rerun, source
mechanism change, seed extension, threshold change, confirmation, formal cell,
figure, or paper claim is authorized. The retry must retain and report the
reference-coverage failure even if all performance metrics are favorable.
