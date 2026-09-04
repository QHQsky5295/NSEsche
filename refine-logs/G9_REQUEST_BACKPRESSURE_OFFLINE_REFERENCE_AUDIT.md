# G9 Request-Level Backpressure Offline-Reference Audit

Date: 2026-09-04 (Asia/Shanghai)

Input-binding commit: `d7fbac8ac27c98644a20e9eef2cb2c9a8b32b4c9`

Status: `references_complete_analyzer_freeze_required_before_online_execution`

## 1. Exact declared population

All 30 reference dependencies in the committed `g9.model.json` were built in
sorted reference-key order:

- 15 D81--D85 tapes covering low, middle, and high homogeneous 20-node load;
- one `ready_order` reference per tape;
- one `ready_request_backpressure` reference per tape; and
- no other method, seed, load, or operational identity.

The two NSESche identities deliberately use different reference keys because
the admitted player populations differ. Both continue to use the same
paper-defined social-utility objective and the same strict Eq. (15) placement
game inside their declared player populations.

## 2. Execution and integrity result

Every one of the 30 builds canonicalized on attempt 1. No partial attempt or
quarantine directory remains. The canonical tree contains 420 files and
265,351,044 bytes; its inventory object hash is
`b91c61ba52b6d59d852f72eb77b812866f120a10baf5f09c6e4bea76ee9a54a3`.
The reference-build ledger SHA-256 is
`0d99350f26c80df9d8ee15fa2d8da5c81bb00fab9d6588cad246c9868362d0b4`.

Independent post-build inspection verified all 30 table files and receipts:

- table SHA-256 equals the catalog and receipt in every case;
- table line count equals the receipt in every case;
- receipt reference key equals its catalog key in every case;
- all 30 table hashes are distinct;
- total table bytes: 4,902,250;
- total reference-state rows: 18,715;
- per-table row range: 83--998; and
- both `ready_order` and `ready_request_backpressure` identities are present.

## 3. Frozen bound artifacts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g9.reference.catalog.json` | 56,794 | `61e4db364391567bcf6714f00c4ca6cb0cd046d420ab21aad25ef80583e17b53` | `5db5cd58eb85ed78af3ca5fe67e430cb72b1d8ede456bfdb244af9c78d513558` |
| `g9.references.json` | 1,822,799 | `8ccf6831a1c2d4e045ba1b95f0a145fd590a6d68cc7945817a1641c2ee7410bb` | `8c54c3d11d34248ef05cd3a634b5e3afe3bc1df4966cb9226e1866a8b94f3573` |

The final manifest passes the complete schema validator. It retains exactly
75 runs and 30 reference dependencies. All 30 NSESche runs have
`build_required=false`, and all 30 bind a unique reference table hash. The
frozen G9 runtime SHA-256 remains
`5f41999cd5c193e9fd989d74a72752760d493d3baa04cf9ac40bd7fee1ac5330`.

No online workspace existed during this audit, so none of the 75 G9/control/
baseline outcomes was exposed by reference construction or validation.

## 4. Authorization boundary

After this audit, catalog, final manifest, and ledger are committed, the next
authorized work is result-free implementation and testing of a G9-specific
analyzer/selector that mechanically evaluates all ten preregistered gates and
retains every run and failure reason. It may also construct a fail-closed
result-blind online selection over exactly the 75 final manifest run IDs.

Online execution remains blocked until that analyzer and selection audit is
committed. D86--D95 confirmation, Q61--Q80 formal replay, figures, and paper
performance claims remain blocked regardless of this reference-stage success.
