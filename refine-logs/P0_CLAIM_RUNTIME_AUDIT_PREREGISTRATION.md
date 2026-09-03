# P0 Claim, Reviewer-Evidence, and Runtime Audit Preregistration

Status: frozen before the detailed P0 extraction and runtime-path inspection  
Frozen at branch/commit: `agent/tsc-resubmit-final` / `0316699add4804f44a66b2029ea7f6c84f3ad89b`  
Scope: read-only source audit and documentation; no scheduler modification and no new experiment

## 1. Purpose

This audit implements Phase P0 of `TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V4.md`. It must establish, before any new run:

1. the exact reviewer issues that require evidence, revision, or both;
2. every material empirical and mechanism claim in the submitted manuscript;
3. which submitted claims are already supported, must be narrowed, or must be removed;
4. which reviewer requests can be answered from existing frozen artifacts and which require preregistered new experiments;
5. whether the paper-faithful `ready_order` runtime and its telemetry can be used without changing scheduling decisions.

This audit is not allowed to introduce a new mechanism, alter the submitted equations, select results after observing their favorability, or authorize a new run by itself.

## 2. Frozen inputs

| Input | SHA-256 / commit |
|---|---|
| Submitted manuscript PDF `（5-12V2）TSC_NSESche_Complete_IEEE_.pdf` | `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18` |
| Raw reviewer material `d883ca48-.../pasted-text.txt` | `ecb83fd9a6d874008c2c1684ff2bf866bd3fe8eac26609496bcfccd151ee8b31` |
| Prior experiment-plan attachment `4b41d04b-.../pasted-text.txt` | `d80061947daf7202393c6fad1fc4bd8e6e34bebadd28557d3b2b9c7df6b69309` |
| Governing V4 experiment plan | file `68369bd695e56232fba76d7be6b91e11d899a2e6372c08234635ea53ec8295c0`; commit `0316699add4804f44a66b2029ea7f6c84f3ad89b` |
| Experiment tracker at freeze time | `40d4507917489a29527a2fc94f75a293b54e87962881407ed3a587c5c2866346` |
| Paper-faithful corrected-runtime anchor | commit `98f822cf` (full commit and binary digest must be recovered from the existing audit trail and independently verified in the P0 runtime audit) |

The original workspace is a read-only rollback source. All P0 outputs are created only in `C:\Users\99349\Desktop\serverless_sim_game_revision`.

## 3. Deterministic extraction rules

### 3.1 Reviewer issues

- Preserve the raw reviewer file byte-for-byte; never overwrite it.
- Atomize only the English reviewer comments into IDs `R1-1` through `R3-4`.
- Treat translations, author analysis, and proposed replies as annotations, not reviewer text.
- Each issue must record: exact source line span, request type, required evidence, manuscript action, existing artifact, gap, and status.

### 3.2 Manuscript claims

- Record material claims from the abstract, contributions, model/algorithm text, evaluation methodology, result discussion, and conclusion.
- Each claim must include PDF page, section or nearby heading, a short faithful paraphrase, claim class, and disposition.
- Allowed dispositions are exactly:
  - `keep`: already defensible from frozen evidence;
  - `narrow`: retain only a bounded claim supported by identified evidence;
  - `remove`: current evidence does not support the submitted wording;
  - `pending-preregistered-evidence`: may be retained only if its stated future gate passes.
- Universal or unqualified superiority claims cannot be marked `keep` when any frozen formal stratum contradicts them.

### 3.3 Evidence mapping

- Existing formal confirmation data are distinct from development/diagnostic data.
- No QC-valid run may be excluded because of an unfavorable outcome.
- A frozen artifact can support only the scenario, seed set, metric definition, and runtime recorded in its audit trail.
- Missing evidence remains explicit; it cannot be replaced by argumentative wording.

## 4. Runtime and telemetry audit rules

The audit must inspect the exact `ready_order` source at corrected-runtime commit `98f822cf`, the archived formal executable if present, the current source, and representative formal logs.

It must answer these questions:

1. Is the exact formal executable still present, and does its SHA-256 match the frozen audit record?
2. Can later convergence/reference analysis be performed solely by parsing existing logs?
3. If additional telemetry is needed, can it be emitted after the scheduling decision from already-computed state, with no control-flow, RNG-consumption, ordering, or arithmetic change before the decision?
4. Is current `ready_order` scheduling code byte-/source-equivalent to the anchor path? If not, the anchor executable remains the only authorized runtime unless a separate equivalence test is preregistered and passes.

Decision-neutral telemetry requires all of the following:

- no new RNG call or changed RNG order;
- no changed candidate enumeration, sorting, comparison, tie-breaking, early exit, or loop bound;
- no changed floating-point expression used by scheduling;
- logging only after the relevant decision has been committed;
- identical per-request placement/action sequence in a paired deterministic replay.

P0 may specify such a replay but may not execute it without a separately frozen protocol.

## 5. Required outputs

The P0 audit is complete only when all of these files exist and are internally consistent:

1. `rebuttal/REVIEWS_RAW.md`
2. `rebuttal/REBUTTAL_STATE.md`
3. `rebuttal/ISSUE_BOARD.md`
4. `rebuttal/STRATEGY_PLAN.md`
5. `rebuttal/MANUSCRIPT_CLAIM_MAP.md`
6. `rebuttal/REVIEWER_EVIDENCE_MATRIX.md`
7. `refine-logs/P0_READY_ORDER_RUNTIME_TELEMETRY_AUDIT.md`
8. `refine-logs/P0_CLAIM_RUNTIME_AUDIT_RESULT.md`

The result audit must name exactly one next stage: either a concrete P1 preregistration, a required decision-equivalence protocol, or a documented stop condition.

## 6. Locked interpretation

- The resubmission may add equations, definitions, proofs, or instrumentation that clarify the submitted mechanism, but it must not silently replace that mechanism.
- The paper's submitted equations and mechanism are treated as fixed for the confirmatory path.
- Maximizing the chance of a favorable resubmission means aligning claims with reproducible evidence, not conditioning seed retention or experiment inclusion on observed rank.
- If the frozen evidence cannot support universal QPR and throughput leadership, the manuscript claim is narrowed to the scenarios and metrics that pass the preregistered gates.
