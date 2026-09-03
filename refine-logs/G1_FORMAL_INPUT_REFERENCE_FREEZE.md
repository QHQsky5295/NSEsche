# G1 Q61--Q80 formal input and reference freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: 120/120 workload tapes and 120/120 state-matched offline references
captured, audited and bound; homogeneous-low online execution is authorized;
formal online results remain 0/1,200

## 1. Paper-section decision

The common workload bank and offline social-utility reference layer for the E1
20-node comparison are complete and reusable.  This closes only the formal
input/evaluation-baseline substage.  It does not close Fig. 6, Fig. 9 or any
performance claim, because no Q61--Q80 online placement run has yet executed.

The first and only currently authorized online cell is homogeneous low:
`10 methods x 20 paired seeds = 200 runs`.  Homogeneous middle remains locked
until the low cell completes canonical QC and NSESche is strictly first in
both mean throughput and mean run-level QPR.

## 2. Frozen manifest and artifact identities

- Protocol implementation commit:
  `125a741b7cffec1973f8d6632c781f9ff83d38ac`.
- Preregistration record commit:
  `b390df4cc74d57faa33b5385d29c1d4ed9454ffa`.
- Runtime source commit:
  `98f822cf2dcb878024a2ca39cc56533895ea692c`.
- Runtime binary SHA-256:
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Ready-manifest document hash:
  `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b`.
- Ready-manifest file SHA-256:
  `d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a`.
- Tape-catalog document hash:
  `2e782dce346ea627bca67e82ca0848889fd9f0c8bc1d0bccc6d1867556e1d143`.
- Tape-catalog file SHA-256:
  `9d0c274a24d54b8fb0fb7e8455650b2deb739feb45ac919d1a89dc4d308ecaa3`.
- Reference-catalog document hash:
  `c44c3dc6b0a570b60a65f535a08acddb2a628a6438c278839fffb933efdefafe`.
- Reference-catalog file SHA-256:
  `2df035cd419f4681646f760677d9a3332f4123cb7c050ac02027da7c0de7fc7e`.
- Frozen FaaSRank artifact SHA-256:
  `4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`.

The ready manifest validates with 1,200 unique run IDs and 1,200 bound tape
rows.  All 120 FaaSRank rows use the frozen model.  All 120 NSESche rows bind
one completed state-matched reference dependency.  No online-result stage or
canonical online run directory existed at this freeze point.

## 3. Workload capture audit

All 120 tape keys completed on attempt 1 and were promoted by verified exact
copy.  Every catalog SHA-256 equals its on-disk tape SHA-256, every key has its
exact canonical directory, and all 120 capture receipts exist.  The catalog
document hash validates.

There are 60 distinct event-stream hashes: for every `(load, seed)` pair, the
homogeneous and heterogeneous entries share one byte-identical request stream
while retaining two distinct node/network environment hashes.  All 60 paired
groups pass this identity rule.

| Load | Captures | Mean arrival rate | Minimum | Maximum | Plan target |
|---|---:|---:|---:|---:|---:|
| low | 40 | 1,925.45 req/s | 1,875 | 1,991 | about 1.9k |
| middle | 40 | 2,525.95 req/s | 2,456 | 2,633 | about 2.6k |
| high | 40 | 6,970.40 req/s | 6,755 | 7,436 | about 7.0k |

These rates are accepted without result conditioning and the tapes are frozen
for reuse by all ten methods and the later E2/E5/E6/E7/E8/E9 projections.

## 4. Offline social-reference audit

All 120 reference keys completed on attempt 1.  The catalog document hash and
every table, receipt, process-observation, simulator summary and welfare-log
SHA-256 validate.  The build produced 117,138 state rows, 120 distinct
state-pair sequences and 120 distinct assignment sequences from the 60 frozen
tape hashes.

Of the state rows, 117,123 are positive references and 15 are negative; no row
is exactly zero.  The 15 negative rows occur in nine tables and represent
0.0128% of all state rows.  They are retained.  The runtime will apply the
frozen explicit nonpositive-reference fallback and record its reason rather
than dividing by the nonpositive value or removing the run.

The nine affected tables are high-heterogeneous Q62/Q68/Q71/Q75,
high-homogeneous Q62/Q66/Q71/Q75, and middle-homogeneous Q68.  Middle Q71 has
zero completed requests in both topology-specific reference-build runs; this
shared difficult workload is also retained and must be discussed if it
materially affects the paired online comparison.

| Load | Topology | References | Mean state rows | Mean completed requests | Mean build time |
|---|---|---:|---:|---:|---:|
| low | homogeneous | 20 | 975.45 | 1,581.50 | 11.566 s |
| low | heterogeneous | 20 | 971.95 | 1,290.25 | 11.919 s |
| middle | homogeneous | 20 | 962.90 | 597.50 | 14.185 s |
| middle | heterogeneous | 20 | 962.65 | 407.90 | 13.480 s |
| high | homogeneous | 20 | 993.00 | 555.80 | 18.944 s |
| high | heterogeneous | 20 | 990.95 | 386.35 | 19.613 s |

Total measured reference-build wall time is 1,794.156 seconds and total
process-tree CPU time is 1,644.843 seconds.  Maximum observed process-tree RSS
is 256.55 MiB.  Reference tables occupy about 29.27 MiB; the complete current
run root, including reproducibility logs and workload captures, is 1.508 GiB.

## 5. Storage and publication boundary

The retained source data are under:

- `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/stages/capture_base_tapes/canonical`;
- `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/stages/reference_builds/canonical`;
- `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/q61-q80.formal.ready.json`.

There are zero `.partial` files after successful completion.  C-drive free
space is 327.13 GiB, so no storage-pressure deletion is required.  These
audited inputs and reference tables are final-paper dependencies and must not
be deleted.  After the first 200 online rows pass QC, the complete formal block
will be copied to the immutable E-drive archive and hash-verified as required
by the experiment plan.

No main-paper experiment is `paper_ready_closed`.  The next scientific step is
the homogeneous-20 low-load online comparison, followed by its result-blind
canonical reconciliation, dual-metric gate, statistics, old-PDF alignment and
Fig. 6 export.
