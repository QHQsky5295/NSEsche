# G3 Order-Counterfactual Protocol, Runtime, and Ready-Manifest Freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: protocol, analyzer, release runtime, and immutable 50-replay manifest
frozen before replay; exactly 50 diagnostic replays authorized; no candidate,
D71--D75 run, or later formal cell authorized

## 1. Scientific boundary

This freeze implements `G3_ORDER_COUNTERFACTUAL_PREREGISTRATION.md` without
changing the paper's Eqs. (1)--(20), strict Eq. (15), common HPA, workload
tapes, offline references, prices, iteration cap, or live `ready_order`
dispatch path. O0--O4 and E0 are observation-only outcomes reconstructed from
the immutable first-inner snapshot. Their results cannot be substituted for
observed throughput, QPR, latency, cost, or any G1/G2 result.

The only authorized next operation is a complete replay of the 50 declared
sources. Every QC-valid replay is retained. No result-conditioned seed,
stratum, order, threshold, or metric replacement is permitted.

## 2. Code and temporal freeze

The no-feedback Rust implementation was frozen earlier at source commit
`14a61d2dd225aaf3b94d8f4aa846640d223f3a89`. The protocol, schema, analysis,
and synthetic gate tests were then committed at
`721b7a1` (`analysis: freeze G3 order replay protocol`) before any G3 online
replay.

Frozen analysis surfaces:

- protocol builder:
  `scripts/reviewer_experiments/protocol/g3_order_counterfactual.py`, 15,618
  bytes, SHA-256
  `679c1af21bd2d88da62a381f243fc4f2eef5bd6919edcb39871f68994b43d35a`;
- analyzer:
  `scripts/reviewer_experiments/analysis/g3_order_counterfactual.py`, 37,955
  bytes, SHA-256
  `37e51891c25d6402783e27867914771665ac393e33f0b15202abf5aa9581d1d0`;
- shared protocol schema: 178,428 bytes, SHA-256
  `9b443dd5a8920ecdbcbd5d01af2ba9c20def89afeef7d41f7ff1cb69c25e8fd0`.

The builder refuses overwrite, fixes the 20+30 result-blind source order, and
requires exact hash bindings for each source run config, summary and
`nash_metrics.jsonl.gz`. The analyzer was frozen with the preregistered 1%
assignment-difference, four-of-seven coverage, 0.1% welfare-regression,
five-of-seven proxy noninferiority, and 1% proxy-regression gates. It sets all
eligibility outcomes false when any integrity gate fails and never uses
throughput or QPR to rank mechanisms.

## 3. Runtime identity

Dedicated executable:

`serverless_sim/target_g3_ordercf_14a61d2/release/serverless_sim.exe`

- bytes: 4,770,816;
- SHA-256:
  `3029160d8c18ba7130a1ed81bf90587e99d21f1a1848093e72e4c4d64629f891`;
- bound Rust source commit:
  `14a61d2dd225aaf3b94d8f4aa846640d223f3a89`;
- `sche_nash.rs` drift from that source commit: zero.

This target directory is dedicated to G3. The retained G1/G2 build trees were
not modified.

## 4. Immutable ready manifest

Manifest:

`runs/tscv1_g3_ordercf_q61q80_d66d70_14a61d2_20260903/g3.order-counterfactual.ready.json`

- bytes: 1,459,713;
- document hash:
  `d3f7b18cb4d51b09f7dbcc1ae2c1d3e01d59484e13aa847e8350a85e694b0a91`;
- file SHA-256:
  `5b55a4d5450895d4f22bc39823e2a67ce69c125d308a77e699b981564aa2af22`;
- declared runs: 50;
- reporting cells/strata: 7;
- bound workload tapes: 50 run bindings;
- bound offline references: 50;
- `formal_results_eligible=false`;
- `D71_authorized=false`.

The source manifests are fixed as follows:

- G1 Q61--Q80: document hash
  `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b`,
  file SHA-256
  `d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a`,
  exactly 20 selected NSESche homogeneous-low source runs;
- G2 D66--D70: document hash
  `8173ab619744d7794106489c67e5ef017160c90e5bdcc4dd597be075f9bcd3f4`,
  file SHA-256
  `d49bc3865244f9b231b7dba312819f4c715059ca4ce7d7bb97b185add7481f18`,
  exactly 30 selected C0 runs over all six cells.

The preregistration itself is bound by SHA-256
`30b7f69ec375e866c69d28dca93e67ab09842a812f9fd465227dbf3034589330`.
Manifest validation accepts the complete 50-run product and rejects altered
source coverage, runtime identity, equations/strictness flags, counterfactual
order list, eligibility thresholds, or formal-use status.

## 5. Verification before replay

- `cargo fmt --all -- --check`: passed.
- Focused deterministic-order, O0 reconstruction, read-only envelope, and
  deliberately-profitable-deviation rejection tests: 4/4 passed.
- G3 protocol/analyzer tests: 11/11 passed.
- Affected run-manifest, G1, G2, G3 protocol and analysis tests: 27/27 passed.
- In-memory construction from the real G1/G2 sources produced exactly 50
  runs, 7 cells and 50 references before the immutable ready manifest was
  written.
- Independent ready-manifest validation: passed.

Existing compile warnings are unchanged and do not affect these gates. The
two unrelated full-suite issues documented in
`G3_ORDER_COUNTERFACTUAL_IMPLEMENTATION_AUDIT.md` remain outside this
diagnostic boundary.

## 6. Zero-data boundary and next operation

At this freeze, the G3 run root contained only the ready manifest. There was
no `online` workspace, partial attempt, canonical replay, quarantine,
scientific observation, aggregate result, or candidate effect estimate.

The next legal operation is one result-blind execution of all 50 manifest
entries through the existing protocol runner, followed by canonical
verification and the already-frozen analyzer. A technical or integrity
failure permits only correction and a repeat of the same 50 sources. A valid
diagnostic may name at most the top two qualifying mechanisms for a separate
fresh D71--D75 candidate preregistration; it does not itself authorize D71.
