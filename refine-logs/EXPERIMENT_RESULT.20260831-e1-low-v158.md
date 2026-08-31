# E1 Homogeneous-20 Low V158 Diagnostic Result

V158 is a valid but unsuccessful adaptive-training diagnostic. Adding every
nonterminal parents-scheduled request whose remaining-work score was at most
`5.5` raised the complete 20-seed hybrid QPR to `0.0579751798`, above OCS
`0.0555771603`, with `14/20` positive pairs. Its throughput mean was also above
Orion (`1.4837` versus `1.4741 requests/ms`), but the paired gate fell to
`11/20`; therefore the joint preregistered decision failed.

The three new rows were E09, E18 and E20. Their throughput sum was `4.234`,
above the frozen `4.042` sum gate, but only E18 beat Orion. Their QPR sum was
`0.2352246693`, above `0.1872642803`. E09 supplied nearly the entire treatment:
it admitted 1,114 short-work nonterminal players, while E18 admitted zero and
E20 admitted five.

The result-blind audit passed before performance reveal. Across 3,000 windows,
2,629 terminal incomplete-parent players and 1,119 short-work nonterminal
players were admitted; 557,930 nonterminal players were rejected. The largest
admitted remaining-work score was `5.0752344`, the smallest rejected score was
`6.0232506`, both queue routes were exercised, and the blind audit parsed zero
performance fields.

Post-result mechanism analysis locates the throughput loss: in E09, 854 of the
1,114 short-work admissions occurred at queue density at or above the already
frozen threshold `8`, where mean queue density was about `16`; only 260 occurred
below `8`, where mean density was about `0.3`. This supports one bounded next
test: permit short-work speculation only under slack, while retaining terminal
pipeline placement at every density.

All three valid V158 rows remain retained, V158 is retired, and its other 17
rows are not run. The sealed result is
`../tmp/nse_e1_homogeneous_short_work_terminal_pipeline_queue8_low_diagnostic_20260831_v158/diagnostic-result-v158.json`;
the result-blind audit is `joint-blind-audit-v158.json` in the same directory.
The low-load comparison remains open, so middle and later paper sections remain
blocked.
