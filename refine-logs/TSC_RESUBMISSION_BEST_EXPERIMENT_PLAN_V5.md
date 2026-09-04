# NSESche TSC Resubmission Experiment Plan V5

Date: 2026-09-05 (Asia/Shanghai)

Status: P1 reviewer evidence is paper-writing ready; the main 20-node
homogeneous comparison remains unresolved. G12/G14/G16/G18 close the
ready-player deferral family. V5 supersedes V4 only for the ordered next-stage
decision and does not retroactively change any frozen population.

## 1. What is already closed

### 1.1 Reviewer-mandated theory/validation evidence (P1)

The retained convergence and offline-reference evidence plus 300 exact-small
states are complete. All 300 states reach a pure Nash equilibrium under the
audited strict best-response process; the worst empirical exact-small PoA is
1.0181. This package may be used to answer the convergence, offline social-
utility reference, and small-state optimality questions, subject to the
evidence-bounded wording in its claim tables.

### 1.2 Negative development families

Initialization/order, lookahead/frontier, request/backpressure,
work-conserving/ready-threshold, and ready-player deferral/cap variants have
been tested on complete fixed development banks and failed their frozen gates.
They remain useful internal negative evidence but are not paper results. The
G19 synthesis permanently closes further fixed cap/valve iteration.

### 1.3 Stable comparison evidence, but not paper-ready claims

The complete homogeneous-low Q61--Q80 ten-method product is retained. Its
NSESche centre (`r0=0.60`, `wq=0.50`) has throughput 1.58150 req/ms and QPR
0.058107, versus FaaSRank 1.59810 and 0.064039. Homogeneous-middle Q61--Q80 is
also complete but NSESche is not competitive. These products are not deleted
or relabelled; neither supports a universal-best statement.

## 2. Fixed scientific constraints

- Eqs. (1)--(20), strict Eq. (15), Eq. (19), QPR, and the game-theoretic
  narrative remain unchanged.
- A run is the sampling unit. Every first QC-valid result in a preregistered
  bank is retained regardless of direction or magnitude.
- Technical retry is allowed only for a documented crash, timeout, OOM,
  truncated/I/O-invalid output, hash mismatch, or structural QC failure, using
  the identical seed/tape/config/binary.
- Development and formal banks are disjoint. A parameter chosen on development
  seeds must be evaluated on a fresh 20-seed formal bank with all methods on
  the same tapes before any comparative claim.
- Old PDF values are alignment anchors, not acceptance targets. A discrepancy
  triggers a whole-cell audit, never method-specific resampling.
- One paper-visible NSESche configuration is used per load because the
  submitted paper already discloses load-specific `r0`/`wq` centres. The
  scheduling mechanism and binary remain global and load-blind.

## 3. Active stage: low-load parameter recovery

The submitted low-load centre and exactly four planned axial neighbours are
screened under `ready_order` on fresh D121--D125 tapes:

| Label | `r0` | `wq` |
|---|---:|---:|
| centre | 0.60 | 0.50 |
| r0_minus | 0.55 | 0.50 |
| r0_plus | 0.65 | 0.50 |
| wq_minus | 0.60 | 0.40 |
| wq_plus | 0.60 | 0.60 |

This is 25 online NSESche runs and 25 parameter-specific offline-reference
builds on five shared tapes. It includes no strong baseline and cannot be used
as the formal E7 figure.

A neighbour may progress only if all frozen population, identity, dual-effect,
paired robustness, per-seed safety, leave-one-out, completion/latency,
runtime/reference, and overhead conditions pass. In particular, its mean
throughput ratio to the centre must be at least 1.015 and its mean QPR ratio at
least 1.11. These viability margins are fixed from the pre-existing low formal
shortfalls (about 1.04% throughput and 9.26% QPR), with additional guard
margin, before D121--D125 outcomes exist.

If multiple neighbours pass, select by largest
`min(throughput_ratio, QPR_ratio)`, then largest geometric mean of those two
ratios, then fixed label order. If none passes, retain the centre for faithful
reporting and close local parameter recovery; do not spend a new 200-run
formal bank on an underpowered candidate.

## 4. Conditional low-load formal confirmation

Only a passing development neighbour unlocks a fresh Q81--Q100 paired formal
confirmation. All ten methods run on each of the 20 new tapes; the nine
baselines remain unchanged implementations/configurations, and NSESche uses
the selected low-load parameter pair with `ready_order`.

The formal product contains 200 runs and is accepted as paper-ready only after
20/20 QC, exact pairing, QPR coverage, complete statistics/figures, and honest
ranking. The target is that NSESche is first in both mean throughput and mean
QPR, but runs are not filtered or extended to manufacture that rank. Failure
is retained and sends the project back to a separately defined research stage;
it does not authorize reusing Q81--Q100 or resampling only NSESche.

The formal E7 low-load panel is then run on the same Q81--Q100 tapes for the
four non-selected axial points; the selected centre is reused from the main
comparison. This keeps tuning (D121--D125) separate from validation
(Q81--Q100) while matching the submitted five-point parameter design.

## 5. Ordered continuation after low closure

Only after the low-load formal comparison is paper-ready does work continue:

1. independently screen/confirm the submitted middle-load parameter centre and
   four axial neighbours on new disjoint development/formal banks;
2. do the same for high load;
3. freeze the homogeneous 20-node low/middle/high product and parameter panels;
4. run the planned ablation;
5. run heterogeneous low, middle, and high in order;
6. run proportional 100/500-node scaling, reusing the frozen 20-node centre;
7. add only the reviewer-required burst, QoS/fairness, and pricing/welfare
   comparisons from the bounded plan.

Native mode, fault injection, extra stress tests, and long soak remain outside
scope. No later block is opened merely because an earlier block finished; the
preceding block must meet its stated evidence and quality conditions.

## 6. Current authorization boundary

The separate low-load screen preregistration is the only authorized next
stage. It initially authorizes protocol/analyzer implementation and result-free
auditing. Tape capture, reference construction, online execution, formal
confirmation, figures, and claims each require their own evidence-preserving
checkpoint. No baseline execution is authorized during the five-seed screen.

Supersession note: V5 remains an immutable historical decision record and is
superseded prospectively by `TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V6.md`.
