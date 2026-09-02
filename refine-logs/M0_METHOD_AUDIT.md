# M0 Formula-Consistent Method Audit

Date: 2026-09-02 (Asia/Shanghai)

## Frozen boundary

- Candidate: final formula-consistent operational refinement, version 1.
- Parent commit: `cbce6d6bfb482a8bed48de3ecccf7be274fb255b`.
- Audited source: `serverless_sim/src/sche/sche_nash.rs`.
- Source SHA-256 before commit: `fcb2756b3f9d589cd59f99ad103f6fb5ae0a4316323cdbde5bcd216ed2321bc8`.
- Patch SHA-256 before commit: `df7f4421dc24190df227a29dd1a85dcb2b45a97b8987f42ca380a27b342f770c`.
- Offline-reference state-key schema: 9.
- Operational-refinement schema: 1.

The paper's utility, heterogeneity, price-feedback, and welfare equations are unchanged. The refinement changes only the operational realization permitted by the frozen plan:

1. Players are request-function pairs and only dependency-ready functions enter a scheduling window.
2. Player order is deterministic: arrival frame, request ID, DAG topological rank, then function ID.
3. Every best response remains inside the common feasible placement set.
4. The current assignment is retained on equal utility; otherwise ties prefer running, then starting containers, then lower projected finish score, then node ID.
5. The tie-break is applied only within the existing utility epsilon and does not add a hidden load-specific scheduler.
6. Cached offline references use schema 9 so older tables cannot be silently reused after the operational refinement.

## Verification

- `git diff --check`: pass (the repository's Windows checkout emits only the expected LF-to-CRLF notice).
- `cargo fmt --all -- --check`: pass.
- `cargo test sche_nash -- --nocapture`: 24 passed, 0 failed.
- `cargo test -- --nocapture` with the default Python 3.14: 93 passed, 7 failed because that interpreter lacked `numpy`.
- Re-run with the existing `D:\Anaconda3` Python environment (NumPy 1.26.4): 97 passed, 3 failed.

The remaining three failures are pre-existing broad/legacy tests outside `sche_nash`:

- `request::tests::test_req_30_frame`: expected zero requests but observed four.
- `metric::tests::test_record_file`: parsed a shared/truncated JSON record (`expected ',' or ']'`).
- `mechanism_thread::tests::test_algo_latency`: timing assertion mismatch (`begin_frame:2 current_frame:3 calltime:2`).

They do not exercise the modified NSESche source. They remain recorded rather than suppressed. Formal/pilot execution still requires the protocol integration and determinism gates before any result becomes eligible.
