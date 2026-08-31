# E1 Homogeneous-20 Low V161 Diagnostic Result

V161 was executed exactly as preregistered on E09, E18 and E20. All three
NSESche rows passed QC on attempt 1 and remain retained. No baseline or other
V161 seed was run. A short outer-shell timeout occurred before the reference
stage created an attempt or ledger; the subsequent authorized reference build
produced the exact three tables on attempt 1.

The result-blind audit was sealed before performance reveal. Across 3,000
scheduler windows it observed 2,485 terminal incomplete-parent admissions and
106 JIT parent-tail short-work admissions, including 87 admissions deeper than
the completion-proximal stage. It also observed 22,756 fail-closed parent-tail
rejections: 277 missing/nonconsecutive histories, 15,624 inactive parents and
6,855 invalid or zero-service paths. The maximum admitted tail/cold-start ratio
was only 0.0667226, showing that the realized-service rule admitted very near
parent completion. Both queue-router branches were exercised. The blind audit
parsed zero throughput, latency, cost, completion or QPR fields.

After reveal, the complete E01--E20 hybrid candidate again passed throughput:
mean throughput was 1.4948 requests/ms versus Orion's 1.4741, with 12 of 20
paired wins. The three diagnostic seeds contributed 4.456 requests/ms and two
of three paired wins. Finite-only and zero-completion-as-zero QPR both averaged
0.0544279156 versus OCS's 0.0555771603. Although QPR retained 13 paired wins,
its mean remained lower by 0.0011492447, and the diagnostic three-seed QPR sum
was 0.1642793854 rather than the required value above 0.1872642803.

| Seed | Throughput (requests/ms) | QPR |
|---|---:|---:|
| E09 | 1.839 | 0.0850366665 |
| E18 | 0.986 | 0.0285742953 |
| E20 | 1.631 | 0.0506684236 |

V161 is therefore a clean mechanistic falsification. It proves that the JIT
gate can propagate 87 deeper placements without disturbing throughput, but the
gate is too late to recover V159's QPR gain. The remaining seventeen V161 runs
and fresh confirmation remain unauthorized. Homogeneous low is not closed;
middle/high evidence and every later paper section remain frozen.

Artifacts:

- Root: `tmp/nse_e1_homogeneous_jit_parent_tail_slack_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v161`
- Ready manifest: `manifest.v161-low-srpt-slack-jit-parent-tail-short5p5-terminal-pipeline-hiku2-ocs-queue8.ready.json`
- Blind audit: `joint-blind-audit-v161.json`
- Diagnostic result: `diagnostic-result-v161.json`
- Blind audit object hash: `5a562689a74ab778ef7ac35cb964f52970b0501c8f9966c54389045ab2202d62`
- Blind audit file SHA-256: `12723d58832ee98f7e9b69c1ca401efd0cb43c63495671d64e6490481484404e`
- Result object hash: `ffc4abff1ee112b8c84b3f28373fb99b2b3321b1a0d785dec1849236612df56d`
- Result file SHA-256: `f143731de00977de67678717d85b7cf30eca18652be05765a4b187f65736a4df`

