# NSESche operational development handoff V52

V52 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E180--E184 cohort. E185--E189 were not
captured or executed, and sealed confirmation seeds E120--E129 remain unused.

## Provenance and gates

- plan/runtime commit: `5ea8f639716f5995c0c56f3694a2e0aa50d5dc71`
- plan SHA-256: `612e60342d426f1d542484ba44cc7294fad8964f6dda7a97636533039625f2f5`
- scheduler code commit: `f402ec1781566f81cd9227df6713321c9daea55c`
- scheduler source SHA-256: `4787cd3f7deadc1a3734f88cc119ee455b2cac09bf962e0622c6384cfb608638`
- release binary SHA-256: `39d0b300d4c23c508aaa70be3fc63086c9aabb3b33183eef3090c771132539d7`
- result-blind joint pairing SHA-256: `cc43ef4ac3c91b2ac59ddca424fe6cc88199098e548f792557dee882c6a8647c`
- result-blind audit hash: `5db007ef784b26ea28cc968ca2ffc5a86440625041f0da2cf9919a18538fa85a`
- result: `tmp/nse_operational_dev_20260825_v52/paired-screen.v52-middle.json`
- result SHA-256: `bfe9c2c441cc8841dcd7e6704c9db6e7f5515ed4e36e12f4307609fd0990f496`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. Four ledger chains and all 20 individual
pairing groups passed. The joint result-blind audit then verified 60 runs in
five complete 12-method groups with identical tape, common-HPA, simulation,
binary, Python, Cargo.lock, and runtime-commit identities. Online and reference
quarantine counts were zero. One externally mislabelled baseline canonical
directory was atomically renamed to the run ID already embedded in its files
and ledger; all 15 file hashes and the ledger hash were unchanged.

## Revealed result

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V52a base2:OCS1 | 0.7898 | 4 | 0.106832413 | 7 | no |
| V52b base1:OCS1 | 0.8292 | 3 | 0.110091379 | 5 | no |
| V52c base1:OCS2 | 0.7418 | 7 | 0.130006009 | 1 | no |

Hiku led throughput at `0.8588`; V52c led both finite-only and
zero-completion-as-zero QPR at `0.130006009`. V52c's QPR margin over the next
method (LoadLeast) was about 7.78%, while V52b's throughput deficit to Hiku was
about 3.45%. No candidate satisfied the simultaneous strict-rank-one gate.
The fixed vote-multiplicity axis is therefore closed: it moved the operating
point between throughput and QPR but did not dominate both.

## Mechanistic next step

The post-reveal window audit provides a distinct, outcome-blind mechanism
hypothesis rather than another vote interpolation. Under V52b, player-weighted
current pending-plus-runnable queue-density shares in bands `<24`, `24--<48`,
and `>=48` were respectively:

- E180: 1.000 / 0.000 / 0.000
- E181: 0.079 / 0.047 / 0.874
- E182: 0.117 / 0.076 / 0.806
- E183: 0.142 / 0.185 / 0.673
- E184: 0.154 / 0.295 / 0.551

The low-density E180 regime is where the frozen V52c expert delivered its QPR
advantage. Hiku dominated the high-density E182/E183 throughput regimes, while
OCS was strongest in E184, which had the largest middle-band share. A fresh
V53 may therefore test one fixed three-regime current-state router: frozen V52c
below 24 tasks/node, exact OCS-P current-demand placement from 24 to below 48,
and load-faithful Hiku-P at 48 or above. Two deletion controls should remove the
middle OCS band or the low V52c composite; this tests the regime mechanism and
does not tune another vote dose. Thresholds are fixed at the already frozen 24
boundary and its one-step doubled boundary 48. All routing inputs precede
placement and exclude completion, latency, cost, seed, and workload labels.

Any V53 execution must use a newly committed plan, untouched E185--E189, all
nine paired baselines, simultaneous reveal, and the same strict throughput plus
two-QPR gate. Low remains frozen as `orion_ocs2_borda`, high remains frozen as
`jiagu_current_demand`, and E120--E129 remain sealed.
