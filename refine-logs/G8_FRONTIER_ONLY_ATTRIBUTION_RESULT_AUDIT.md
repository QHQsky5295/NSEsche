# G8 frontier-only attribution result audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Analyzer audit commit: `429b56f`  
Status: `complete_no_g8_authorized`; lookahead-family mechanism search closed

## Integrity and retained products

The single preregistered real invocation completed with exit code 0. It retained
all 25 canonical runs and produced all 20 exact within-bank/same-tape pairs.
No simulator, workload, offline-reference builder, or scheduler ran. G2
D66--D70 was used only for its five C0/warm pairs and was not combined with
D71--D75.

| Product | Rows | SHA-256 |
|---|---:|---|
| `g8_frontier_only_attribution.json` | n/a | `a95860a5e4ca3ee3a087bd0067c160ff1e955ac76af9065b6a23548aa44905c7` |
| `g8_frontier_only_runs.csv` | 25 | `d5dd9cb28025d6e34c15dac2efdaf0fba453b1db2e8ed90ef3c048e5ab64547e` |
| `g8_frontier_only_pairs.csv` | 20 | `a46fb78395c36342dab271bf3d1b6e64230208f48df583a4a63f3e3c48b6adac` |

The JSON document hash is
`d43bf3e4ce1e603211a20ddd94a38850258a87d69a2e1100e0809b84e67180fb`;
recomputing the canonical object hash after removing that field gives the same
value. The JSON binds the two CSV hashes, all eight frozen input receipts,
seven code-source receipts, and all 25 canonical run receipts.

## Raw cohort outcomes

Values are five-seed means. Throughput is krequests/s.

| Cohort | Throughput | QPR | Latency ms | Completion | Parent-blocked mean | Resident mean |
|---|---:|---:|---:|---:|---:|---:|
| G2 C0 D66--D70 | 1.5104 | 0.040895436 | 138.8638 | 0.787860 | 0.0 | 443.2152 |
| G2 warm D66--D70 | 1.5508 | 0.042180784 | 125.2634 | 0.808689 | 0.0 | 418.6945 |
| G3 C0 D71--D75 | 1.1434 | 0.024900429 | 84.4634 | 0.598534 | 0.0 | 1219.8310 |
| G6 unrestricted lookahead | 1.0784 | 0.029572233 | 77.4537 | 0.564216 | 2012.8565 | 3309.6264 |
| G7 frontier-1 + warm | 1.0580 | 0.021155059 | 100.1229 | 0.553675 | 1045.8881 | 2324.7073 |

## Prespecified condition result

Six of seven conditions passed:

- G7 enforced maximum unfinished-ancestor depth 1 with zero violations in all
  5 seeds; G6 exceeded one hop in all 5 seeds (mean maximum depth 5.4).
- G7 reduced both parent-blocked and resident queue means relative to G6 in all
  5 pairs. Mean reductions were 966.9684 and 984.9191 respectively.
- G7 exposed positive warm-refined and lower-utility initial choices in all 5
  seeds; G6 had zero lower-utility initial choices in all 5.
- G7 had 14 exact `not_requested` active windows and exceeded G6 in 4/5 seeds;
  all other active-window reference shapes remained valid.

The sole failure was the exact B2 dual-outcome pattern. G7 minus G6 mean
throughput was -0.0204, but G7 lost throughput in only 2/5 pairs rather than
the required at least 3/5. It won throughput in D71, D73, and D74. Mean QPR was
-0.008417174 and G7 lost QPR in all 5/5 pairs. Therefore the conjunction is
false even though both mean differences are negative. This result cannot be
reinterpreted after exposure or weakened to authorize G8.

Descriptively, G7 minus G6 also increased latency by 22.6692 ms on average
(4/5 positive) while sharply reducing both queues. Its throughput difference
was highly seed-sensitive: the 95% descriptive paired-t interval was
[-0.2508, 0.2100], and leave-one-seed-out means changed sign. In contrast, all
five QPR differences were negative, although its interval still crossed zero
at this small development n.

G2 warm-only remained a directional, bank-specific hint: mean throughput
changed by +0.0404 (3/5 positive), QPR by +0.00128535 (4/5 positive), latency
by -13.6005 ms, and completion by +0.02083. Every corresponding 95%
descriptive interval crossed zero, so it does not rescue or confirm a general
performance claim.

## Interpretation and implication

The one-hop frontier control is real and removes much of the unrestricted
lookahead backlog, but the retained data do not isolate warm initialization as
the cause of a consistent throughput regression. Warm/frontier G7 loses QPR
uniformly while throughput varies in direction, and its incomplete reference
coverage is an additional integrity failure. The prespecified evidence needed
to justify a clean frontier-only G8 experiment is absent.

Consequently:

- `g8_candidate_preregistration_authorized=false`;
- `g8_implementation_authorized=false`;
- `new_sampling_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

No G8, G9, Q81--Q100, later formal cell, figure, or main-performance claim may
proceed from this branch. The next permissible work is a separately frozen
claim/scene feasibility audit over already retained products, followed by a
revised experiment plan. It must not search seed subsets or silently redefine
the primary metrics.
