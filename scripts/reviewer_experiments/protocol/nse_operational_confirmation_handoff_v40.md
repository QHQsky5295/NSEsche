# NSESche operational confirmation handoff V40

The one-time E11--E20 confirmation is complete and did not close the final
three-load objective. The frozen V40a/V8 profile must not be reported as a
universal winner, and E11--E20 must not be reused for tuning or a second
scientific confirmation.

## Provenance and result-blind gates

- confirmation plan commit: `72026df014758196a3d99d6e34a71bdaeea2e496`
- confirmation plan SHA-256: `3ad37f1cfdbb62580dfa4c9247516de9b9a689d071f26475dbcf780d5bde3c17`
- frozen scheduler binary SHA-256: `26c49f147dbfc291cdf540c2061c67ab18c1978187cc76fad5ffd3c083a3505b`
- ready manifest hash: `7712ac3c452971de3a803a5d7269e13721e072e1efcf1898b78e98b19796c905`
- ready manifest file SHA-256: `38fd1658d94476cd3d582d2f1f39dd0437c31344d349b6f8df84a1142059e3db`
- confirmation pairing SHA-256: `bdb8d15e79b6a6693f3b31c9093a2bbe28474cd26599be56c5711069943f6277`
- result: `tmp/nse_operational_confirmation_v40/confirmation-result.v40-e11-e20.json`
- result SHA-256: `04fa6810b92154af7e229c929c2faae7014a9a797a536450a77a76084bd7ba03`

The 30 confirmation tapes were exact audited projections from the frozen
formal E11--E20 catalog. Thirty offline references and 30 online NSESche runs
all canonicalized on attempt 1 with zero quarantine. All ledgers and 30
candidate pairing groups passed. Each candidate group matched the frozen
baseline group in workload-tape, function/DAG/QoS, node/network, seed tuple,
simulation, and common-HPA hashes. The 270 matching non-NSESche baseline runs
were reused without rerun.

One middle E17 optimized run and seven matching baseline runs completed zero
requests, so latency, cost, and QPR are honestly unavailable for those runs.
The result reports both the formal finite-only QPR mean and a conservative
zero-completion-as-zero sensitivity mean. Rankings below are unchanged under
both treatments; no missing value was silently imputed in the formal column.

## Revealed E11--E20 result

| Load | Frozen profile | Throughput | T rank | QPR | Q rank | Best baseline T | Best baseline QPR |
|---|---|---:|---:|---:|---:|---:|---:|
| low | V40a hybrid3 + LoadLeast + OCS x2 | 1.4233 | 2 | 0.0447498 | 4 | Orion 1.4257 | OCS 0.0534051 |
| middle | V8 Orion expert | 1.0046 | 8 | 0.0504283 (n=9) | 6 | FaaSRank 1.1348 | FaaSRank 0.0673777 (n=9) |
| high | V8 structural expert | 0.4535 | 1 | 0.00473841 | 2 | Jiagu 0.4384 | Jiagu 0.00478647 |

High confirms the throughput gate and misses QPR by only about 1.0%. Low is
within 0.17% of the throughput leader but misses the QPR gate. Middle is the
material failure: the development-era V8 profile does not transfer to this
independent seed block.

The result-informed next hypothesis may be tested only on a new development
cohort: retain the near-leading low V40a profile while testing OCS/Orion
initialization; replace middle with a FaaSRank-oriented profile; and replace or
augment high structural initialization with Jiagu current-demand placement.
The already declared but unused E115--E119 seeds are eligible for that new
development block. Any later confirmation must use a newly declared holdout,
not E11--E20.
