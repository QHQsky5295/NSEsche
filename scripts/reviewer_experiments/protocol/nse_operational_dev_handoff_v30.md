# NSESche operational development handoff V30

V30 is closed. It used the preregistered, non-formal E61--E65 cohort and did
not select a candidate. E11--E20 remain sealed.

## Frozen provenance

- plan commit: `e14b3384bbf140c10ca5321864dd9e8bd7670edd`
- plan SHA-256: `dfaa81b6fbafd901db64f15af8b68a106c4bc9ac812bc999768e82ee698abf5c`
- scheduler code commit: `3c9a9fdd7423ad3ba4f03e8688409b4d2cd2a23a`
- scheduler source SHA-256: `9a9299510a6d6dc7d997144ad76a9a964f60aa808dd6e8a5ad29fefbda91031e`
- release binary SHA-256: `be4539343794e525502abcba6edee87f557dd9068ad690798fbb8f42f6d97ef9`
- result: `tmp/nse_operational_dev_20260824_v30/candidate-screen.v30-warm-gated-ordinal.json`
- result SHA-256: `eb718f5f09db5ca40b8092b7b692b5de6246bd925cd3022e53f12a2e0c214144`

All five tape captures, 15 reference builds, 45 baseline runs, and 15
candidate runs canonicalized on attempt 1. All four ledgers and all 20 paired
environment groups passed; online and reference quarantine counts were zero.
The simulator ran strictly serially and `serverless_sim/records` remained
empty.

## Revealed result

The E61--E65 baseline leaders were LoadLeast for mean fixed-window throughput
(`1.4438`) and Jiagu for mean per-run QPR (`0.0667323105`).

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V30a warm-gated singleton | 1.4304 | 3 | 0.0661384011 | 4 | no |
| V30b idle-warm-gated singleton | 1.3924 | 6 | 0.0684348663 | 1 | no |
| V30c warm-complement control | 1.4002 | 5 | 0.0679820894 | 2 | no |

No candidate strictly exceeded both baseline leaders, so no confirmation was
unsealed. Frozen V8 remains the middle/high rollback winner and frozen V11
remains the best low-load rollback candidate.

## Bounded follow-up hypothesis

V30a and V30b differ only when a singleton-demand function has a feasible warm
container but no feasible idle-warm container. In those differing windows,
E61 had roughly 41.5 queue-pressure tasks/node, E62/E63 roughly 1.8/5.5, and
E64/E65 roughly 31/21. V31 may therefore test a preregistered, outcome-blind
queue-density band router on fresh E66--E70: retain V30a under high pressure,
retain V30b under low pressure, and use the exact LoadLeast current-demand
ranking in the middle band. V30 metrics must not be used to add candidates on
E61--E65.
