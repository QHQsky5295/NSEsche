# P5 common-platform analyzer and online-selection audit

Date: 2026-09-05 (Asia/Shanghai)

Parent offline-reference audit commit: `4e39293`

Selection implementation commit: `7f4bfcbf9d62bee218c49532108e0e983929d2ab`

Status: `result_blind_selection_frozen_exact_ninety_online_runs_authorized_after_commit`

## 1. Frozen analysis contract

The P5 analyzer retains the twelve-condition contract implemented before any
P5 input, reference, or online result. The new selection builder reads only
the complete ready manifest's identities and immutable dependency hashes. It
rejects selection freeze if the online parent already exists and validates
the selection against the current analyzer source hash and exact ready
manifest.

Analyzer:
`scripts/reviewer_experiments/analysis/p5_common_platform.py`

- bytes: 37,022;
- SHA-256:
  `de087cdff7e92d76069a22f62afb26e4ca70fb0f45998cf4c0148c45589d1f66`;
- gate conditions: twelve, conjunctive;
- conditions 1--11 are decided before the relative-performance appendix;
- the relative appendix is excluded from pass/fail; and
- selection/analyzer source commit:
  `7f4bfcbf9d62bee218c49532108e0e983929d2ab`.

The conditions cover exact population/runtime/input/reference identity,
arrival identity, conservation, FCFS admission, active-capacity bound,
terminal timing, metric algebra, usable completion cohort, input-traffic
interpretation, reference/NSESche integrity, one semantic determinism
duplicate, and result blindness. Throughput, QPR, method rank, and old-PDF
drift are not pass/fail conditions and cannot authorize a retry.

The 10,943-byte dedicated test file has SHA-256
`995ed725ca62fbaf889e87340241439c178601cc5fd70e103f55e14a70b8c441`.
Directed P5 protocol/analyzer tests pass 13/13 in 6.357 s. The complete
analysis suite passes 223/223 in 84.060 s. Formatting, compilation, and
`git diff --check` pass. Tests prove exact manifest-order freezing, absence of
result fields, rejection of an existing online parent, document self-hash,
and fail-closed rejection of selection-order mutation.

## 2. Exact result-blind selection

Path:
`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/p5_common_platform.online.selection.json`

- bytes: 50,808;
- file SHA-256:
  `e70dd418a48c8c5e21f2cc047dec9182ea4834442e337b8fd3aefeec89e90d8f`;
- canonical document hash:
  `b352ab183290bb1977152390189ee4c0cfe3694ab9c64d28ddbd1013bf6225ed`;
- ready-manifest file SHA-256:
  `7f9720e9dc7aa8dfe00d96e00c4d8deee8df6863d0c914d2490f51d625353d19`;
- ready-manifest canonical object hash:
  `0a02d480e583b1fba4eec97a9d1f974573406be5c8de48dae7181dd5e60de3ee`;
- 90 rows, 90 unique run IDs/spec hashes/reference hashes, nine shared tape
  hashes, and exact ordinal sequence 1--90; and
- exact order: load-major low--middle--high, seed-major P5P01--P5P03,
  method-ordinal within seed.

The P5 fixed plan previously described P5.5 as seed-major then load-major,
while the zero-result manifest, all input/reference stages, the user's
paper-order requirement, and this result-free selection consistently use
load-major then seed-major. The plan wording is corrected in this same
pre-online audit. No run, seed, method, tape, reference, parameter, result, or
gate changes.

Each selection row contains exactly ordinal/order, load, seed, method,
run ID/spec hash, tape hash, and reference hash. No row contains QPR,
throughput, rank, result, status, completion, latency, cost, or metric fields.
The builder and independent validator pass. At freeze, neither
`online/canonical` nor its `online` parent existed. The selection explicitly
records no result-conditioned selection, all-valid-run retention,
technical-retry-only handling, no scientific-outcome retry, and exclusion of
relative performance from the gate.

## 3. Authorization boundary

After this audit is committed, exactly one complete execution of the 90
selected rows is authorized in the frozen load-major, seed-major,
method-ordinal order. Every first QC-valid canonical result must be retained.
Only same-run technical retries permitted by the existing protocol may occur;
outcome-dependent seed, method, run, tape, reference, or parameter replacement
is forbidden.

The one predeclared low/P5P01/NSESche semantic duplicate is authorized only
after its canonical observation exists and cannot replace it. Gate analysis,
relative aggregation, figures, claims, and the formal paper-order rerun remain
blocked until all 90 rows, the duplicate, and the complete retained product
are independently audited.
