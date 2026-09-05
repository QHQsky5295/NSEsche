# P5 first online canonical integration audit

Date: 2026-09-05 (Asia/Shanghai)

Parent resume-control audit commit: `022f9ad4d9f78a87ade0176fef86336252d0d361`

Status: `first_canonical_validated_remaining_eighty_nine_authorized_after_commit`

## 1. Canonical result

Run:
`TSCv1.E1.homogeneous.n20.low.greedy.FP5P01.1ce7b703`

The explicit corrected-QC resume appended its authorization evidence and used
only attempt 3. The runner promoted attempt 3 to the exact frozen canonical
path. Attempts 1 and 2 remain immutable under quarantine.

Independent read-only canonical validation passes:

- run-spec SHA-256:
  `f8a8ec2b1605d1a529dfd67b95cf6925403144b53d78bd18f478cfff449dcc36`;
- workload-tape SHA-256:
  `022d7a3484328932da24f771fa905fc3e5f1869231286a4dcfc499694720a07a`;
- offline-reference SHA-256:
  `f1adaae4bedd7a037701db14b1421dc7008141d22227b2a35ec2a0ecd0e38f06`;
- attempt: 3, status/classification: `qc_pass`/`qc_pass`;
- QC passed with zero issues;
- audit status: `canonical`, audit object hash
  `13198e4592e82ac4e9ee7341068dd5df6f7fde1921089b2b666115d08681a7d0`;
- 16 final files, 584,502 bytes, inventory object hash
  `30995bb4696e3adaa8942d7890275caf9adcdf1bc91191afec63425ba345d725`.

File identities:

- QC report: 7,797 bytes, SHA-256
  `390f74709d0e3958eb7c9798fe8db43841584a92c3788a15b0be74475c49670e`;
- attempt metadata: 1,839 bytes, SHA-256
  `5df9c1ffc831e4f0889319b6697e16d4b78ca10b6b0707c8d1584d636d001a85`;
- canonical audit manifest: 80,460 bytes, SHA-256
  `8c5eb01e8a80caf06dabda571eed5cde7571a25c37abcc91046d0eb3e14edfd9`;
- summary: 6,068 bytes, SHA-256
  `36c62cc11966f0dc26acf9560e21b5ea070f457434aae269213156c6d118b2df`.

No QPR, throughput, latency, cost, completion, rank, or old-PDF comparison was
used for canonical validation or continuation authorization.

## 2. Ledger and retained history

The online ledger has 15 events, 12,024 bytes, SHA-256
`22dd8c937abe96710ae6d4452d996b397c05c54270f4ff13a1468634ea400f13`,
and tip
`6388958cb6b326fd24e8016cff923208c7706b1d4ae7a72cf4c657531d632adc`.
Events 11--15 are, in order, corrected-QC resume authorization, batch start,
attempt-3 start, attempt-3 canonicalization, and batch finish.

Current counts are one canonical run and two quarantined attempts for the
first run. Nothing was deleted, overwritten, or promoted from quarantine.

## 3. Authorization boundary

After this audit is committed, run the remaining 89 selection rows in their
frozen load-major, seed-major, method-ordinal order. The first canonical row
must be skipped as already canonical; the corrected-QC resume option must not
be supplied again. Retain every first QC-valid result and all technical
attempts. Do not inspect relative performance until all 90 canonical rows and
the predeclared semantic duplicate are complete and independently audited.
