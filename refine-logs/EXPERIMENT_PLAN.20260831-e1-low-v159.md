# Experiment Plan: E1 Homogeneous-20 Low Slack Short-Work Diagnostic V159

**Current paper section:** E1 homogeneous, 20 nodes, low load.
**State:** still open. V158 passed QPR but failed the preregistered throughput
paired gate with `11/20` wins.

## Why this bounded diagnostic is justified

V157 and V158 bracket the mechanism. Terminal-only pipeline placement retained
throughput but left the QPR mean `0.0011434` below OCS. Adding all short-work
nonterminal pipeline players raised QPR above OCS, but lost one required
throughput pair. V158's treatment was concentrated in E09: 854 of its 1,114
short-work admissions occurred at queue density at or above `8`, with mean
density about `16`; only 260 occurred below `8`, with mean density about `0.3`.

This is disclosed outcome-informed adaptive training. It motivates a single
causal change using two thresholds already frozen before V159: remaining work
`5.5` from V158 and queue density `8` from the V155 scoring router.

## V159 single change

V159 retains every V157 player. A nonterminal parents-scheduled player is added
only when its request remaining-work score is at most `5.5` **and** current
pending-plus-runnable queue density is strictly below `8`. Terminal pipeline
players remain admitted at every density. The threshold-8 scoring router,
SRPT order, NSESche equations, common HPA, tapes, metrics and reference rules
remain unchanged.

The mechanism interpretation is resource reservation under backlog:
speculative container preparation can help a short chain under slack, but the
same action competes with runnable work when queues are already dense.

## Fixed diagnostic and gate

- New work: three references and three NSESche runs, E09→E18→E20.
- Reuse: the other 17 V155 rows and all 180 frozen baseline rows.
- Before reveal: require all slack short-work admissions to have work `<=5.5`
  and density `<8`; all congestion-gated short-work rejections density `>=8`;
  terminal admissions, over-work rejections and both scoring routes observed;
  zero performance fields read.
- After reveal: apply unchanged gates—throughput mean `>1.4741`, three-seed sum
  `>4.042`, at least `12/20` and `2/3` wins; both QPR means
  `>0.055577160345697`, three-seed sum `>0.187264280342794`, at least `12/20`
  wins and finite `20/20` coverage.

A pass authorizes only a separately committed remaining-17 training block. A
failure retains the three valid diagnostics and retires V159. Neither branch
opens fresh confirmation directly.

Machine-readable plan:
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_plan_v159.json`.
