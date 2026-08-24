# NSESche operational development handoff — V50

V50 is a closed, immutable middle-load development cohort. It came within
about two percent of simultaneous throughput/QPR closure. No valid run was
deleted or replaced.

## Frozen identities and evidence

- Mechanism commit: `31893ebe4deaef6dc519e5168a4ff6f1f24e0670`
- Plan/runtime commit: `a27a21b576134046133a30c151e02430dcc69501`
- Source blob: `e0ad226e512dcd7b6141d3b027cb4a31d5ad1598`
- Source SHA-256: `54451e2ee292e667a01c1a84e3b0171644b8e1ec211d049762687f8459fb3749`
- Binary SHA-256: `4b90d1c6115db431cf113b6a6cb2bc7e1c94c5e51ac51384ad911b9f42ca0057`
- Plan SHA-256: `07a99b8e7c68237f2ea1cb4b75547d6216dd5ef52e7ee1573ce5e668e0b78fdd`
- Seeds E170–E174; E175–E179 and confirmation E120–E129 remained sealed.
- Five tapes, 15 references, and 60 online runs all passed on attempt 1 with
  zero quarantine.
- Joint pairing SHA-256: `593e72ba38eb6e2f18fb5f755110956f53fbe9dfffbd0ba0759ec94a44fb83d5`
- Joint pairing audit hash: `ddbe155593b0cd4aaf4d6b6438d7f68fcd0387298fa399fb6aa01654d37d202e`
- Result SHA-256: `158422f9994ebad47610424fa4760b2e85cda3aa997e87e4895a0bae81eb245c`

## Result and next bounded step

`v50b-repeat-jiagu-low12` ranked first in fixed-window throughput at 1.4854
requests/ms, 15.49% above FaaSRank at 1.2862. Its QPR was 0.1648851767,
rank 2, only 2.02% below FaaSRank at 0.1682766415. Both QPR conventions were
identical and all observations were finite. Density 8 had lower QPR and
density 16 also moved away from the optimum, so V51 should compare density
11, the immutable density-12 control, and density 13 using untouched
E175–E179. All older profiles, low/high frozen settings, and formulas remain
unchanged.
