# G13 deferral-persistence diagnosis result audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `3a88c3768693a710dcf2e89555c9ac5091cd73e1`

Analyzer freeze commit: `3dd01d7173bccb168884831bc976d31183434b09`

Status: `complete_deferral_release_valve_preregistration_authorized`

## Decision

The single preregistered read-only invocation completed over all 15 retained
G12/C0 D101--D105 pairs. All five frozen conditions pass. The retained
evidence therefore authorizes a separate preregistration for exactly one
load-blind, parameter-free `deferral_release_valve` successor.

This result does not authorize an implementation or any simulator execution.
It is a mechanism-selection diagnostic, not formal evidence, a causal claim,
or a paper result. G12 remains a closed negative development experiment, and
all of its valid favorable, tied, and unfavorable observations remain
retained.

## Frozen product and integrity

The analyzer revalidated the exact G12 source root before extracting any
features: 1,092 files, 390,090,635 bytes, sorted inventory SHA-256
`5a41481e09fa159364741b8158e385367c81920350e3a1231ffe3baaf1f1b20a`.
It also revalidated the bound manifest, online selection, gate report,
62-event ledger, every canonical run inventory, and all same-tape pairings.

Run output:
`runs/tscv1_g13_deferral_persistence_diagnosis_from_g12_20260904`.
It contains one file and 124,669 bytes with inventory SHA-256
`1015d8389a73609e2c1ea19bebd565cc18046d8b310d43c022b8525491659ef5`.
An exact mirror exists at
`E:/NSEsche_experiment_archives/tscv1_g13_deferral_persistence_diagnosis_from_g12_20260904`
with the same file list, byte count, and inventory hash.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `g13.report.json` | 124,669 | `45c4560892cf83860fc930b1b6e7c3c88dca9f22878498d4040f7bda4c31f556` |

The report's stored canonical document SHA-256 is
`42c258f264801eeb75df0d5df594e311cab5c6131e11c693f7b43e0a2bfad77b`
and independently reproduces after removing that field. Coverage is exactly
15 run-level feature rows and 15 artifact receipts. All six structural
violation totals are zero in every row. Four runs have no activation, three
have isolated-only activation, and eight have persistent activation; no row
is discarded or imputed. High-load D103 retains its recorded one-window
inner-limit/runtime exception and remains in every applicable summary.

## Frozen group comparison

| Group | Runs | Loads | Joint wins | Win rate | Mean log throughput ratio | Mean log QPR ratio |
|---|---:|---|---:|---:|---:|---:|
| isolated-only | 3 | low, middle | 3 | 1.000 | +0.002745 | +0.012870 |
| persistent | 8 | low, middle, high | 1 | 0.125 | -0.021869 | -0.087693 |
| isolated minus persistent | -- | -- | -- | +0.875 | +0.024614 | +0.100563 |

The isolated-only runs are low D102 and middle D102--D103. The persistent
group contains low D104, middle D101 and D105, and all five high-load runs.
The one persistent joint win, middle D101, is retained; exact throughput/QPR
ties are retained as nonwins by the frozen rule.

All 15 leave-one-run-out recomputations preserve positive throughput and QPR
mean-log contrasts. The smallest contrasts occur after omitting high D101 and
remain +0.011890 for throughput and +0.032711 for QPR. Thus the admission
decision does not depend on retaining the extreme high-D101 tail. Independent
arithmetic recomputation from all emitted feature rows matches the report.

## Descriptive coherence

Persistent-transition fraction has overall Spearman association -0.5827 with
paired log throughput ratio and -0.6838 with paired log QPR ratio. The signs
remain negative in every leave-one-run-out calculation. Longest positive
episode similarly has overall coefficients -0.4972 and -0.5073. These are
descriptive, non-causal associations and are not used as paper evidence.

The raw sequence evidence also explains why G12's fixed prefix was unsafe.
High D101 has a 992-window longest episode and contributes 5,089,902 deferred
feasible-player observations; other persistent runs range from three to 200
windows in their longest episodes. In contrast, every isolated-only run has
exactly one positive window. This supports testing a stateful escape from
continued bounding without selecting a load, seed, fitted threshold, or
outcome-conditioned branch.

## Authorization boundary

The five frozen conditions pass respectively: exact pair/integrity coverage;
minimum group sizes and load coverage; higher isolated-only joint-win rate;
positive mean-log primary contrasts; and positive contrasts under every
defined leave-one-run-out calculation. Therefore only
`deferral_release_valve_preregistration_authorized=true`.

The report correctly keeps all of the following false:

- `implementation_authorized`;
- `sampling_authorized`;
- `confirmation_sampling_authorized`;
- `formal_progression_authorized`; and
- `paper_claim_eligible`.

Before source changes, the successor must be defined in a new immutable
preregistration. In particular, its one-bit state transition must be fully
implementable and deterministic: it may use the current global feasible-ready
count and node count, but not outcomes, load labels, seeds, learned thresholds,
baseline experts, or post-hoc seed selection. Fresh seeds are required for its
first validation.

## Verification

- Analyzer: 27,471 bytes, SHA-256
  `77b42a1ea26e8126a527921d92fba8f902805f8b4ead9ff666bc61f75b6359fe`.
- Directed G13 tests: 9/9 passed.
- Complete analysis regression: 135/135 passed in 102.248 seconds.
- Python compilation and Black formatting checks passed before invocation.
- Exactly one real analyzer invocation was made; it created no tape,
  reference, simulator output, seed extension, figure, or paper claim.

