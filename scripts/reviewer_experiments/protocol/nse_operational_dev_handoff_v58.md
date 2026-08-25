# NSESche operational development V58 handoff

V58 is a technically clean, scientifically failed development cohort. All 195
online runs were completed on the preregistered E220--E224 tapes before any
performance metric was read. The joint result-blind audit passed 15 load/seed
groups with 13 methods per group.

## Frozen provenance

- Plan: `nse_operational_dev_plan_v58.json`
- Runtime commit: `c34893e91dfbb159a591234b1210ebbf2ae0bbe1`
- Implementation commit: `4e71b0a7e4955f9d4fae660491531cb961bce5bc`
- Binary SHA-256: `38174088a5073b01d7a41cc559fd130b8d00fde4242f5dd0946bf63fe8ce2a49`
- Joint audit hash: `50b58844414575755291eef068d91c20ed349a82c95ba98257e6b8307a7aa2ce`
- Joint audit file SHA-256: `bbbf5fd23670e679da2b47ebc1fc73d2ca17b650985967e56fded7d8fac5bb5e`
- Result file SHA-256: `fea2df456af44c037f53565ae78b9eb5c0dbc63d06b58e0afe421a2731cc1098`
- Canonical rename receipt SHA-256: `80c951f1d1e3e2be331801e8b9cca1404db89554aa3118e825f2a934212603b0`

The single canonical directory repair was a same-parent atomic rename from
`attempt-01` to the run ID already declared by the ledger. Fifteen file hashes,
the manifest, and the ledger were unchanged; no result was rerun or edited.

## Simultaneous reveal

The preregistered gate required one candidate per load to be strictly first over
all twelve paired alternatives in fixed-window throughput, finite-only QPR, and
zero-completion-as-zero QPR.

- High passed: `v58b-srpt-ready-ocs` ranked first in all three metrics
  (throughput `0.3464`, finite QPR and zero-as-zero QPR
  `0.0026173145305277163`).
- Low failed: `v58a-srpt-ready-hiku` led throughput (`1.3768`), while
  `v58d-srpt-ready-hiku-ocs-borda` led both QPR conventions
  (`0.08751688061457523`). No single candidate passed all three.
- Middle failed: `load_least` led throughput (`0.65`), while
  `v58a-srpt-ready-hiku` led both QPR conventions
  (`0.02596962580821214`). No candidate passed all three.

Therefore `development_success=false`. The high profile is the only legal
load-specific V58 selection; low and middle remain unselected.

## Scientific boundary

- E220--E224 are permanently sealed and must not be used to tune a later
  candidate.
- E225--E229 remain untouched.
- All 195 runs, all 60 references, and the rename receipt remain retained.
- Any later low/middle candidate must be justified independently of V58 outcome
  values and evaluated on fresh tapes with a new simultaneous reveal.
