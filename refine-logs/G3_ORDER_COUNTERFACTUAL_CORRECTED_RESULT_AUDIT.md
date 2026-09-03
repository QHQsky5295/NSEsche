# G3 Corrected Order-Counterfactual Result Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: **COMPLETE VALID DIAGNOSTIC**; E0 alone may be carried into a separate
operational-candidate preregistration. This document does not authorize D71,
homogeneous-middle formal execution, or any paper performance claim.

## 1. Frozen inputs and execution closure

The corrected diagnostic uses the preregistered 50-run source bank without
changing any workload tape, seed, reference, source result, topology, load,
configuration, equation, order definition, or reporting stratum. The only
runtime change is the preregistered observation-only E0 incumbent correction
at source commit:

`166689339c66f81c72ea90cbf1e8fbf532c37064`

The repeated ready manifest is:

`runs/tscv1_g3_ordercf_e0fix_q61q80_d66d70_1666893_20260903/g3.order-counterfactual.ready.json`

- document hash:
  `df5d293d5f2e6eb500373943fa649f523cd582c29bbe417cff7ac258e0163bbb`;
- file SHA-256:
  `1082c38334a9b6fb2fa78b05aa5acd200303952678af2b47bf66425deb5ce2e7`;
- frozen executable SHA-256:
  `6a05e0b17ea6cad3aaeccf7fa257794e1e31c6f3c55d5b7b776fda8225db4ac3`.

All 50 declared replays completed and canonicalized on attempt 1. No run was
deleted, replaced, selected, or rerun. Result-blind reconciliation reports 50
exact paths and zero reconciled paths; it explicitly records
`scientific_process_reexecuted=false` and
`scientific_metric_values_used_for_selection=false`.

- reconciliation document hash:
  `adad5ea75741cae49b3a9991ff00ee3acc1f5c8ce213e71df56759cfc45d81ca`;
- reconciliation file SHA-256:
  `dccb425a7a800ee1309b9470a9ab0e56766a3506aa6f533fdd3fcbc2d2892a04`;
- ledger: 102 events, valid final event hash
  `6b8501aca3814e882ab1ab0c291fd44e48188f41a96f627c803b0d5c8820634e`;
- ledger file SHA-256:
  `51c22807f04042b09cd16a899f5919f85d31b8c5fc31ed099446fd89f18822e8`;
- quarantine: zero.

The runner retains 50 empty `online/partial` directories after successful
promotion. They contain zero files and zero bytes; they are not incomplete
observations and do not affect the evidence set.

## 2. Frozen analyzer integrity result

Analyzer V2 returned `status=complete_valid_diagnostic` and
`integrity_passed=true`:

- declared/canonical runs: 50/50;
- run-summary rows: 300;
- raw diagnostic streams: 50,000;
- exported order/window rows: 300,000;
- missing or unexpected runs: zero;
- live-C0 source-parity errors: zero;
- diagnostic errors: zero;
- decision feedback: false for every stream;
- O0 reconstruction, first-inner parity, stable completion, and independent
  strict-PNE certification gates: all passed.

The primary analysis artifact is
`runs/tscv1_g3_ordercf_e0fix_q61q80_d66d70_1666893_20260903/analysis_v2/g3.order-counterfactual.analysis.json`
with SHA-256
`ea43d53f0ef91a256b2f6d4f673ede3c1c4eeef8dce36e00d6012b7c97c4d07a`.
The complete raw stream SHA-256 is
`dc77ff57ba55a895a73d38a527bc82120890cfc05b1cb34b8577e71d7c38b72b`;
the 300,000-row CSV SHA-256 is
`635f556d5e5bc4188f4bb35a8c725a77b03f0d5e3913f47503939bc4f8b59fa6`.

## 3. Preregistered proxy result

Across the 50 runs, O0 and E0 have the following equal-weighted run means:

| Mechanism | Welfare/player | Startup burden/player | Projected finish/player | Different assignment fraction | Added bad windows |
|---|---:|---:|---:|---:|---:|
| O0 `ready_order` | 36.791628 | 29.932931 | 246.726684 | 0 | 0 |
| E0 envelope | 36.798107 | 29.694490 | 245.643183 | 0.290415 | 0 |

