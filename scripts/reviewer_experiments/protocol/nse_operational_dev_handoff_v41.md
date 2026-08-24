# V41 load-specific expert development handoff

V41 is closed on the permanently non-formal E115--E119 cohort.  No seed was
deleted, replaced, or selected after observing an online outcome.  The frozen
E11--E20 baseline thresholds were not rerun.

## Frozen load-specific profiles

| Load | Profile | Mean throughput | Mean QPR | Frozen threshold T / QPR | Decision |
|---|---|---:|---:|---:|---|
| low | `orion_ocs2_borda` | 1.4520 | 0.0541153 | 1.4257 / 0.0534051 | freeze |
| high | `jiagu_current_demand` | 1.3342 | 0.0124722 | 0.4384 / 0.00478647 | freeze |

The low result is the complete five-run V41c cohort.  The high result is the
complete five-run V41a cohort.  Both strictly pass throughput, finite-only
QPR, and zero-completion-as-zero QPR gates.  The V41b low profile achieved
1.4014 throughput and 0.0583002 QPR, so it failed the throughput gate and was
not selected.

Pairing audit SHA-256 values are:

- V41a, all loads: `d8a38f67119b789928e901f55965e2a58fb0dde3501bf6e9b377890ba43cdd4b`
- V41b, low only: `c47bbb089c2cd7e702ac8e8c2136bc8c7165a0dd768070d0fd7e1f31a6764136`
- V41c, low only: `cafb729b392ad9d74cabfa13750159d91c7e88aa1abed791c7f6ebee4a862b29`

## Middle-load closure

No V41 middle profile is frozen.  V41a `faasrank_score` completed all five
runs but failed both gates (throughput 0.5340, QPR 0.00327661 versus frozen
FaaSRank thresholds 1.1348 and 0.0673777; the conservative QPR threshold is
0.0606399).

V41b and V41c never reached online execution for middle.  In both cases the
E116 state-matched reference build repeated the same frozen adapter limit:

- V41b: 1798.906 s and 1799.015 s, exit 2.
- V41c: 1798.797 s and 1799.438 s, exit 2.

The automatically started third V41c attempt was stopped after about 25
seconds under the preregistered rule that two repeated technical failures make
the candidate unavailable.  All completed and quarantined evidence remains in
`tmp/nse_operational_dev_20260824_v41`; no middle online metric exists for
V41b or V41c.

## Diagnostic and next cohort

The direct V41 FaaSRank proxy is not semantically equivalent to the frozen
FaaSRank baseline: the baseline uses `CollectTaskConfig::PreAllDone`, whereas
NSESche collected `All` DAG functions before applying the FaaSRank score.  V42
may test a preregistered ready-frontier FaaSRank operational profile on fresh
development seeds beginning at E130.  E120--E129 remain sealed holdout seeds.
Low and high stay frozen and must not be retuned in V42.
