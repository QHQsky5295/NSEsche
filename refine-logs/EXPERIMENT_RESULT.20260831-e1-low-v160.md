# E1 Homogeneous-20 Low V160 Diagnostic Result

V160 was executed exactly as preregistered on E09, E18 and E20. All three
NSESche rows passed QC and remain retained; no baseline was rerun and no other
V160 seed was started.

The result-blind audit was sealed before performance reveal. Across 3,000
scheduler windows it observed 2,485 terminal incomplete-parent admissions, 93
short-work admissions that were all completion-proximal, 22,603 deeper
nonterminal short-work rejections, and 161,138 congestion-gated short-work
rejections. Both sides of the unchanged queue-8 router were exercised. The
blind audit parsed zero throughput, latency, cost or QPR fields.

After reveal, the complete E01--E20 hybrid candidate passed the throughput
gate: mean throughput was 1.4947 requests/ms versus Orion's 1.4741, with 12 of
20 paired wins. The diagnostic seeds contributed 4.454 requests/ms and two of
three paired wins. However, finite-only and zero-completion-as-zero QPR both
averaged 0.0544234924 versus OCS's 0.0555771603. Although QPR had 13 paired
wins, its mean remained lower by 0.0011536680, and the diagnostic three-seed
QPR sum was 0.1641909205 rather than the required value above 0.1872642803.

| Seed | Throughput (requests/ms) | QPR |
|---|---:|---:|
| E09 | 1.837 | 0.0849482016 |
| E18 | 0.986 | 0.0285742953 |
| E20 | 1.631 | 0.0506684236 |

The topology restriction removed V159's E09 throughput loss, but it also
removed nearly all of V159's QPR increase. Thus V160 fails the joint diagnostic
and is retired. The remaining seventeen V160 runs and fresh confirmation remain
unauthorized; homogeneous low is not closed, while middle/high evidence and all
later paper sections remain frozen.

Artifacts:

- Root: `tmp/nse_e1_homogeneous_completion_proximal_slack_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v160`
- Ready manifest: `manifest.v160-low-srpt-slack-completion-proximal-short5p5-terminal-pipeline-hiku2-ocs-queue8.ready.json`
- Blind audit: `joint-blind-audit-v160.json`
- Diagnostic result: `diagnostic-result-v160.json`
- Blind audit hash: `273bb5208b66007ef3f526149585bfd78eae386ee7e97d43fef1e5992c6affe2`
- Result hash: `3d88100f4eb985a12826485d6ce450c4f981842a3b47b13088e60645a586e4cd`
