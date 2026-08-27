# V94 independent E3/E4 confirmation closure

## Outcome

V94 passed every preregistered E3/E4 operational confirmation gate against the frozen V87 advanced-baseline means. The V94 E3/E4 operational group is closed.

This is an independent three-seed confirmation (`E723`-`E725`), not a high-powered population estimate. Training (`E720`-`E722`) and confirmation remain separate cohorts and are not pooled. The confirmation values vary materially by seed; the claim supported here is limited to the preregistered complete-cohort mean gate.

| Scenario | Throughput mean | Frozen maximum throughput baseline | Relative margin | QPR mean | Frozen maximum QPR baseline | Relative margin |
| --- | ---: | --- | ---: | ---: | --- | ---: |
| E3 `spike5x50ms` | 0.463333 requests/ms | 0.103333, FaaSRank | +348.39% | 0.000520546 | 0.000160393, Hiku | +224.54% |
| E3 `sustained3x200ms` | 0.339000 requests/ms | 0.095000, OCS | +256.84% | 0.000202369 | 0.000154699, OCS | +30.81% |
| E3 `pulse4x4x50ms` | 0.391333 requests/ms | 0.127333, OCS | +207.33% | 0.000186875 | 0.000146967, OCS | +27.15% |
| E4 `steady` | 0.708667 requests/ms | 0.120333, Jiagu | +488.92% | 0.005588069 | 0.000712497, Jiagu | +684.29% |

Both preregistered QPR definitions have the same mean in every confirmation scenario because all 12 runs have finite QPR and nonzero completions. All 12 throughput and both QPR gates passed strictly.

## Frozen candidate

- E3 profile: `faasrank_native_faithful_terminal_ocs_srpt_ready_dual_window_safe_pareto`
- E4 profile: `faasrank_native_faithful_terminal_ocs_idle_warm_dominance_srpt_ready_dual_window_safe_pareto`
- Implementation commit: `66d4a867ca50fae29a030d0ddd9d88300ec09c61`
- Isolated binary: `tmp/nse_v94_build_66d4a86/release/serverless_sim.exe`
- Binary SHA-256: `9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77`
- Cargo.lock SHA-256: `9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb`
- Frozen module configuration SHA-256: `cc2eaf7f0637f9a7982ff71df661b56a9a9dd7e52f4385b96d25cae48fa216df`

The two V94 profiles and this binary are frozen. No further V94 runs, tuning, seed replacement, or selective rerun are authorized by this closure.

## Preregistration and baseline boundary

- Confirmation plan: `scripts/reviewer_experiments/protocol/nse_e3e4_srpt_terminal_dual_confirmation_plan_v94.json`
  - file SHA-256: `ba11cefa2af67a0347f126104922d3e94c501a9dce043965463719405a5cc90d`
  - frozen in commit: `7e9fe84`
- Training result: `scripts/reviewer_experiments/protocol/nse_e3e4_srpt_terminal_dual_training_result_v94.json`
  - file SHA-256: `c4d82d46fbd5fa703322bbe4dc58aa744985d8489dad52f58aa54efa47daf2b1`
  - result hash: `6d550c6ddac6613df052983a736844b357eed7db0d5dcfc5905dd2ad21d6daa7`
  - frozen in commit: `4b2f61a`
- Frozen V87 advanced-baseline source: `scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_plan_v88.json`
  - file SHA-256: `7d24e1846319513286cd45f13ca941942a7ed39c38fe642a4ed10052d795a0ab`

No advanced baseline was rerun. V93 reserved confirmation seeds `E716`-`E718` remain sealed and unopened. No training row was pooled into confirmation.

## Confirmation evidence

- Confirmation result: `scripts/reviewer_experiments/protocol/nse_e3e4_srpt_terminal_dual_confirmation_result_v94.json`
  - file SHA-256: `eb36fd25ce623dbe7ca18e836208244c40f7d254b40e228b41d2b21ceec50605`
  - result hash: `cba45bd87f85094a35d55fdb8cdce455a3b29480141fa8076f6f4111fb48fd38`
  - frozen in commit: `e347d4c`
