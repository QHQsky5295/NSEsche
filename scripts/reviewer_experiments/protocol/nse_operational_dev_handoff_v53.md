# NSESche operational development handoff V53

V53 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E185--E189 cohort. E190--E194 remained
uncaptured reserve, and sealed confirmation seeds E120--E129 remain unused.

## Provenance and gates

- final plan/runtime commit: `48d33ff83cbc1fc054a5b0671630c7eba3698659`
- plan SHA-256: `7248b3b4ae195f71b31651833ac5bc954c21b825073e50a1b70a747986352411`
- scheduler code commit: `b29658d54ee958e19f3c59f70c22413c06b808f4`
- scheduler source SHA-256: `afda9f7cfa9cc6560c43c2875f7f3e1cc6c70b0901ecdbb5e942ead1b06c3235`
- release binary SHA-256: `5d2c2e2c6f8af013d4ffa0cbe96db4226a3541f6dad32cb4e17d4b80b4aae8b0`
- result-blind joint pairing SHA-256: `96ba24d5d4624c31a2681df31c2111b4befef36b61496cd45ed73a4ff2a5a991`
- result-blind audit hash: `8ec0b26aaed194884471400e5661a04d4baee8ebd25eb0e2b404085885147bbb`
- result: `tmp/nse_operational_dev_20260825_v53/paired-screen.v53-middle.json`
- result SHA-256: `877fc2d6bc55f0545d73baa6804b41081409308ba6807a94fef1f8a670aed11d`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. Four online and three reference ledgers
passed, quarantine was empty, and no canonical directory-name repair was
needed. The joint result-blind audit verified 60 runs in five complete
12-method groups with common tape, HPA, simulation, binary, Python,
Cargo.lock, and runtime identities before performance metrics were read.

## Revealed result

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V53a full triage | 1.5072 | 1 | 0.105202390 | 7 | no |
| V53b delete middle | 1.4990 | 2 | 0.108590432 | 5 | no |
| V53c delete low composite | 1.4698 | 3 | 0.093734071 | 10 | no |

V53a strictly led throughput, exceeding the best frozen baseline FaaSRank
(`1.4146`) by about 6.55%. Hiku led QPR at `0.117609336`; V53b was the best
candidate QPR and trailed Hiku by about 7.67%. The OCS middle band increased
throughput slightly but reduced QPR, so the simpler V53b two-regime router is
the rollback point for the next mechanism. The fixed 24/48 queue-regime axis is
closed without further threshold subdivision.

## Mechanistic next step

The QPR deficit was concentrated in E188: V53b QPR `0.417568021` versus Hiku
`0.484254003`. V53b already exceeded Hiku in E187 and E189, so globally routing
low queue density to Hiku would discard valid gains. A post-reveal,
pre-placement-state audit distinguishes the regimes:

- E188 is low-queue throughout, with a narrow current scheduling frontier and
  a mature cluster containing many running containers.
- E189's low-queue windows also have a narrow frontier, but essentially no
  running-container coverage; switching there would be a startup error.
- E180/E187 more often have a wide frontier where V52c/V53b already helped.

A future V54 may therefore retain V53b (V52c below queue density 24 and
load-faithful Hiku at or above 24), but inside the low band invoke Hiku only
when all current-state semantics agree: the frontier is narrow relative to the
20-node cluster, running-container count is at least node count, and the
player's feasible set contains an idle-warm container. The exact structural
predicate is outcome-blind and mirrors Hiku-P's pull-worker applicability.
Deletion controls may remove the idle-worker requirement or remove the global
maturity requirements; they must not sweep thresholds.

Any V54 execution must commit code and a fresh plan before capturing untouched
E190--E194, run all nine baselines and three candidates on every seed, reveal
only after joint pairing, and preserve the same strict throughput plus two-QPR
gate. Low remains frozen as `orion_ocs2_borda`, high remains frozen as
`jiagu_current_demand`, and E120--E129 remain sealed.
