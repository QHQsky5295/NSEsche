# G2 Protocol, Runtime, and Unbound-Manifest Freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: protocol and runtime frozen; unbound data-empty manifest validated;
D66--D70 input-only capture is authorized; no online result is authorized yet

## 1. Frozen identities

- Candidate implementation commit:
  `3ae7792782adcef60a254fa7c6bdb60a43d8171d`.
- Protocol implementation commit:
  `5926c99d35f7788140d40f6bbcb4f879033f88ad`.
- Release executable:
  `serverless_sim/target_g2_init_3ae7792/release/serverless_sim.exe`.
- Executable SHA-256:
  `18f5f85ac6bd5276948709ed1c0abc42dfdb4c070fbd63af6cd0a00cb19c810d`.
- Executable bytes: 4,740,096.
- Rust-source drift from the candidate implementation commit through the
  protocol commit: zero files.

The release build completed from the frozen Rust source. Existing compiler
warnings are the repository's pre-existing unused-code and naming warnings;
the release build exited successfully.

## 2. Exact development product

The dedicated G2 protocol freezes:

- candidates C0 `ready_order`, C1 `ready_warm_init`, and C2
  `ready_finish_init`;
- topologies homogeneous and heterogeneous;
- loads low, middle, and high;
- seeds exactly D66--D70;
- 90 candidate online runs and 90 candidate-specific reference builds;
- nine frozen baseline methods on homogeneous-low only, 45 online runs;
- exactly 30 shared workload tapes and 135 total online runs;
- no formal-result eligibility and no result-conditioned extension, seed
  deletion, replacement, or rerun.

The analyzer requires all 135 canonical QC-valid runs and complete run-level
QPR. It first applies the frozen twelve-ratio global maximin candidate rule.
It authorizes a new disjoint formal bank only if the selected candidate also
strictly exceeds every one of the nine homogeneous-low baselines in both mean
throughput and mean QPR. Old-PDF alignment remains a separate diagnostic and
cannot select the candidate or weaken a baseline.

## 3. Verification

- Dedicated G2 tests: 6/6 passed.
- Affected protocol regression group: 71/71 passed.
- Dynamic-contention legacy regression: 7/7 passed.
- Complete protocol suite: 185/185 passed.
- Complete analysis suite: 48/48 passed.
- Black formatting check: passed for all modified Python files.
- CLI help exposes `g2-initialization-development` and
  `analyze-g2-initialization`.
- Ruff was not installed in the frozen Anaconda environment; no Ruff result is
  claimed and no dependency was installed.

The shared runtime-contract validator now recognizes C1/C2 as strict Eq. (15)
only when their schema version is 4 and their exact initialization semantics
match the frozen contract. The G2 analyzer additionally requires schema 4 and
the candidate-specific semantics for C0/C1/C2, plus nonnegative integer
initialization counters in every policy window.

## 4. Unbound manifest and zero-data boundary

Run root:
`runs/tscv1_g2_init_d66_d70_3ae7792_20260903`.

Unbound manifest:
`g2.initialization.unbound.json`.

- Manifest document hash:
  `afcb15ccfc3ed7da20846e60d5e899400422d3a2bb6a6107ee3085b201cb7d19`.
- Manifest file SHA-256:
  `d182155aaafe61641a7ac565f396a84d1260a79c4e8295e36bd7fb414e5db7c9`.
- Validated counts: 135 runs, 27 cells, 90 reference dependencies.
- `all_faasrank_models_bound=false`; tapes and references are unbound.
- Immediately after creation the run root contained exactly one entry: the
  unbound manifest. No tape, reference, online result, QC report, or ledger
  existed.

The next legal operation is input-only capture of exactly the 30 D66--D70
base-tape keys. The frozen FaaSRank model may then be bound, followed by all 90
reference builds. Online candidate or baseline execution remains prohibited
until the ready manifest validates all three dependency classes.

