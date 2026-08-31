# E1 Homogeneous-20 Low-Load V155 Result

V155 is a complete, technically valid training result, but it does not close
the homogeneous 20-node low-load comparison. The publication-facing algorithm
name remains `NSESche`; `V155` is only internal development provenance.

## Primary result

- Fixed-window throughput: `1.49915` requests/ms, above the frozen Orion
  ceiling `1.47410` by `1.70%`; `12/20` paired seeds are strictly positive.
- Finite-only and zero-completed-as-zero QPR: `0.0537230873`, below the frozen
  OCS ceiling `0.0555771603` by `3.34%`; `13/20` paired seeds are positive and
  all `20/20` candidate QPR values are finite.
- Joint training decision: fail. The profile is retired unchanged; no fresh
  E1530-E1549 confirmation input was generated or opened.

## Mechanism result

The queue gate behaved exactly as preregistered in all `20,000` scheduler
windows: `7,137` windows used Hiku2/OCS Borda below density 8 and `12,863`
used exact OCS current-demand at or above density 8. There were zero route
mismatches, zero placement rejections, 20/20 canonical runs, and no technical
retry.

Relative to V150, V155 increased mean throughput from `1.47905` to `1.49915`,
increased QPR from `0.05104068` to `0.05372309`, reduced mean latency from
`104.84` to `102.17` ms, reduced cost/completed request from `0.4525` to
`0.4446`, and reduced Nash assignment moves from `32,728` to `7,175`. The
intervention therefore improved every targeted aggregate without closing the
last QPR gap.

The remaining gap is primarily latency rather than cost: frozen OCS averages
`96.69` ms and `0.4425` cost/completed request. V155 already matches OCS cost
closely but only places functions whose parents have completed, whereas native
OCS can place a descendant once its parents have been scheduled. The next
mechanism investigation must therefore test pipeline-ahead placement while
preserving the SRPT/queue-control throughput path; threshold search is not
authorized by this result.

## Immutable evidence

- Root: `tmp/nse_e1_homogeneous_queue8_low_training_20260831_v155`
- Ready manifest hash:
  `1ed440cc4a7d2da149db824eb1d1e0cb6e8d8a31e04317a8824d18d69845ae44`
- Blind-audit hash:
  `5baf5db11dc071b040c9e87620e745a21f06642e3637524f9c63cfdc6614968d`
- Result hash:
  `d13908a16458d8c90faeb72875a08f197af263c9af6016f9dd2c7246f0de1fb0`
- Release binary SHA-256:
  `cd91cf1f36e8940027e9386cc0bf4188615479ba22ad057ae76edc554e3c7a23`

All valid samples remain retained. V155 is not materialized into a final-paper
catalog or figure.
