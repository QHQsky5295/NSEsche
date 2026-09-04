# G16 Overflow-Magnitude Valve Development Experiment (Closed)

Status: `complete_g16_development_gate_failed_strong_baselines_blocked`

This directory is the permanent root-level evidence package for the closed
G16 development experiment. It retains the result-free protocol lineage,
exact 30-run selection, reconciliation and gate reports, append-only ledgers,
audits, and exact mechanism/analyzer source files.

G16 bounds the first overflow window only when the exact widened-integer
predicate `4F>=5N` passes; below-threshold first overflow and every adjacent
overflow release the complete feasible-ready legacy sequence. The
implementation passed the complete activation contract and stayed below the
policy-overhead cap. It improved mean throughput/QPR by 0.77%/0.81% at low
load and 3.06%/10.29% at high load, but middle throughput/QPR were
5.55%/1.01% below C0. Low and middle recorded only three joint nonlosses each,
middle D112 violated both per-seed floors, and middle completion was lower.
The candidate passed three of nine frozen conditions and is not eligible for
strong baselines, confirmation, formal replay, a figure, or a paper
performance claim. See
`audits/G16_OVERFLOW_MAGNITUDE_VALVE_RESULT_AUDIT.md` for the complete outcome.

The complete immutable raw workspace is stored at:

`E:\NSEsche_experiment_archives\tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904`

It contains 1,092 files and 395,532,897 bytes. Its sorted inventory SHA-256 is
`28a7d5a16592e928e4c63d11901f76629c75d8a5041d69955baec12e36f04c9f`,
which exactly matches the source run root at closure.

Key commits:

- mechanism source: `8da3dbdc9694e683889e5448bead908e288093fa`;
- final bound inputs: `7711f85815c579276eb0d2cd409d8f34d57ec47a`;
- frozen analyzer: `563f68da95694d51b58de9f9b0c9642f4004134e`;
- zero-result online selection: `1975555c786b4a7b2b542e46da9d8790539c8d5a`.

Do not reuse D111--D115 for tuning, seed selection, or successor validation.
Any future mechanism requires a distinct name, a fresh seed bank, and a
committed result-free protocol after a read-only diagnosis of this retained
evidence.