Thus E0 changes about 29.04% of comparable assignments, increases the proxy
welfare mean by about 0.0176%, reduces startup burden by about 0.7965%, and
reduces projected finish by about 0.4392%. The small welfare increase is not
the selection objective beyond satisfying the frozen noninferiority envelope.

The direction is consistent in every preregistered stratum:

| Stratum | Runs | Different (%) | Welfare delta (%) | Startup delta (%) | Projected-finish delta (%) | Added bad windows |
|---|---:|---:|---:|---:|---:|---:|
| G1 Q homogeneous-low | 20 | 25.620 | +0.0110 | -0.8215 | -0.4003 | 0 |
| G2 homogeneous-low | 5 | 20.640 | +0.0121 | -0.6267 | -0.4700 | 0 |
| G2 homogeneous-middle | 5 | 30.180 | +0.0209 | -0.7437 | -0.5308 | 0 |
| G2 homogeneous-high | 5 | 45.897 | +0.0267 | -0.8453 | -0.4335 | 0 |
| G2 heterogeneous-low | 5 | 14.860 | +0.0114 | -0.7262 | -0.7331 | 0 |
| G2 heterogeneous-middle | 5 | 31.920 | +0.0314 | -0.6786 | -0.5167 | 0 |
| G2 heterogeneous-high | 5 | 44.458 | +0.0313 | -1.0945 | -0.3540 | 0 |

Over all 50,000 windows, E0 selects O0 31,582 times and a non-O0 ordering
18,418 times: service scarcity 6,284, reverse ready 5,286, capacity scarcity
3,632, and resource impact 3,216. A non-O0 selection can converge to the same
assignment as O0; 14,523 all-window records have a different assignment.
Consequently, the diagnostic supports the adaptive constrained envelope, not
hard-coding one alternative order.

All fixed single-order alternatives O1--O4 are ineligible because each adds
bad windows (7, 12, 10, and 25 overall, respectively) and fails one or more
preregistered cross-stratum gates. E0 passes every frozen gate: it differs in
all seven strata, lowers both burden proxies overall and in all seven strata,
has no excessive stratum regression, preserves the welfare envelope, and adds
no bad window.

## 4. Correction-specific comparison

The failed original replay remains immutable. A streaming comparison between
its V2 raw export and the corrected raw export, keyed by source run, frame, and
window, found:

- 50,000 aligned streams in each export;
- after ignoring `placement_dispersion_normalized`, exactly three records
  differ, all in the E0 envelope selection and exactly matching the
  preregistered capped-O0 incumbent defect;
- the corrected selections are service scarcity at homogeneous-high D67,
  reverse ready at homogeneous-high D70, and resource impact at
  heterogeneous-high D69;
- all O0--O4 candidate assignment hashes, stability/certification fields,
  welfare components, startup burden, and projected finish values are
  otherwise identical;
- 6,194 streams contain only binary32 accumulation-order variation in
  `placement_dispersion_normalized`: 12,038 scalar differences, maximum
  absolute magnitude `1.7881393432617188e-7`, with no eligibility effect.

The original V2 result failed closed with three diagnostic errors and no
eligible mechanism. The corrected V2 result has zero diagnostic errors and
does not conceal or replace the failed evidence.

## 5. Decision boundary and next authorized action

The frozen eligibility output is:

- `eligible_ranked=["E0"]`;
- `later_candidate_preregistration_options=["E0"]`;
- `selection_uses_throughput_or_qpr=false`;
- `D71_authorized=false`.

Therefore G3 closes only as a mechanism diagnostic. It does **not** establish
that E0 improves realized throughput or QPR, and it does not close any paper
experiment group. The next permissible step is to write and commit a separate
operational E0 candidate preregistration, including implementation boundaries,
fresh D71--D75 development seeds, all-six-cell evaluation, scheduler-overhead
reporting, and a frozen homogeneous-low nine-baseline dual-metric gate. Only
that preregistration may authorize new sampling.
