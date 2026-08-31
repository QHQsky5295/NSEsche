# Experiment Plan: E1 Homogeneous-20 Low Terminal-Pipeline Diagnostic V157

**Current paper section:** E1 homogeneous, 20 nodes, low load.  
**State:** still open. V156 passed both complete-cohort means but failed the
pre-registered throughput paired gate (11/20 rather than 12/20).

## Why V156 did not close the section

V156 proved that parent-scheduled preplacement is a real mechanism: 10,522
pipeline-ahead players were exercised, the E09 mean latency fell from 139.07
ms to 74.10 ms, and the hybrid QPR mean rose above OCS. But unrestricted
pipeline placement also reduced E09 and E20 completions by 241 and 312. The
complete block therefore had only 11 throughput wins even though its mean was
slightly above Orion.

This is consistent with speculative capacity occupation. A child whose
parents are assigned but unfinished can reserve an HPA-created container long
before it contributes a completed request. That reservation is most defensible
for a terminal child: once it executes, the request completes. It is less
defensible for a nonterminal descendant, which merely advances speculation by
one layer.

## V157 single change

V157 returns to the complete V155 parents-completed cohort and adds only
terminal functions whose parents are all assigned. It excludes nonterminal
pipeline-ahead functions. The terminal label is immutable DAG topology; it
does not depend on seed, load label, future arrivals, or any performance
outcome.

Everything else remains V155: threshold-8 Hiku2/OCS scoring, SRPT order,
NSESche equations, common HPA, tapes, metrics and offline references.

## Fixed diagnostic and gate

- New work: three references and three NSESche runs, E09→E18→E20.
- Reuse: the other 17 V155 rows and all 180 frozen baseline rows.
- Before reveal: prove that admitted incomplete-parent players are terminal,
  excluded nonterminal pipeline candidates are counted, both queue routes are
  exercised, and no performance field was read.
- After reveal: replace only the three same-seed V155 rows. Require hybrid
  throughput mean >1.4741 and at least 12/20 wins (at least 2/3 here), both QPR
  means >0.055577160345697 with at least 12/20 wins, complete finite coverage,
  three-seed throughput sum >4.042 and QPR sum >0.187264280342794.

A pass only authorizes a separately committed remaining-17 training block. It
does not close low load and does not open confirmation. A failure retires V157
without running the other 17.

Machine-readable plan:
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_plan_v157.json`.
