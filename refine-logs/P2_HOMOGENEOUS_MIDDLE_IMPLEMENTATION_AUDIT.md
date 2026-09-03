# P2 Homogeneous-Middle Zero-Result Implementation Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: `implementation_and_selection_frozen_online_authorized_once`

## 1. Scope and zero-result boundary

This audit closes the implementation-only stage preregistered in
`P2_HOMOGENEOUS_MIDDLE_PREREGISTRATION.md`. At selection freeze and throughout
the tests below, the registered online root

`runs/tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904/`

did not exist. No homogeneous-middle scientific process had been launched and
no middle-load outcome was available to the selection, analyzer, alignment
specification, tests, or figure builder.

The parent revision commit was
`aedfc9273f5eeac136fd627c51bc2e0f29fcfea0`. The preserved runtime remains
source commit `98f822cf2dcb878024a2ca39cc56533895ea692c`, binary SHA-256
`7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`,
and 4,707,328 bytes. No paper equation, NSESche parameter, scheduling
candidate, workload tape, reference table, baseline model, or retry rule was
changed.

## 2. Frozen selection

`P2_HOMOGENEOUS_MIDDLE_SELECTION.json` was generated once from the complete
ready manifest and then independently revalidated.

- file SHA-256:
  `3d72f9fdb51461b89f7e59ce652e1966ebda2cff1a8fe5440fc6c41d5c7b2d04`;
- document SHA-256:
  `6f6a8682448b64fd4b21f3a8536270fb735a2072c56b4ebd8c0ffe21b09a0a18`;
- exactly 200 unique run IDs and 200 unique run-specification hashes;
- exactly 20 runs for each of the ten submitted-paper methods;
- exactly ten methods for each seed Q61--Q80;
- exactly 20 hash-checked paired tapes and 20 complete state-matched NSESche
  offline references;
- one hash-checked frozen FaaSRank artifact and one preserved runtime binary;
- `scientific_metric_values_consulted=false` and
  `result_conditioned_seed_or_run_selection=false`.

The selection validator also rechecks all P1/V4 authorization receipts, the
retained low-load report, the full 1,200-run source manifest, method/seed
product, NSESche `ready_order`/strict-Eq.-(15) contract, `(r0=0.5,wq=0.6)`,
four-inner/two-outer limits, and every bound input hash before execution.

## 3. Analysis and figure contract

The result analyzer accepts only the hash-consistent G1 integrity report for
this exact selection and canonical root. It recomputes and verifies run-level
QPR from throughput, drained-cohort mean latency, and internal cost. It writes
all 200 rows, 50 method/metric summaries, the frozen 18-member paired primary
comparison family, and 40 old-PDF alignment rows. The default analysis uses
10,000-resample BCa intervals, 100,000 paired sign flips, one Holm family,
paired effect sizes, wins/ties/losses, and paired relative-change intervals.

The V4 rule is executable rather than interpretive: NSESche enters the
possible-stop branch only if its mean rank is 6--10 for both throughput and
QPR; the stop is confirmed only if both paired-difference BCa upper endpoints
against the corresponding fifth-ranked method are strictly negative. Missing
QPR remains in the 200-row result and blocks progression. No result directly
authorizes high load; a non-stop outcome only permits a separate high-load
preregistration after the middle result audit.

The submitted Fig. 6 diagnostic was frozen before outcomes with source PDF
SHA-256
`03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`,
page 9, render coordinates, four axis conversions, ten bar centers, and the
submitted method order. Its specification SHA-256 is
`caea79e0b748992cc79f777470634d242ccd655655f9c9deab12d74f11d5a916`.
The approximate bars cannot control run acceptance, retry, parameter choice,
or seed retention; a difference of at least 15% is only a whole-scene
provenance diagnostic.

The new middle-cell figure has two primary-metric panels, displays every
finite run point plus mean and run-level 95% BCa interval, uses 182 mm width,
an opaque background, vector PDF/SVG, and a 900-dpi PNG. NSESche is redundantly
encoded as a blue filled diamond and baselines as gray open circles, preserving
meaning in grayscale without relying on color alone.

## 4. Frozen source hashes

| Source | SHA-256 |
|---|---|
| `protocol/p2_homogeneous.py` | `cbd0cbf01c4071adf89d284605d4cc6bd56985a7c4f7747a70b4c7f2e731cec4` |
| protocol directed tests | `25b74b7e99b284eda28d8ac8ff9ae8e33282767c0fad66ca584e55451255df45` |
| `analysis/p2_homogeneous.py` | `2c47d2cfb3712789bda9b11ae289247514353dcb723646931995768f7ab33dd4` |
| analysis directed tests | `7b67ac9fca81eb8e9560defac2865e583b3aedf208d38cdf85d262ad707579b2` |
| old Fig. 6 coordinate specification | `caea79e0b748992cc79f777470634d242ccd655655f9c9deab12d74f11d5a916` |
| `figures/p2_cell.py` | `a75c50565ac89d08e63aae426ee9597cf1a2e01bdf74f06b6d4336c4046c6c29` |
| figure test package marker | `ec8ea7241ef7712d780e2f35b2beaceff7ba3a6db664d91ba4ac2a6cb2783e75` |
| figure directed test | `59441132d09c62bc5d665ae1275be3e00ad3a14a0b2a5dab075d99e21c5b7c19` |

## 5. Verification

The required interpreter was `D:\Anaconda3\python.exe`.

- compilation and Black formatting checks passed for all new Python sources;
- the seven focused P2 selection/statistics/figure tests passed;
- the complete protocol suite passed `209/209` in 801.527 s;
- the complete analysis suite passed `92/92` in 87.684 s;
- the P2 figure suite passed `1/1` in 0.432 s;
- total full-suite outcome: `302/302` passed;
- `git diff --check` passed;
- the selection revalidation passed after serialization;
- the protected low-load workspace and all protected runtime target trees were
  untouched.

Warnings were limited to existing dependency deprecations and legacy PDF font
metadata messages; there were no test failures.

## 6. Narrow authorization

After this audit and all frozen sources are committed together, exactly one
execution of the 200-run selection is authorized. On completion, the workflow
must perform result-blind canonical-path reconciliation, write the unchanged G1
integrity report, invoke the P2 analyzer once, render the figure once, and
commit a result audit with all source/table/figure hashes. Every first QC-valid
result is canonical even if scientifically unfavorable.

No homogeneous-high, heterogeneous, ablation, sensitivity, scaling, burst,
QoS, pricing/welfare, native, fault, extra-stress, or soak run is authorized by
this document.
