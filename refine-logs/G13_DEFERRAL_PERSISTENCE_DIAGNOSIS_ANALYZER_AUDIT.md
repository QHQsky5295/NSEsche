# G13 Deferral-Persistence Diagnosis Analyzer Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `3a88c3768693a710dcf2e89555c9ac5091cd73e1`

Status: `zero_result_read_only_analyzer_frozen_one_invocation_authorized`

## Frozen implementation

`scripts/reviewer_experiments/analysis/g13_deferral_persistence_diagnosis.py`
is 27,471 bytes with SHA-256
`77b42a1ea26e8126a527921d92fba8f902805f8b4ead9ff666bc61f75b6359fe`.
It writes only to a previously absent G13 output directory and never mutates
the closed G12 root.

Before feature extraction it requires the exact 1,092-file,
390,090,635-byte G12 root inventory and fixed root hash; validates the bound
manifest and source-hash-bound online selection; validates the G12 report's
file and canonical document hashes; reconstructs and verifies all 62 online
ledger events; and reopens every candidate canonical directory through the
standard manifest/QC/artifact-inventory validator.

The analyzer then retains all 15 same-tape candidate/control pairs and computes
only the preregistered adjacent-window episode, queue-context, admission, and
paired-outcome fields. Ties use average ranks. Every overall/load-specific
Spearman coefficient, all 15 leave-one-run-out coefficients, both group
summaries, and all 15 leave-one-run-out group contrasts are emitted, including
undefined values as null.

The five-condition decision is an exact conjunction. Even a pass authorizes
only a later preregistration; the analyzer hard-codes implementation,
sampling, confirmation, and formal-progression authorization as false.

## Verification

- focused G13 tests: 9/9 passed;
- complete analysis regression suite: 135/135 passed in 102.248 seconds;
- Python compilation and Black formatting checks: passed;
- zero-feature input-contract dry validation: 30 manifest rows, 30 gate-report
  run rows, and 15 paired rows validated; and
- G13 output directory: absent.

The first dry validation exposed only a genesis-ledger sentinel mismatch in
the new analyzer (`None` versus the protocol's fixed 64-zero previous hash).
It occurred before feature extraction, was corrected, and the complete suite
and input validation were rerun successfully before this freeze.

After this audit commit, exactly one real read-only invocation is authorized.
No scheduler change, new input, or simulator execution is authorized.
