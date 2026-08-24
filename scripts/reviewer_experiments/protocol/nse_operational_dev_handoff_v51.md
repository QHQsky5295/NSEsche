# NSESche operational development handoff — V51

V51 is a closed, immutable middle-load development cohort. It used the
untouched E175–E179 reserve declared before V50 execution. No valid run was
deleted, replaced, or selected by outcome.

## Frozen identities and evidence

- Mechanism commit: `3e2bf7de56ae3fcea96095825c4b364f0c9c0d0d`
- Plan/runtime commit: `8167b90157c01e2ad9b485de2132132e0b61da5d`
- Source blob: `1debc78169c22402db63c1b50b5dca56763996f5`
- Source SHA-256: `15c71ee44e6239b6d72d99d13b0aa2ad2bdbe9bd6ab022305429bda1de080756`
- Binary SHA-256: `a03898a64b52a8f72bf3902586cfd3ce3f7e6ebaef555b1d88a032872861359d`
- Plan SHA-256: `dcbb6a3b567fac90d798bc09c09db7f8a9e037d55e169c4930ad7b7fca1a2c91`
- Five tapes, 15 references, and 60 online runs all passed on attempt 1 with
  zero quarantine.
- One valid E179/Hash canonical directory was externally labelled
  `attempt-01`. It was atomically renamed to its embedded/ledger run ID after
  all 15 file hashes were checked; no content or ledger byte changed. The
  repair receipt hash is
  `df7739ece7046664c1326d7b0ebd10ebf1d2695534d8b70b0e76b7a63b23c6ee`.
- Joint pairing SHA-256:
  `73026105acae311ea9c74c801cddabc21751542a29c9e43f44f4e937c6904de3`
- Joint pairing audit hash:
  `8e4177f7400e5a8fe335de358a19733de5309265e48c710f2c345d2b903da9bf`
- Result SHA-256:
  `8cf4a969679ff6466ea56e4808cd3cbb35c6af366d48bf9a1f6499e239b91591`

## Result and bounded next mechanism

The density-11, density-12 control, and density-13 candidates were identical:
all had mean fixed-window throughput `0.5928` requests/ms and QPR
`0.0112185980`. They tied for throughput rank one but failed the strict tie
gate and ranked fourth through sixth for QPR. OCS led QPR at `0.0498233505`,
while Jiagu was the best baseline throughput at `0.5764`; the candidates were
about 2.85% above that baseline throughput.

The identical candidates are explained by state coverage rather than a code
failure. Across 4,880 active candidate windows, only one window had current
pending-plus-runnable density in `[11,13)`. Threshold interpolation is
therefore closed: no further threshold subdivision or seed replacement is
allowed. The candidate mean latency (`193.888` ms), rather than its mean cost
(`5.63669` simulator units/completed request), is the main QPR deficit; OCS
and Hiku had mean latencies `75.5365` and `65.9943` ms respectively.

A fresh V52 may retain the exact density-12 throughput router and add only an
outcome-blind OCS current-demand latency/cost vote. The bounded fixed family is
base:OCS vote ratios `2:1`, `1:1`, and `1:2`. This changes neither the paper
utility nor the social-welfare/reference objective. It must use fresh paired
seeds E180–E184, reveal all 60 runs together, and keep E120–E129 sealed.
