# G17 Threshold-Safety Diagnosis (Closed)

Status: `complete_fixed_threshold_valve_family_closed`

This directory is the permanent root-level evidence package for the G17
read-only diagnosis. G17 used no new simulator run. It revalidated and
analyzed exactly the 15 retained G16/C0 D111--D115 pairs under a result-blind
analyzer frozen before the first extraction of unreported window features.

Only the integrity condition passed. The preregistered ordering selected
`h=4`, which predicts zero safe runs and reduces the optimistic diagnostic
envelope to C0. The nondegenerate `h=1.5` screen has balanced accuracy 0.45,
sensitivity 0.10, specificity 0.80, only two predicted-safe runs, and no
middle-load safe group. Therefore the fixed-threshold valve family is closed.
No implementation, new sampling, strong-baseline comparison, confirmation,
formal replay, figure, or paper claim is authorized.

The immutable source G16 workspace remains at:

`runs/tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904`

It is independently archived at the location recorded in the G16 closure.
Its 1,092 files, 395,532,897 bytes, and sorted inventory SHA-256
`28a7d5a16592e928e4c63d11901f76629c75d8a5041d69955baec12e36f04c9f`
were revalidated before G17 feature extraction.

Key commits:

- preregistration: `565334a`;
- frozen analyzer: `3177622`;
- result closure: `96fb9305a8ff4152bbd0498dfefd0486ec6ad4e7`.

The one-shot report has file SHA-256
`01f60135b6d9f1d9f91aa06a56096661186b0d758ab777041e0641e84a3b0464`
and document SHA-256
`eef43d9fe6fabedd5c99c4a3e9e43c9936ed1e1596d8109c4160bbf32078356e`.

Do not reuse D111--D115 to tune another threshold, select favorable seeds, or
present the optimistic G16-or-C0 envelope as measured performance.
