# V58 experiment plan

V58 tests one mechanism-level hypothesis on untouched E220--E224: prioritize
the parent-complete ready frontier by shortest outcome-blind remaining workflow
work, then apply one of four frozen placement experts. The order directly
targets completed-workflow throughput and latency without reading completion
outcomes; warm-aware placement also targets the simulator cost denominator.

The exact machine-readable contract is
`scripts/reviewer_experiments/protocol/nse_operational_dev_plan_v58.json`.
It fixes four candidates, nine paired baselines, three loads, five seeds, 15
tapes, 60 references, 195 strictly serial online runs, simultaneous reveal,
and a strict per-load rank-one gate for throughput and both QPR conventions.

V57 remains a failed immutable confirmation and its E210--E219 metrics are not
used to choose V58 candidates. E225--E229 remain untouched reserve. No source,
binary, tape, or run may be created for E220--E224 until this plan is committed.
