# P1 Theory, Reference, and PoA Response Material

Status: evidence-complete and manuscript-ready within the stated scope. This
file is insertion material, not a claim that an unavailable revised manuscript
has already been edited.

## R1-1 and R1-2: why the inner method works

We agree that finiteness and bounded utilities alone do not prove convergence.
We replace that discussion with a fixed-snapshot finite-improvement result.
For player $i$, write $a_i=h_{ri,i}$, $b_i=h_{fc,i}$, and $x_i=a_i b_i$.
After collecting the non-pair terms into $v_i(n)$, Eqs. (1)--(9) give

$$
u_i(s)=v_i(s_i)-a_i\rho_{s_i}
\sum_{j\ne i:s_j=s_i}x_j.
$$

For $b_i>0$, the function

$$
\Phi(s)=\sum_i b_i v_i(s_i)
-\sum_n\rho_n\sum_{i<j:s_i=s_j=n}x_i x_j
$$

satisfies $\Delta\Phi=b_i\Delta u_i$ for every resource-feasible unilateral
move. Zero-complexity players have $x_i=0$ and affect no other payoff; a
secondary sum of their utilities completes a lexicographic potential proof.
Consequently, sequential strict improvements terminate at a resource-feasible
pure equilibrium in at most $|\mathcal F|-1\le\prod_i|S_i|-1$ state changes.
With shared capacity this is a constrained PNE (equivalently, a pure GNE); with
independent candidate sets it is the standard PNE. The implementation's
$10^{-6}$ tolerance yields an epsilon-constrained equilibrium.

This proof is conditional on a fixed scheduling snapshot, fixed prices, fixed
candidate sets, and complete feasible initialization. We explicitly do not use
it to claim convergence of the changing outer loop.

## R1-3: mathematical role of Eqs. (19)--(20)

Equation (20), $\gamma=r_0\tanh(g)$, is nonnegative, increasing, bounded above
by $r_0$, and has diminishing sensitivity for $g\ge0$. Equation (19) applies
the common factor $c=1+\gamma\beta\Delta$ to immutable baseline prices. It
therefore preserves $\widetilde p_n/\widetilde p_m=p_n^0/p_m^0$ and avoids
recursive multiplicative drift. These are the precise advantages we claim:
bounded load sensitivity, preservation of the baseline price structure, and a
finite per-round adjustment for finite $\beta$ and gap. A common multiplier
does not create relative node discrimination and does not by itself prove
uniqueness or outer convergence; those stronger claims are removed.

## R2-1 and R3-1: inner equilibrium versus outer stability

We now distinguish three objects. An inner equilibrium has no resource-feasible
unilateral gain above $10^{-6}$ at fixed prices. A strong Nash--Social fixed
point would additionally require both the placement and price-feedback map to
remain unchanged. The implementation checks only whether successive inner
placements are identical (or the measured gap is numerically zero), so we call
the observed property **outer placement stability**, not a proved joint fixed
point.

Across 19,509 active scheduling windows from 20 paired seeds, all inner games
stabilized, with seed-level mean inner-round count 1.7054 (95% BCa interval
[1.6044, 1.8009]). Outer placement stability was 97.396%; nine windows
(0.0461%) hit the outer cap and no oscillation was observed. All 508 nonstable
outer windows are retained: 499 arose because the heuristic reference lay
below current welfare and feedback failed closed, and nine reached the
two-round cap. These measurements support the budgeted implementation but are
not presented as a universal outer-loop proof.

## R2-2: reference construction, updates, cost, and invalid cases

For the six 20-node topology/load cells, we constructed 120 seed- and
configuration-bound offline tables before online replay. Each table stores a
deterministic state-keyed estimate produced by canonical initialization,
multi-start local improvement, and simulated annealing. It is loaded once per
run and queried in every active scheduling window; no annealing is performed
online. A table must be rebuilt when its bound runtime, topology, load/profile,
seed, formula semantics, or reference-state key changes.

The 120 tables contain 117,138 state rows and required 1,794.156 seconds
(29.90 minutes) total build wall time, 1,644.844 CPU seconds, at most 269.009 MB
peak process-tree RSS, and 30.69 MB storage. Online lookup averaged 14.202 us
per active window (95% BCa [12.407, 16.103] us); the NSESche solve itself
averaged 27.435 us. Fifteen stored rows are nonpositive. If a reference is
missing, nonpositive, nonfinite, or below current welfare beyond tolerance,
the price update is skipped and the baseline-price/valid inner-equilibrium path
is retained.

All 19,509 active retained low-load windows found a positive reference, but
499 estimates (2.558%) were below current welfare and were explicitly labelled
search-suboptimal rather than treated as optima.

## R3-4: exact-small PoA and reference accuracy

We exhaustively enumerated 300 preregistered constructed games with three
nodes and 4, 6, or 8 players (100 games per size), covering 737,100 feasible
assignments plus every feasible unilateral deviation. An independent raw-data
implementation reproduced the utilities, equilibria, optimum, potential
identity, and PoA.

All 300 games had a PNE and the deterministic update reached one in 300/300.
Exact worst-PNE PoA had median 1.002848, p95 1.010731, and maximum 1.018114.
The offline estimator reached the exact optimum in 192/300 games; normalized
shortfall had median 0, p95 0.0935%, and maximum 0.2008%, and never exceeded
the exact optimum. We report these as exact results for the constructed small
population, not as a universal bound or proof that large-state SA values are
exact. Pricing/welfare comparators and QoS fairness remain separate R3-4 work.

## Suggested compact manuscript paragraph

Under a fixed scheduling snapshot, fixed adjusted prices, and a nonempty
resource-feasible assignment set, NSESche is a finite constrained weighted-
potential game. For positive-complexity player $i$, every feasible unilateral
move satisfies $\Delta\Phi=h_{fc,i}\Delta u_i$; zero-complexity players have
zero pairwise impact and are handled by a secondary potential. Sequential
strict best responses therefore terminate at an epsilon-constrained pure
equilibrium after at most $|\mathcal F|-1$ state changes. This result applies
to the inner placement loop only. We do not claim unconditional convergence of
the outer price loop; instead, we report its measured placement-stability,
reference-fallback, and iteration-cap rates.
