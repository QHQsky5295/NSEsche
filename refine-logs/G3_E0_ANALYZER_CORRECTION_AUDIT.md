# G3 operational E0 analyzer field-path correction audit

Date: 2026-09-04  
Status: complete; one unchanged-product analyzer invocation is authorized

## 1. Implemented correction

Commit `a3ac15dd5729add8a9b06dc5b0a91ed552da9b33` implements exactly the
preregistered integration correction. In production code, the G3 operational
runtime validator now reads:

`decision_neutral_diagnostics.order_counterfactual_enabled`

instead of the nonexistent:

`observation.order_counterfactual_enabled`

No fallback or dual-schema acceptance was added. The validator still requires
the real emitted flag to be exactly `false`. The synthetic fixture now mirrors
the Rust run-config schema, and an explicit regression proves that a synthetic
`observation=false` cannot mask a true real counterfactual flag.

## 2. Diff and hashes

The reviewed production diff is one lookup-path replacement (four displayed
lines replacing two due to formatting). The only other changed file is its
test module. There is no simulator/Rust change, so the already executed
`93b572d` binary and every immutable run artifact remain valid.

- corrected analyzer SHA-256:
  `93a86896d633be89a0a26c21c237c4eceae7864b81808dcb695e17c445853821`;
- corrected test-module SHA-256:
  `29233deaa36d40f04cc8ed29b6bfe268389534e4ccb0dbc49c5f12cc720a2ce3`;
- pre-correction analyzer SHA-256:
  `9a60780e07357ccf94fce38c18aef90e893302d0f7b6198c6f557a69e0cddf9d`.

## 3. Verification

- corrected G3 operational module: 7/7 tests passed;
- combined G2/G3 protocol regression: 13/13 tests passed;
- Python compile-all: passed;
- Black check on the changed production/test files: passed;
- `git diff --check`: passed before commit.

The added test is
`test_runtime_stream_uses_emitted_counterfactual_field`. It explicitly sets
the real diagnostic flag to true while adding a false legacy-shaped field and
confirms fail-closed rejection.

## 4. Preserved data boundary and authorization

The first analyzer invocation exposed no metric and created no selection
artifact. No simulator rerun, import, promotion, deletion, seed change, or
artifact rewrite occurred. The existing product remains exactly 135 canonical
attempt-1 runs with a valid 272-event ledger.

Exactly one analyzer invocation is now authorized on the same
`g3_e0.ready.json` and `online/canonical` product. The complete frozen
selection, baseline, QPR, runtime, and 9x timing gates remain unchanged.
Formal execution and paper-ready claims remain blocked pending that result.

