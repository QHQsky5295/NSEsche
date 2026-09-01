# E1 Homogeneous-20 Low V187 Result

V187 is a complete, technically valid training failure. All 40 paired NSESche
runs on E1610--E1629 passed QC on attempt one, the two arms used the same fresh
tape per seed, and the result-blind inventory was sealed before the single
reveal. Two Windows-misnamed candidate directories were restored to their
ledger-sealed run IDs before the blind audit; all 30 contained file hashes were
unchanged.

The response-time-majority candidate raised mean QPR to `0.06623203`, above
frozen OCS (`0.05557716`) and its same-tape control (`0.06354818`). It did not
close the paper comparison because mean throughput was only `1.44045` req/ms,
below frozen Orion (`1.47410`) and the same-tape control (`1.45185`). The paired
throughput change was `-0.01140` req/ms with 4 wins, 2 ties and 14 losses.

Post-reveal diagnosis shows that the response-time expert controlled an average
of 59.83% of all scheduling windows. The candidate completed 11.4 fewer requests
per run on average, while mean latency rose 4.43 ms and cost per completion rose
0.0232 simulator units. Moreover, 91.45% of the aggregate QPR gain came from
E1623, where the candidate completed 105 fewer requests. Thus a two-response to
one-OCS Borda vote was not a throughput-safe secondary optimization; it became
the primary high-density policy and improved the completed cohort partly by
changing which requests finished.

The complete V187 cohort remains available at
`tmp/nse_e1_homogeneous_20node_low_response_time_ocs_training_20260901_v187`.
The immutable failure receipt is
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_20node_low_response_time_ocs_training_failure_v187.json`.
Homogeneous-20 low remains open, and middle load plus every later paper section
remain blocked.
