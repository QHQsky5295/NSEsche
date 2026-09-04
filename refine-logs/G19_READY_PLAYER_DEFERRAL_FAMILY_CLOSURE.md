# G19 Ready-Player Deferral Family Closure

Date: 2026-09-05 (Asia/Shanghai)

Status: `read_only_family_synthesis_complete_family_closed`

This document is a result-preserving synthesis of the already frozen G12,
G14, G16, and G18 reports. It creates no new metric, run, seed subset, or
scheduler candidate. The underlying QC-valid observations remain complete in
their respective closed products.

## 1. Question and fixed evidence

The question is whether another fixed ready-player admission cap or release
valve is justified after four preregistered variants were tested. The evidence
is limited to the complete development populations already reported before
this synthesis:

| Stage | Operational change | Seeds | Low T/QPR ratio | Middle T/QPR ratio | High T/QPR ratio |
|---|---|---:|---:|---:|---:|
| G12 | fixed global-ready admission | D91--D95 | 0.9976 / 1.0014 | 1.0009 / 1.0124 | 0.9877 / 0.9575 |
| G14 | one-window fixed-`N` release valve | D101--D105 | 1.0193 / 1.0179 | 0.9951 / 1.0270 | 1.1511 / 1.2712 |
| G16 | overflow-magnitude release valve | D111--D115 | 1.0077 / 1.0081 | 0.9445 / 0.9899 | 1.0306 / 1.1029 |
| G18 | one-window `ceil(5N/4)` soft cap | D116--D120 | 0.9999 / 1.0019 | 1.0000 / 0.9986 | 0.9810 / 0.9823 |

Ratios are candidate/control arithmetic-mean ratios copied from the frozen
stage reports. They are descriptive across disjoint five-seed development
banks and are not pooled into a new inferential estimate.

## 2. Family conclusion

No tested variant provides a dual-metric improvement at all three loads.
G14's large high-load gain is accompanied by a middle-load throughput loss
and failed preregistered robustness/secondary gates. G16 reduces the high-load
gain and has a material middle-load throughput loss. G18 makes the intervention
softer, but its low/middle effects are effectively neutral and it has a severe
high-D120 safety loss. G12 is likewise not an across-load solution.

The sign changes across loads, seeds, and intervention intensities show that
the unresolved problem is not a single globally safe cap magnitude. Selecting
another cap after seeing these outcomes would be an outcome-conditioned
extension of the same exhausted mechanism family.

Therefore:

- the fixed ready-player deferral/admission/cap family is closed;
- G12, G14, G16, and G18 remain negative development evidence and cannot enter
  formal figures or performance claims;
- no new threshold, cap fraction, persistence length, or load-conditioned
  deferral rule is authorized from this evidence; and
- the next efficient route is the paper-disclosed `r0`/`wq` parameter
  sensitivity path, using the unchanged `ready_order` mechanism and an
  independent fixed development bank.

## 3. Relation to the manuscript

The pivot does not alter Eqs. (1)--(20), Eq. (15), Eq. (19), the QPR
definition, or the scheduler mechanism. Both `r0` and `wq` are already present
in the submitted model and its parameter-sensitivity experiment. The new
development screen only asks whether the submitted low-load centre should be
retained or replaced by one of its four already planned axial neighbours.

This synthesis is an internal stopping record, not a manuscript result. It
authorizes no sampling by itself; the separate low-load parameter-screen
preregistration defines the only next population and gates.

