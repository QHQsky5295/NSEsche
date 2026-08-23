# NSESche operational development handoff V31

V31 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E66--E70 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `99c809b98478458af7a32950d8690ae7bbeaa0d6`
- plan SHA-256: `de09a6343b36a9e069a876c5271f236b59aa61fca0b524e96e9fdf6d9f5565a0`
- scheduler code commit: `11fcf7ba9d3d9b5d4a8ef30b764ba539c686505a`
- scheduler source SHA-256: `5cdd43783e347ae83325026a3b8ed5bc8ba99c8f0cfd7cda0b1fe8aba92e1848`
- release binary SHA-256: `39fdcd0d01f8fd583023fd17b4be9c46d2c0c8ae8b51ab23dd99b608d66abffd`
- result: `tmp/nse_operational_dev_20260824_v31/candidate-screen.v31-queue-banded-ordinal.json`
- result SHA-256: `67035a74edc03c965e55baeed4f3d08201e7c684f137991e5c5c82a9c195f8d4`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. Four ledger hash chains and all 20 paired
environment groups passed. Online/reference quarantine counts were zero,
execution was strictly serial, and `serverless_sim/records` remained empty.

## Revealed result

Hiku led both E66--E70 baseline metrics: mean fixed-window throughput `1.4984`
and mean per-run QPR `0.0665992351`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V31a queue-12 bands | 1.4698 | 3 | 0.0618803184 | 3 | no |
| V31b queue-8 bands | 1.4590 | 4 | 0.0593337133 | 7 | no |
| V31c queue-16 bands | 1.4546 | 5 | 0.0598455953 | 6 | no |

The threshold family is closed without subdivision. Frozen V8 remains the
middle/high rollback winner and V11 remains the best low-load rollback point.
A future fresh cohort may instead audit and repair the semantic gap between the
current outcome-blind Hiku proxy and the exact Hiku baseline, because one
baseline led both V31 metrics; it must not add candidates on E66--E70.
