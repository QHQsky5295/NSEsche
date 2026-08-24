# NSESche operational development handoff V40

V40 is closed with `v40a-hybrid3-loadleast-ocs2` selected and frozen. It used
only the preregistered, permanently non-formal E110--E114 cohort. The selected
candidate passed both low-load gates, so the previously sealed E11--E20
confirmation block is now unsealed under the V40 plan.

## Provenance and gates

- scheduler code commit: `b45731de2125c9cbaaf7a2cf719dfa584ccb5981`
- plan commit: `621d97dee53ec6cc5b4e349b494fa448e1270329`
- plan SHA-256: `ec1005da21c8d3792aec90f6f5cd3f9b6e3811d40c1a5edd114522ab4081b187`
- scheduler source SHA-256: `9b08ee9e0cc9ae9948ecde8dca5aea8d2a8c09d1bf8af028eaa880f8705a4689`
- scheduler source blob: `dac8db7ed052baa744da58b5e7e0650d72fdefd5`
- release binary SHA-256: `26c49f147dbfc291cdf540c2061c67ab18c1978187cc76fad5ffd3c083a3505b`
- result: `tmp/nse_operational_dev_20260824_v40/candidate-screen.v40-ocs-votes.json`
- result SHA-256: `820ff6c990f5432d9b496928b685f580e9e6103b7e432d86509f4f76d159b38c`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 60 online runs passed QC and result-blind
pairing; capture, online, and reference quarantine counts were zero. Execution
was strictly serial, `serverless_sim/records` remained empty, and all 60 runs
shared one Git, binary, Python, and Cargo.lock identity. No canonical-name
repair was required.

## Revealed result and frozen selection

Jiagu led E110--E114 baseline throughput at `1.4874`; Hiku led baseline QPR at
`0.0495549378`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V40a hybrid3 + LoadLeast + OCS x2 | 1.5352 | 1 | 0.0553401729 | 1 | yes |
| V40b hybrid3 + LoadLeast + OCS x3 | 1.5310 | 2 | 0.0518527782 | 2 | yes |
| V40c hybrid3 + LoadLeast x2 + OCS x2 | 1.5114 | 3 | 0.0488623964 | 4 | no |

V40a and V40b both strictly exceeded every baseline in both mean metrics. The
preregistered fixed priority selects V40a, the smaller OCS increment; V40b may
not replace it after reveal. The frozen low profile is therefore three V11
hybrid votes, one current-demand LoadLeast vote, and two current-demand OCS
votes. Frozen V8 remains the middle/high profile.

Confirmation must reuse the frozen matching E11--E20 baselines and run exactly
30 optimized NSESche processes: V40a for low, V8 Orion-P for middle, and V8
structural initialization for high. No confirmation seed may be deleted,
replaced, used to tune the frozen profiles, or selectively rerun for a
scientific outcome. Closure requires optimized NSESche to rank first in both
mean fixed-window throughput and mean per-run QPR at each of the three loads.
