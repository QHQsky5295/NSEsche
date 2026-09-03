# G3 operational E0 analyzer field-path correction preregistration

Date: 2026-09-04  
Status: correction frozen before implementation and before any result exposure

## 1. Trigger and result-blind boundary

The complete 135-run D71--D75 online stage finished with exit code zero. Its
canonical product has exactly the 135 manifest run IDs, all from attempt 1,
with zero failed and zero quarantined directories. The 272-event ledger chain
is valid.

The first invocation of `analyze-g3-e0-operational` stopped on the first C0
run with:

`has the wrong operational selector config`

It failed before aggregate construction, emitted no throughput/QPR value, and
created no `g3_e0.selection.json`. No result, candidate ranking, or admission-
gate outcome was exposed before this correction was frozen.

## 2. Root cause

The analyzer correctly validates the operational schema, selection object,
player order, and no-counterfactual requirement, but the final requirement
reads:

`config["observation"]["order_counterfactual_enabled"]`

The real Rust `run_config` schema has never emitted an `observation` object for
this field. It emits the already established object:

`config["decision_neutral_diagnostics"]["order_counterfactual_enabled"]`

Direct, result-blind inspection of one C0, one C1, and one C2 `run_config`
event proves all three use the latter path with value `false`. Their remaining
frozen selector fields are exact:

- C0: schema 4, `single_ready_order_path`, no operational dispatch feedback,
  and the original deterministic ready-player order;
- C1/C2: schema 5, the exact O0--O4 order list, strict-PNE/welfare eligibility,
  frozen lexicographic ranking, candidate-specific first/every-round semantics,
  and operational dispatch feedback;
- all three: order-counterfactual observation and dispatch feedback disabled.

The unit-test fixture duplicated the analyzer's nonexistent `observation`
shape, so the six pre-run tests could not expose this integration mismatch.

## 3. Frozen correction

The only authorized production-code change is replacing the analyzer lookup
of `observation.order_counterfactual_enabled` with the real emitted lookup
`decision_neutral_diagnostics.order_counterfactual_enabled`.

The only authorized test changes are:

1. update the synthetic run-config fixture to use the real
   `decision_neutral_diagnostics` field path;
2. add a fail-closed regression proving a true real counterfactual flag is
   rejected even if a synthetic legacy `observation` object claims false.

No fallback accepting both paths is allowed. No formula, simulator source,
binary, run manifest, seed, tape, reference, runtime artifact, metric
definition, candidate, selection score, tie break, baseline gate, timing gate,
or threshold may change. No simulator rerun is authorized.

## 4. Verification and next gate

Before analysis may resume, the correction must pass:

- the complete G3 operational unit-test module;
- the affected G2/G3 regression modules;
- Python compile and Black checks;
- source-diff review proving the one-field production change;
- a committed correction audit with new source/test hashes.

Only then may the unchanged analyzer be re-invoked once on the same immutable
135-run canonical product. Formal execution and paper-ready claims remain
blocked regardless of the eventual D71--D75 outcome.

