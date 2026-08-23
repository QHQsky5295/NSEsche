# NSESche operational development handoff V33

V33 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E76--E80 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `2a99f3c4c92f77af9a6551e77acf32eb488445ff`
- plan SHA-256: `6090d30cc503c4acdef4178e87b8828373495ae57c318b20a9cf32eb9d6bb057`
- scheduler code commit: `97d5148b2edfa82aa1aced02bd82ea130b721971`
- scheduler source SHA-256: `dd1fdc9febce765a61bf34584f9e65d1fd2e02817a4273860444086dbef7cf1b`
- release binary SHA-256: `fad199173f1108df0057db7cfb43e687cbdec944587cba828de69e05d2deef4b`
- result: `tmp/nse_operational_dev_20260824_v33/candidate-screen.v33-jiagu-forecast-semantics.json`
- result SHA-256: `50c4de80bb38d95f268fbe8d230a9ddb7c74766015a3b9f3eea424706280afc5`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 20 paired environment groups passed. Online and
reference quarantine counts were zero, execution was strictly serial, and
`serverless_sim/records` remained empty.

## Revealed result

Orion led E76--E80 baseline mean fixed-window throughput at `1.4532`.
FaaSRank led mean per-run QPR at `0.0578273875`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V33a Jiagu forecast order | 1.3426 | 10 | 0.0514360343 | 2 | no |
| V33b Jiagu forecast width | 1.4076 | 4 | 0.0419653516 | 7 | no |
| V33c Jiagu forecast faithful | 1.4054 | 6 | 0.0419591937 | 8 | no |

The Jiagu forecast family is closed without subdivision. Mirroring the
baseline's 20-frame mean-plus-trend forecast in player ordering, active-prefix
width, or both did not reproduce a joint lead. Frozen V8 remains the
middle/high rollback winner and V11 remains the best low-load rollback point.
E76--E80 must not be reused for candidate selection.
