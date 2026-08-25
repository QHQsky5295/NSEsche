# V59 low/middle NSESche closure plan

High is already closed by V58 and will not be rerun. The nine low/middle
baseline methods from V58 are also frozen. V59 runs only NSESche on fresh
E230--E234 random workloads.

The V58 low result split throughput and QPR between the Hiku endpoint and the
equal Hiku/OCS Borda endpoint. Middle showed the complementary split. V59
therefore evaluates a preregistered vote-weight path: equal Borda, 2:1 majority,
3:1 majority, and the pure endpoint. The expert switch threshold is fixed to
zero for all candidates so the declared operational expert consistently resolves
paper-utility indifference; paper utility, social welfare, and offline reference
search do not change.

There are 10 tapes, 40 state-matched references, and 40 online NSESche runs.
No baseline or high-load process is rerun. Metrics remain hidden until all 40
runs pass QC and a result-blind 2 loads × 5 seeds × 4 candidates audit passes.
Each load closes independently when one candidate strictly exceeds the frozen
V58 baseline maximum in throughput and both QPR conventions. A passing load is
published and reused as `NSESche-low-final-v1` or
`NSESche-middle-final-v1`; candidate IDs remain provenance-only labels.
