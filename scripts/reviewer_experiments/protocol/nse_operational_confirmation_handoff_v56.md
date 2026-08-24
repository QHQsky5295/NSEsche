# NSESche operational confirmation handoff V56

The one-time E120--E129 confirmation is complete and did not close the final
three-load objective. The frozen V56/V41 stack must not be reported as a
universal throughput-and-QPR winner. E120--E129 must not be reused for tuning,
seed selection, or a second scientific confirmation.

## Provenance and result-blind gates

- confirmation plan/runtime commit: `210efec7cc22626b5250414a95c90cc5630806a2`
- confirmation plan SHA-256: `52f6a0cb6510f4d02bf22c7f24af52cb26faf538064b92648a766ce756cd654b`
- frozen scheduler binary SHA-256: `1aa42fb04e2ab4dc33dc405008a592b2d7be4aa32a41712e7219b339cd6f1d45`
- ready manifest hash: `24c413dd01df213ba6012bc0da0a92a09f499641879e132b7e538fcd6afc6e7f`
- ready manifest file SHA-256: `42a55bf46e2ec7bf45cb23e74f8f03ef6f85dc69856fe4a4b79c52d9cc77d6d4`
- result-blind audit SHA-256: `2f3d9a3a9fc1b68e347c3e5d649e8765cf6ad807e0d793a5dc74719b9ecee78c`
- result-blind audit hash: `bd936a2dce9cb23c2bb598c849f0fd01db86ec7021710cb43726e34dd2ceda8c`
- result: `tmp/nse_operational_confirmation_v56/confirmation-result.v56-e120-e129.json`
- result SHA-256: `b1a63a406e04450f27fe43039e89069abdd61af1751399df2eca1154ab77af1f`

Thirty tape captures, 30 state-matched reference builds, and 30 frozen
NSESche confirmation runs all canonicalized on attempt 1 with zero
quarantine. All three ledgers passed. Before any metric was read, the
result-blind audit verified the exact 3-load x 10-seed product, all QC/archive
evidence, manifest/tape/reference bindings, frozen per-load profiles, and a
common binary/Python/Cargo.lock/Git runtime identity.

## Revealed E120--E129 result

| Load | Frozen profile | Throughput | T threshold | T gate | Finite QPR | Q threshold | Q gate | Zero-as-zero QPR | Q0 gate |
|---|---|---:|---:|---|---:|---:|---|---:|---|
| low | `orion_ocs2_borda` | 1.2905 | 1.4257 | fail | 0.08555977 | 0.05340513 | pass | 0.08555977 | pass |
| middle | `topology_faasrank_or_ocs` | 0.5613 | 1.1348 | fail | 0.00549318 | 0.06737767 | fail | 0.00549318 | fail |
| high | `jiagu_current_demand` | 0.5250 | 0.4384 | pass | 0.00681662 (n=9) | 0.00478647 | pass | 0.00613496 | pass |

High passes all three gates, including the conservative QPR treatment after
one zero-completion seed. Low improves QPR by about 60.2% over its frozen
threshold but misses throughput by about 9.48%. Middle is the decisive
transfer failure: throughput is about 50.5% below its threshold, finite-only
QPR about 91.8% below, and zero-as-zero QPR about 90.9% below.

Therefore `confirmation_closed=false`. V56b remains a valid development-set
winner on E200--E204, but it is not a confirmed universal middle-load winner.
No seed was deleted or replaced, no metric-triggered rerun occurred, and the
nine baseline methods were not rerun.

## Scientific closure

The preregistered failure action is binding: retain and report the failed
loads and metrics; do not modify the frozen profiles; do not reopen E205--E209
or E120--E129 for tuning; and do not claim that the original optimization
objective was achieved. V1--V56 remain rollback/audit points, while the exact
confirmation evidence remains immutable.
