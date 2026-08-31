# E1 Homogeneous-20 Low V157 Diagnostic Result

V157 is a valid but unsuccessful training diagnostic. Its terminal-only
pipeline frontier restored the complete 20-seed hybrid throughput result to
`1.4948 requests/ms`, above Orion's `1.4741`, with `12/20` paired wins. It did
not restore QPR: the hybrid mean was `0.0544337981`, below OCS
`0.0555771603`, even though `13/20` paired comparisons were positive.

The three new rows were E09, E18 and E20. Their throughput sum was `4.456`
and two of three beat Orion, while their QPR sum was only `0.1643970` against
the frozen `0.1872643` gate. The result-blind mechanism audit passed: 2,485
terminal incomplete-parent players were admitted, 741,487 nonterminal
incomplete-parent players were rejected, and no performance field was read
before the audit sealed.

All three valid rows remain retained as adaptive-training evidence. V157 is
retired, the other 17 V157 rows are not run, and fresh confirmation remains
closed. The result is stored at
`../tmp/nse_e1_homogeneous_terminal_pipeline_queue8_low_diagnostic_20260831_v157/diagnostic-result-v157.json`;
the blind audit is `joint-blind-audit-v157.json` in the same directory.

The next falsifiable mechanism question is whether nonterminal pipeline
placement can be limited to objectively short remaining requests. V156 showed
that a broad pipeline frontier can lift QPR, while V157 showed that terminal
restriction restores throughput but removes too much of that benefit.
