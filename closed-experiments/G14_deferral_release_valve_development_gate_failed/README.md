# G14 Deferral Release-Valve Development Experiment (Closed)

Status: `complete_g14_development_gate_failed_strong_baselines_blocked`

This directory is the permanent root-level evidence package for the closed
G14 development experiment. It retains the result-free protocol lineage,
exact 30-run selection, reconciliation and gate reports, append-only ledgers,
audits, and exact mechanism/analyzer source files.

G14 bounds only the first window of each consecutive overflow episode, then
releases the complete global feasible-ready legacy sequence while overflow
persists. The implementation passed the complete state-machine activation
contract and stayed below the policy-overhead cap. It improved mean
throughput/QPR by 1.9%/1.8% at low load and 15.1%/27.1% at high load, but
middle-load throughput was 0.49% below C0 and the low/middle paired joint-win
counts were only 2/5 and 0/5. The candidate failed five of nine frozen
conditions and is not eligible for strong baselines, confirmation, formal
replay, a figure, or a paper performance claim. See
`audits/G14_DEFERRAL_RELEASE_VALVE_RESULT_AUDIT.md` for the complete outcome.

The complete immutable raw workspace is stored at:

`E:\NSEsche_experiment_archives\tscv1_g14_deferral_release_valve_d106_d110_64d36b7_20260904`

It contains 1,092 files and 396,182,667 bytes. Its sorted inventory SHA-256 is
`fdb9706343dd4871e49c75be0cd7a2f81f15e095b9ea7aacf65d4ba04de59b63`,
which exactly matches the source run root at closure.

Key commits:

- mechanism source: `64d36b7b0fc6aa441283cb3b6c6115c8ba1d834b`;
- final bound inputs: `b03f6c8965a2ed08a2c35d9e71e8ac9572eaa089`;
- frozen analyzer: `4da9b196cd11be443db239931ac15a721ad5ab8a`;
- zero-result online selection: `728b15d11db34371cb3526e2d9f555f042b89714`.

Do not reuse D106--D110 for tuning, seed selection, or successor validation.
Any future mechanism requires a distinct name, a fresh seed bank, and a
committed result-free protocol after a read-only diagnosis of this retained
evidence.
