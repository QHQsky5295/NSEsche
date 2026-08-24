# NSESche operational development handoff — V48

V48 is a closed, immutable middle-load development cohort. It is not the
middle-load frozen profile because no candidate was strictly first in both
fixed-window throughput and QPR. All valid evidence is retained; no seed was
replaced or deleted.

## Frozen identities

- Mechanism commit: `eeb85983a2f6fe4b1b38ab84e7b685e4f691a805`
- Plan commit/runtime identity: `d8337dc4fb649726ca2f178632019bb7f7a1ecf5`
- Source blob: `e9f0715fd837209330910d0dcee7a4c6d533d771`
- Source SHA-256: `9b4a1b76794073ad9aad569a786fe845d6ee69240486ec264ea7b93c272a20d5`
- Release binary SHA-256: `3fed90bf3786e69f084d1e42ffbd323724b0533c7ad38a492b0bf196b28d8774`
- Plan SHA-256: `eb5e47ea4cc2449cee90954930c7cefd582d436105df6958b11722472a13a35a`
- Development seeds: E160–E164; reserve E165–E169 remained untouched.
- Sealed confirmation seeds E120–E129 remained untouched.

## Execution and result-blind gate

- Five base tapes, 15 offline references, and 60 online runs completed on
  first attempts with zero quarantine.
- Joint pairing: `tmp/nse_operational_dev_20260824_v48/pairing.v48-joint-result-blind.json`
- Joint pairing SHA-256: `713d23dae7714206e19ad21effe3b775b049c92928063a1ec6cbdefdde6ba32d`
- Joint pairing audit hash: `612f8bad07bacc9f60546aa19a672fd2605e39812d93d01bbadca037d8e2227a`
- The gate passed for 60 runs, 12 methods, and five paired seeds before any
  performance metric was read.

## Revealed result

Result artifact:
`tmp/nse_operational_dev_20260824_v48/paired-screen.v48-middle.json`
(SHA-256 `342fede1385df8a34f9028143a1be3838a926d4af96294411a8f832d12dd0c63`).

The repeat-demand Jiagu router (`v48c-jiagu-repeat-low8`) ranked first in
fixed-window throughput at 0.7386 requests/ms. FaaSRank was the best baseline
at 0.7036 requests/ms, so V48c led by approximately 4.98%.

V48c did not close QPR. Its five-seed mean QPR was 0.0298044789, rank 3,
versus FaaSRank at 0.0307250572, rank 1 (approximately 3.00% lower). The
finite-only and zero-completed-as-zero rankings were identical and all methods
had five finite QPR observations. V48a retained better QPR than V48c but did
not lead throughput. Therefore `selection=none` and `freeze_middle=false`.

## Next bounded hypothesis

V48 showed that the outcome-blind repeat-demand Jiagu branch below queue
density 8 buys enough throughput but slightly overpays latency/cost. V49 may
use only the untouched E165–E169 cohort to compare narrower fixed thresholds
inside that same branch (for example 2, 4, and 6), while preserving V47c at
density 8–24 and Orion at density 24 or above. Low and high frozen profiles,
V47/V48 names, and all earlier evidence must remain unchanged.
