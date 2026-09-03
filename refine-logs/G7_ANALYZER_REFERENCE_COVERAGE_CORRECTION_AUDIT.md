# G7 analyzer reference-coverage correction audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Prerequisite preregistration commit: `3359daad5967dc37b0c8cfa6ca5ccee4f86b2fcb`  
Status: reporting-only correction frozen; one unchanged-product analyzer retry
authorized

## Implemented scope

Only the G7 analyzer and its directed test module changed. The simulator,
candidate mechanism, Eqs. (1)--(20), run manifest, five online products,
offline-reference tables, G3 controls, baselines, thresholds, and G6 analyzer
remain unchanged.

For every active G7 window, dispatch integrity is still fail closed. Reference
handling now has exactly two accepted shapes:

- `offline_table`: requires a nonnegative integer state key and finite
  reference value, then counts one hit;
- `not_requested`: requires explicit null state key/reference and explicit
  false cache-hit/feedback-eligibility flags, then counts one unreferenced
  active window.

Any other source, absent required field, partial value, or inconsistent flag
still raises a protocol error. The gate records one coverage row per seed and
requires `offline_reference_hit_windows == active_window_count` and
`unreferenced_active_window_count == 0` for every seed. Thus the retained
14-window G7 deficit must fail the total gate and cannot be reclassified as a
hit or omitted from the denominator.

## Source receipts

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/protocol/g7_frontier_warm.py` | `3b54bb50d7f4be80cb14dc8f27831cf1fe72227e563b803d1abec8df28139d43` |
| `scripts/reviewer_experiments/protocol/tests/test_g7_frontier_warm.py` | `4bbc00dd139a2ff8bd4437e5507da0d49ba9ae5e3c7d7f1627a897cb05219a4c` |

## Verification

- Python compilation: pass for both changed files.
- Black format and subsequent `--check`: pass for both changed files.
- G7 directed tests plus G6 regressions: 10/10 pass in 5.615 s.
- Complete generic protocol suite plus G2 initialization regressions: 46/46
  pass in 254.181 s.
- Total executed tests: 56/56 pass.
- `git diff --check`: pass.
- `g7.selection.json` remained absent throughout implementation and testing;
  no real retained-product analysis was run before this audit.

Directed tests prove that a fully referenced row can pass, the exact
`not_requested` shape is retained and forces the coverage condition false,
and a forged state key or alternate missing-table source fails closed.

## Authorization boundary

Exactly one invocation of the corrected analyzer is authorized on the
unchanged `g7.ready.json`, the same five canonical D71--D75 products, and the
same 50 frozen G3 controls. It must write the previously absent
`g7.selection.json`, report all metrics and conditions, and retain the
reference-coverage failure. No simulator/reference rerun, new seed, mechanism
change, threshold change, confirmation, formal progression, figure, or paper
claim is authorized.