- Joint blind audit: `tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94/joint-blind-audit-v94-confirmation.json`
  - file SHA-256: `a3038338350f1a1087e077fa8e1f0f2f5f2160a5a0f07653bcfadcb92a1390fd`
  - audit hash: `c8e450adb2e77826d22eac10c2364d36a2115eeb504beaf509c66a524397484c`
  - metrics consulted before audit: false
  - scientific summary files opened before audit: 0
- Ready manifest: `tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94/manifest.v94-srpt-terminal-dual-confirmation.ready.json`
  - file SHA-256: `256a8534de3121895760b28e5330093044e6ef0b85873ab7edecc4451e0d4e40`
  - manifest hash: `f68d33b2d3a07e0fcb05337fd88983993d508a0d1fd58ebbceff552bbd0639db`
  - 12 runs and 12 reference dependencies
- Confirmation configuration file SHA-256: `44c70f8bbf2429f5f332976300605e3dc27afeb35bb437c5dbde8a7bceb50397`
- Tape catalog file SHA-256: `9cb86b2a7b6113a5249e2d1b91d82566894d8dda2672d705abe5d598444a24bd`
  - catalog hash: `7d80cdb92cfcce6d7c768733d1bffe6c554442252540d05712feb0f3f6912851`
  - 3 fresh base tapes plus 9 deterministic burst derivatives
- Tape-capture ledger file SHA-256: `367899a4d02584acaba4b24e608f857c869b1cd1d7f494c586e90768c9f0e345`
  - 3 events; last hash: `c22494739883bd2aacfc27fad412b8330016998650cd3522634ab280f67a7c10`
- Reference catalog file SHA-256: `dfca3458b6a8713d11383d16a7d242df44de4a0f26c6ae5dd73cb1b8da20a115`
  - catalog hash: `63e37a000d650e2fb78602690c3d99ff5782c08d969dce9e5802d9ff7823a265`
  - 12 independently built references
- Reference ledger file SHA-256: `a6a9d55d76798202d0c1bce6745ea2667cb815520cb7c43ebe3dd2254c78db20`
  - 12 events; last hash: `e81ad25c6803f55da1edb1515a04c692ca767b206fdcb05ecf8d6746aab90e73`
- Run ledger file SHA-256: `240e730ca6c6483d0b466bc4aba4952652fa5583001f7db08126c4e5520f490a`
  - 26 events; 12 canonicalized, 0 blocked; last hash: `42f644ce29671210666fae25230b80f2a1788f59ea152ba75ae0c0526a576ab1`
- Pairing audit: `tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94/confirmation-v94-pairing-audit.json`
  - file SHA-256: `1957e99089ea23c7e810b387e852bdc02e3340cf5b94c6200375e1bfd28e31d7`
  - 12/12 groups passed; 0 failed

All three tape captures, all 12 reference builds, and all 12 online runs completed on attempt 1. There was no quarantine and no seed substitution.

## Runtime identity

The blind audit and pairing evidence bind every confirmation run to one runtime identity:

- Runtime Git commit: `5ffbd581dadfd0361d5c083a34de7e7957eacfb4`
- Binary SHA-256: `9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77`
- Python executable SHA-256: `a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384`
- Cargo.lock SHA-256: `9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb`

The blind-audit and reveal scripts were frozen in commit `5ffbd581dadfd0361d5c083a34de7e7957eacfb4`. Metrics were revealed exactly once after the joint blind audit passed.

## Preserved preparation incidents

Two preparation-only failures are preserved verbatim:

- `tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94.failed-prep-keyerror`
- `tmp/nse_e3e4_srpt_terminal_dual_confirmation_20260828_v94.failed-prep-reuse-schema`

Each stopped before tape capture, reference construction, or online execution and contains no scientific result. They are retained as control-plane incident evidence and must not be deleted or rewritten.

## Closure decision

- Close the V94 E3/E4 operational confirmation gate: **yes**.
- Represent this as independent `n=3` operational confirmation: **yes**.
- Claim broad population-level significance from these three seeds: **no**.
- Pool training and confirmation: **no**.
- Rerun baselines or selectively replace seeds: **no**.
- Open V93 `E716`-`E718`: **no**.
- Reopen resource scaling or tune V94 further: **no**.
