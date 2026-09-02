# NSESche TSC Resubmission Goal

## Objective

Rebuild the original paper experiments in chapter order and add only the
experiments needed to answer the TSC reviewers.  Preserve the paper's core
game-theoretic formulas while producing a single auditable NSESche
implementation whose throughput and QPR are competitive with the strongest
placement baselines.

## Authoritative inputs

- User objective:
  `C:\Users\99349\.codex\attachments\b1e9bcdb-1aaa-4ed5-b5b4-582d6f487cce\goal-objective.md`
- Approved plan:
  `C:\Users\99349\Desktop\serverless_sim_game\（NSESche）PLAN.md`
- Original paper:
  `C:\Users\99349\Desktop\serverless_sim_game\（5-12V2）TSC_NSESche_Complete_IEEE_.pdf`

Before every experiment or repository mutation, read the objective and plan
above.  The run manifest must record their SHA-256 hashes.

## Execution constraints

- Keep `serverless_sim_game` and `serverless_sim_game_e1_closure` unchanged for
  rollback and historical diagnosis.
- Develop the final revision only in `serverless_sim_game_revision` on
  `agent/tsc-resubmit-final`.
- Preserve the published utility, pricing, social-reference and QPR formulas.
- Use a common HPA/runtime, common workload tape and common feasible set for all
  methods.
- Optimize algorithm versions only on development tapes.  Never select,
  delete, replace or supplement a valid formal observation because of its
  result.  Failed formal banks remain auditable and a changed method receives
  a new disjoint confirmation bank.
- Keep only compressed, hashed evidence locally; archive immutable formal data
  on `E:\NSEsche_experiment_archives`.

## Paper-ready definition

An experiment group is `paper_ready_closed` only when all 20 paired formal
seeds pass QC, NSESche has the highest mean throughput and QPR in the stated
comparison, the complete statistical analysis is present, and the source-data
table and publication figure are reproducible from the frozen manifest.
