# P5 corrected-QC resume preregistration

Date: 2026-09-05 (Asia/Shanghai)

Parent QC-correction audit commit: `b2cd222945c95f0fa438b5c28d1578cd7176e4a3`

Status: `result_free_resume_control_preregistered_online_execution_blocked`

## 1. Trigger

After the queue-semantics correction audit, an ordinary invocation for the
same first selected run consumed no attempt. The generic runner re-read the
two retained pre-correction failure reports, detected their repeated stored
signature, appended a second blocked batch, and returned before attempt 3.

The append-only ledger now has ten events. Events 8--10 are a no-op batch
(`batch_started`, `run_blocked`, `batch_finished`); there is still no
canonical result, no attempt-03 directory, and no additional simulator output.
Deleting or rewriting the old reports or ledger is prohibited.

## 2. Frozen resume control

Add an explicit corrected-QC resume option to the ordinary runner. It must
fail closed unless all of the following hold:

1. exactly one manifest run ID is selected and no experiment/method filter is
   used;
2. the supplied 64-hex signature equals the current repeated failure
   signature;
3. exactly attempts 1 and 2 are used, both are finalized under quarantine,
   attempt 3 is absent, the manifest maximum is three, and no canonical or
   live partial exists;
4. both stored reports failed only with `queue_semantics_mismatch`;
5. both retained attempts have exit code zero, are not timed out, and bind the
   exact run ID/spec, tape, reference, and result artifacts;
6. read-only re-evaluation with the current frozen QC source makes both
   attempts pass without rewriting them;
7. the supplied correction audit path is a file and its SHA-256 is recorded;
   and
8. an append-only `corrected_qc_resume_authorized` event records the old
   signature, attempt/report/result identities, current QC-source identity,
   correction audit identity, and next attempt 3 before launch.

Without this explicit option, the repeated-signature lock must remain exactly
unchanged. The option cannot reset the attempt budget, promote an old attempt,
select a new seed, or authorize more than the remaining attempt.

## 3. Prohibited changes

Do not alter the ready manifest, selection, simulator binary, algorithms,
paper equations, seed, method, workload tape, reference, model, admission,
active limit, horizons, drain deadline, metrics, or QC thresholds. Do not use
any QPR, throughput, latency, cost, completion, rank, or old-PDF value in the
resume decision.

## 4. Validation and authorization

Add directed tests showing ordinary repeated-signature blocking remains
unchanged and the explicit path both succeeds under all eight conditions and
fails closed under identity, artifact, issue-set, and scope mutations. Pass
the complete protocol and analysis suites, then commit a resume-control audit.
Only after that audit commit may the exact first row be invoked with the
explicit option to consume attempt 3.
