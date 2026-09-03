# G6 lookahead development result audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `b43b5c76522eb1e40962f780387226202ab38171`  
Reference-audit prerequisite: `bb14882ab5ad93bce00be8d9b9b3a3b576cdef06`  
Status: development gate failed; confirmation and formal progression blocked

## Outcome

The sole preregistered G6 `lookahead_preall_sched` candidate was executed once
for each of D71--D75, in manifest order.  All five first attempts passed QC and
were retained.  The predeclared analyzer returned
`complete_g6_development_gate_failed`:

- `candidate_development_qualified=false`;
- `confirmation_preregistration_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

The result is a valid negative development result.  It must not be repaired by
dropping D73, substituting a seed, changing a threshold, or rebuilding an
offline reference after viewing the metrics.

## Frozen result product

Run root:
`runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904`

| Artifact | Hash |
|---|---|
| ready manifest canonical hash | `d5b7a2143688f618a9ef286466d0c7c7a6b92687bb5bf97dab6e28ce9ca4c1f3` |
| `g6.ready.json` file SHA-256 | `69f34423d632fbdb1de286f9dc0ca27c1e3da24fbb629b4dc7e52614b2b96965` |
| selection document hash | `842a20e410c1f1a188b76d42b4398251171574241d39121b0e33630371d04592` |
| `g6.selection.json` file SHA-256 | `6fa6446ef8a84432dee6607c8a58b3cbd02548e67aa0f22dbbbb787c2e60d3f6` |
| `online/ledger.jsonl` file SHA-256 | `99ac3d2a3be35a547bd336f9fd4149426eb73fde76fb699b9840233f806a6b84` |

The analyzer revalidated five candidate artifact receipts and all 50 frozen
source-control artifact receipts.

## Aggregate results

| Metric | G6 candidate mean | G3 C0 mean | Frozen best baseline | Gate |
|---|---:|---:|---:|---|
| throughput (requests/ms) | 1.078400 | 1.143400 | 1.151400 (`sche_Hiku`) | fail |
| QPR | 0.029572 | 0.024900 | 0.040391615 (`sche_jiagu`) | fail |
| latency (ms; lower is better) | 77.4537 | 84.4634 | n/a | pass versus C0 |
| completion ratio | 0.564216 | 0.598534 | n/a | fail versus C0 |

Relative to C0, the paired mean throughput difference was -0.0650
requests/ms (95% t interval [-0.2626, 0.1326]), the paired mean QPR difference
was +0.004672 ([-0.01492, 0.02426]), the mean latency improvement was 7.0097
ms ([-22.3453, 36.3647]), and the paired mean completion-ratio difference was
-0.034318 ([-0.13839, 0.06975]).  The mean solve-time ratio was 0.9766 with a
95% interval [0.7139, 1.2393], so computational overhead was not the failed
constraint.

## Per-seed paired results

| Seed | Candidate T | T/C0 | Candidate QPR | QPR/C0 | Latency improvement (ms) | Completion delta | T win | QPR win |
|---|---:|---:|---:|---:|---:|---:|---|---|
| D71 | 1.636 | 0.9359 | 0.039047 | 0.9086 | -10.556 | -0.05870 | no | no |
| D72 | 0.956 | 1.0269 | 0.017901 | 1.0311 | -8.377 | +0.01298 | yes | yes |
| D73 | 0.588 | 0.6447 | 0.007474 | 0.6910 | +36.637 | -0.17089 | no | no |
| D74 | 0.998 | 1.0267 | 0.058111 | 2.2894 | +28.761 | +0.01357 | yes | yes |
| D75 | 1.214 | 1.0520 | 0.025329 | 0.9057 | -11.417 | +0.03145 | yes | no |

The fixed win requirements were throughput at least 3/5, QPR at least 4/5,
and joint improvement at least 3/5.  Observed counts were 3/5, 2/5, and 2/5.
D73 also violated both preregistered 80% per-seed safety floors.  Mean
completion was below C0.  These failures are decisive even though activation,
mean latency, and solve-time gates passed.

Leave-one-seed-out analysis does not justify seed removal.  Excluding D73
would leave the paired throughput difference at -0.00025 requests/ms rather
than establish a stable gain; excluding D74 would make the paired mean QPR
difference negative (-0.002342).  The candidate's favorable QPR mean relative
to C0 is therefore not robust and remains below the frozen best baseline.

## Mechanism activation and integrity

Every seed passed the activation gate.  Pre-ready binding shares for D71--D75
were 45.40%, 14.45%, 41.55%, 35.30%, and 33.06%; corresponding mean startup
overlaps were 16.51, 11.43, 13.07, 6.68, and 8.24 ms.  Thus the negative result
cannot be attributed to a dormant implementation.

All five canonical runs have:

- attempt number 1 and `qc_pass` status;
- process exit code 0 and no timeout;
- adapter status `completed`;
- frozen binary SHA-256
  `90988e545679a04f46f680d6ac7e0e0a52d8e1335c2d0309e73d4383c3147611`;
- exact post-run module-inventory restoration.

There are exactly five canonical run directories and zero files in the
partial workspace after promotion.  All prepared assignments were sent, with
zero invalid assignments and zero dispatch-channel failures.  Every active
window hit its bound offline reference.

## Interpretation and next boundary

Parent-scheduled lookahead does overlap startup, but unrestricted early
binding is not safe: it sometimes reserves placement/resources before a child
is executable, improving latency in some seeds while lowering completion and
throughput in others.  D73 is the largest manifestation, but D71 also loses
throughput and latency despite strong activation, so activation share alone is
not a sufficient enablement rule.

G6 is closed and cannot enter confirmation.  Only read-only post-failure
diagnosis over the retained G3/G6 artifacts is authorized next.  A new
operational candidate, if supported by that diagnosis, requires a new named
preregistration and a fresh development product before any simulator sampling.
The paper's Eqs. (1)--(20), strict Eq. (15), fixed controls, fixed seed policy,
and all G6 results remain unchanged and retained.
