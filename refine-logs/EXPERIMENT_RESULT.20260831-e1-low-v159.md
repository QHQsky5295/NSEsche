# E1 Homogeneous-20 Low V159 Diagnostic Result

V159 is a valid but unsuccessful adaptive-training diagnostic. Restricting
nonterminal short-work speculation to the existing queue-density-below-`8`
slack regime retained the QPR improvement: the complete 20-seed hybrid QPR was
`0.0570260211`, above OCS `0.0555771603`, with `13/20` positive pairs. The
throughput mean was also above Orion (`1.48555` versus `1.4741 requests/ms`),
but the paired gate remained at `11/20`; therefore the joint preregistered
decision failed.

The three new rows were E09, E18 and E20. Their throughput sum was `4.271`,
above the frozen `4.042` sum gate, but only E18 beat Orion rather than the
required two seeds. Their QPR sum was `0.2162414948`, above `0.1872642803`, and
all three QPR values were finite. The per-seed throughput/QPR pairs were E09
`1.654/0.1369988`, E18 `0.986/0.0285743`, and E20
`1.631/0.0506684`.

The result-blind audit passed before performance reveal. Across 3,000 windows,
2,449 terminal incomplete-parent players and 261 slack short-work nonterminal
players were admitted. Another 85,924 short-work players were rejected by the
queue gate. The maximum admitted queue density was `1.6`, strictly below `8`;
the minimum queue-gated rejected density was `8.5`. The largest admitted
remaining-work score was `5.0752344` and the smallest over-work rejected score
was `6.0232506`. Both queue routes were exercised, and the blind audit parsed
zero performance fields.

Post-result comparison with V157 shows that the short-work change affected the
trade-off almost entirely through E09: relative to terminal-only V157, E09
gained about `0.0518445` QPR but lost `0.185 requests/ms` throughput, while E18
and E20 were unchanged. The next mechanism analysis must therefore explain
which subset or timing of the 261 slack admissions causes the E09 trade-off;
V159 does not authorize fitting another threshold or running the other 17
seeds.

All three valid V159 rows remain retained, V159 is retired, and its other 17
rows are not run. The sealed result is
`../tmp/nse_e1_homogeneous_slack_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v159/diagnostic-result-v159.json`;
the result-blind audit is `joint-blind-audit-v159.json` in the same directory.
The low-load comparison remains open, so middle and later paper sections remain
blocked.
