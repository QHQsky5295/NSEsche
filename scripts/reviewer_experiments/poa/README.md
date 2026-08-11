# Exact small-instance PoA

This directory implements the separately budgeted 300 exact games from E6:
three nodes, 4/6/8 players, and 100 deterministic states per player count.
It enumerates every feasible assignment and every unilateral deviation, so the
reported ratio is an exact pure-strategy PoA for the constructed small game.

The payoff is the same decomposition used by `sche_nash.rs`: baseline utility,
node price, function-level quality weight, pairwise externality, and social
contribution. Node pressure, utilization, and price are fixed within one game,
matching one scheduling-window snapshot. All candidate containers are declared
as already provisioned by the common HPA, keeping this a placement-only test.

These are deliberately labelled **constructed small exact games**. They are not
presented as Azure-trace runs and are not mixed with the large-scale SA welfare
gap. A state with no positive worst equilibrium reports `exact_poa=null` and
retains the relative welfare gap when it is mathematically defined.

Run from the repository root:

```powershell
& 'D:\Anaconda3\python.exe' -m scripts.reviewer_experiments.poa.generate_games `
  run-ledger\exact-poa-games.jsonl
& 'D:\Anaconda3\python.exe' -m scripts.reviewer_experiments.poa.exact_poa `
  run-ledger\exact-poa-games.jsonl run-ledger\exact-poa-results.jsonl
& 'D:\Anaconda3\python.exe' -m scripts.reviewer_experiments.poa.verify_results `
  run-ledger\exact-poa-games.jsonl run-ledger\exact-poa-results.jsonl `
  run-ledger\exact-poa-verification.json
```

The verification pass independently enumerates all assignments and unilateral
deviations again for all 300 states, checks exact result equality and frozen
3-node/4,6,8-player coverage, then writes a hash-bound receipt. All three
writers use a `.partial` file and refuse to overwrite an existing result.
