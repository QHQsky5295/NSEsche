# M1 Completion-Guard Screen Result Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: complete non-formal screen; family rejected; qualification forbidden

## Frozen boundary

The completion-guard family was preregistered before source modification or
D21--D25 execution.  It contained exactly the unchanged `ready_order` control,
`guarded_finish_05`, and `guarded_finish_15`.  The paper utility, Eqs. 1--20,
load-dependent `(r0, wq)`, QPR definition, common HPA, and six E1 cells were
unchanged.  D21--D40 were disjoint from both formal seeds and the failed
D01--D20 development family.

Runtime and protocol identity:

- scheduler source commit: `a049f61c91b697fb5e27b92b1901b2f141ab7ab7`;
- runtime SHA-256: `209a3375f563d07a9b4e304675ef7fbef351b956f6ef8106a082e95102f01804`;
- runtime bytes: 4,676,608;
- screen protocol commits: `97d13893f1e3def7a038795b477108f221166f2b` and
  `70813caef6e0fc25c188747a84346f521ba7d56a`;
- complete source manifest internal hash:
  `92edfcb4c2625968ba194ea47ba61fe5c8021228c796b5ae2c220b72bf13fa49`;
- ready screen manifest internal hash:
  `218ac9befdc0c22759baeaebe5f86d4a7067100eca4e839b48c444f3b3655ac1`;
- ready screen manifest file SHA-256:
  `26e56ab1c0f3b99c0217261ef87fd4d51c3431efdad09fe03102cac547a25298`.

## Dependency and execution audit

- 30/30 D21--D25 base tapes canonicalized on attempt 1;
- capture quarantine count: 0;
- capture ledger: 30 events, final hash
  `8c3f42ed49f395d158727144cfa1af8c43541f10b89a5792005af6724394e9e2`;
- tape catalog: 30 entries, file SHA-256
  `d6abfc0d0ed150f1e489413cba0aa83b61c8b5a0a894d442bb0c3a9cfd18646d`;
- 90/90 candidate-state-matched offline references canonicalized on attempt 1;
- reference quarantine count: 0;
- reference ledger: 90 events, final hash
  `9c1b7257f7491fc5ecab65c4b92818044f7565b7347b481f686ec3953523330a`;
- reference catalog: 90 entries, file SHA-256
  `ba63a321beb58c67d11557049ec755f2554708e390811b50e6e7e04bbebbd462`;
- screen: 90/90 canonical runs, every run on attempt 1, quarantine count 0;
- screen ledger: 182 events, final hash
  `7853fb105d87f70aaf0d8eb32bc4e7bface43552b61b41caab81c4610431b582`.

No candidate result was read before all 90 runs were canonical.  Every fixed
row was retained.

## Frozen selection result

The machine-readable receipt is
`runs/tscv1_m1_guard_a049f61_20260902/m1.guard.selection.json`.

- receipt file SHA-256:
  `09cda548fd5d152b2da7dbd1a48e67ded6a190de95a69a14661b89f87c74aacc`;
- internal document SHA-256:
  `d0a83ab56e26db0ec99dd941cbd3a0e4166415de28cae2dc150c0c934e56e3b2`;
- selected candidate: `ready_order`;
- status: `complete_guard_screen_family_rejected`;
- qualification authorized: false.

| Candidate | Worst of 12 relative metrics | Mean of 12 relative metrics | Joint-first cells |
|---|---:|---:|---:|
| ready_order | 0.750686 | 0.939454 | 2 |
| guarded_finish_05 | 0.537324 | 0.873390 | 2 |
| guarded_finish_15 | 0.511532 | 0.811635 | 1 |

Relative to `ready_order`, the guarded candidates had the following arithmetic
mean changes:

| Topology | Load | Candidate | Throughput | QPR |
|---|---|---|---:|---:|
| homogeneous | low | guarded_finish_05 | +0.75% | +19.38% |
| homogeneous | low | guarded_finish_15 | -2.77% | +8.07% |
| homogeneous | middle | guarded_finish_05 | -33.12% | -46.27% |
| homogeneous | middle | guarded_finish_15 | -32.86% | -48.85% |
| homogeneous | high | guarded_finish_05 | -4.38% | -3.39% |
| homogeneous | high | guarded_finish_15 | -11.15% | -15.53% |
| heterogeneous | low | guarded_finish_05 | +9.25% | +33.21% |
| heterogeneous | low | guarded_finish_15 | +5.93% | -13.32% |
| heterogeneous | middle | guarded_finish_05 | +4.02% | -10.01% |
| heterogeneous | middle | guarded_finish_15 | -15.22% | -48.21% |
| heterogeneous | high | guarded_finish_05 | -7.91% | -31.36% |
| heterogeneous | high | guarded_finish_15 | +13.86% | +6.65% |

The gains are cell-specific and do not support one global guard.  The frozen
global maximin rule therefore correctly retained the control.

## Mechanism diagnosis

The guard's projected-finish score uses the static window snapshot:
`startup_remaining + runnable + starting_resident + pressure`.  During
initialization and best-response updates it does not include the players
already placed into `state_without_player.node_aggregates` in the same window.
The published utility does include this dynamic joint-decision externality via
`other_impact_sum`.  Allowing 5% or 15% utility regret can therefore override
the dynamic balancing signal and repeatedly choose a statically attractive
node, increasing within-window concentration.

The two catastrophic homogeneous-middle seeds support that mechanism-level
explanation:

| Seed/candidate | Placement dispersion | Co-location conflict ratio | Mean pressure | Completion ratio | Cost/completed request |
|---|---:|---:|---:|---:|---:|
| D22 ready_order | 0.6228 | 0.2452 | 0.8860 | 27.08% | 0.8996 |
| D22 guarded_finish_05 | 0.4905 | 0.3825 | 0.9010 | 3.03% | 7.6983 |
| D22 guarded_finish_15 | 0.3220 | 0.5430 | 0.9028 | 3.11% | 7.5162 |
| D24 ready_order | 0.8398 | 0.1443 | 1.4005 | 10.22% | 2.9529 |
| D24 guarded_finish_05 | 0.8139 | 0.1732 | 1.6540 | 2.62% | 11.9227 |
| D24 guarded_finish_15 | 0.5693 | 0.4148 | 1.6600 | 2.35% | 12.6808 |

This is not a missing warm-container supply problem and not a reason to tune a
load-specific radius.  It is a mismatch between a static completion proxy and
the dynamic assignment state.  A scientifically defensible successor, if
authorized as a separate fresh-seed family, must make completion ranking
contention-aware rather than merely increasing or decreasing the regret
radius.

## Gate consequence

The protocol rejected qualification derivation with exit code 2 and created no
qualification manifest.  The D21--D40 1,200-run qualification is therefore not
run, and M2 remains unauthorized.  No fourth candidate may be appended to this
closed screen.
