# G12 Global-Ready Admission Development Experiment (Closed)

Status: `complete_g12_development_gate_failed_strong_baselines_blocked`

This directory is the permanent root-level evidence package for the closed G12
development experiment. It retains the result-free protocol lineage, exact
30-run selection, reconciliation and gate reports, append-only ledgers, audits,
and exact mechanism/analyzer source files.

G12 applied an exact `min(feasible,N)` prefix to the complete globally
collected dependency-ready sequence under the unchanged C0 legacy order. The
implementation passed all six structural invariants and stayed below the
policy-overhead cap. It produced a small middle-load improvement but failed
low/high throughput robustness, high-load QPR, the completion/latency safety
condition, and the preregistered activation threshold. High D101 alone
contributed 5,089,902 deferral observations and the severe retained
throughput/QPR tail. The candidate is not eligible for strong baselines,
confirmation, formal replay, a figure, or a paper performance claim. See
`audits/G12_GLOBAL_READY_ADMISSION_RESULT_AUDIT.md` for the complete outcome.

The complete immutable raw workspace is stored at:

`E:\NSEsche_experiment_archives\tscv1_g12_global_ready_admission_d101_d105_c4e31a9_20260904`

It contains 1,092 files and 390,090,635 bytes. Its sorted inventory SHA-256 is
`5a41481e09fa159364741b8158e385367c81920350e3a1231ffe3baaf1f1b20a`,
which exactly matches the source run root at closure.

Key commits:

- mechanism source: `c4e31a99b62012bf0fbdd48f7a6a0010d7484801`;
- final bound inputs: `1690f72c7aff5de70e5dee41bdb8855504978686`;
- frozen analyzer and zero-result selection:
  `92b7b49d778aec4f642fa7688bca4668012f13ee`.

Do not reuse D101--D105 for tuning, seed selection, or successor validation. A
future mechanism requires a distinct name, a fresh seed bank, and a committed
result-free protocol after read-only diagnosis of this retained evidence.
