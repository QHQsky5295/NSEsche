# Proof Package

## Claim

The submitted manuscript informally suggested that bounded utilities and a
finite strategy space establish convergence of the complete NSESche inner and
outer loops. That claim is too strong.

The corrected claim is:

> For one fixed scheduling snapshot and one fixed adjusted-price vector, the
> strict sequential NSESche best-response process has the finite-improvement
> property over resource-feasible assignments. Starting from a complete
> feasible assignment, it terminates after finitely many strict unilateral
> improvements at a resource-feasible pure equilibrium. With the runtime
> tolerance $\varepsilon>0$, the terminal state is an
> $\varepsilon$-constrained pure equilibrium. This theorem does not establish
> convergence of the outer price-feedback loop.

## Status

**PROVABLE AFTER WEAKENING / EXTRA ASSUMPTION**

The fixed-snapshot inner claim is proved below. Unconditional convergence of
the changing outer loop is not currently justified and is explicitly removed.

## Assumptions

1. The player set $I$ and node set $N$ are finite.
2. Each player $i$ has a nonempty finite node set $S_i$. The set
   $\mathcal F\subseteq\prod_i S_i$ of jointly resource-feasible assignments
   is nonempty.
3. A unilateral move is permitted only when the resulting assignment remains
   in $\mathcal F$. Thus the theorem covers the implementation's shared
   container-memory feasibility rule.
4. During the inner loop, node pressure, utilization, adjusted price, the
   network proxy, function features, candidate sets, and existing-container
   state are fixed. These are scheduling-window snapshot quantities.
5. The update rule is sequential. A player changes node only when its utility
   gain exceeds $\varepsilon\ge 0$; the current node is retained on numerical
   ties. The exact theorem uses $\varepsilon=0$; the implementation uses
   $\varepsilon=10^{-6}$.
6. All utility components are finite. Resource intensity $a_i=h_{ri,i}$ and
   function complexity $b_i=h_{fc,i}$ are nonnegative.
7. A complete feasible initial assignment is available. If initialization
   reports an infeasible/incomplete assignment, the equilibrium conclusion is
   not asserted for that window.

## Notation

- $s=(s_i)_{i\in I}\in\mathcal F$ is a feasible node assignment.
- $a_i=h_{ri,i}\ge 0$ and $b_i=h_{fc,i}\ge 0$.
- $x_i=a_i b_i$ is player $i$'s pairwise impact.
- $\rho_n\ge 0$ is the fixed Eq. (6) pressure of node $n$.
- $v_i(n)$ contains all node-dependent terms in Eqs. (1)--(9) except the
  pairwise Eq. (8) externality: baseline reward, adjusted-price cost, quality,
  and social contribution.
- $I_+=\{i:b_i>0\}$ and $I_0=\{i:b_i=0\}$.

For a fixed snapshot, the implemented utility can be written exactly as

$$
u_i(s)=v_i(s_i)-a_i\rho_{s_i}
\sum_{\substack{j\ne i\\s_j=s_i}}x_j.
\tag{A1}
$$

## Proof Strategy

For positive-complexity players, multiply each utility change by $b_i$; this
symmetrizes the pairwise externality and yields a weighted potential. A
zero-complexity player has $x_i=0$, so it affects no other player's utility.
Those boundary players are handled by a secondary potential. Every strict
move increases the resulting lexicographic potential, and a finite feasible
state space precludes a repeated state.

## Dependency Map

1. Lemma 1 establishes the weighted-potential identity for $I_+$.
2. Lemma 2 establishes the one-way independence of $I_0$ players.
3. Theorem 1 combines the two lemmas with a lexicographic potential.
4. Corollary 1 supplies the finite state-change bound.
5. Propositions 2--3 establish only bounded structural properties of
   Eqs. (19)--(20), not outer-loop convergence.

## Proof

### Lemma 1: positive-complexity weighted potential

Define

$$
\Phi_+(s)=
\sum_{i\in I_+}b_i v_i(s_i)
-\sum_{n\in N}\rho_n
\sum_{\substack{i<j;\ i,j\in I_+\\s_i=s_j=n}}x_i x_j.
\tag{A2}
$$

For any $i\in I_+$ and any feasible unilateral move from node $o$ to node
$d$, with all $s_{-i}$ fixed,

$$
\Phi_+(d,s_{-i})-\Phi_+(o,s_{-i})
=b_i\bigl[u_i(d,s_{-i})-u_i(o,s_{-i})\bigr].
\tag{A3}
$$

**Proof.** Only player $i$'s non-pair term and pairs containing $i$ can change.
Therefore

$$
\begin{aligned}
\Delta\Phi_+
={}&b_i[v_i(d)-v_i(o)]
-\rho_d x_i\sum_{\substack{j\ne i\\s_j=d}}x_j
+\rho_o x_i\sum_{\substack{j\ne i\\s_j=o}}x_j. \\
\end{aligned}
$$

Because $x_i=a_i b_i$, factoring $b_i$ gives

$$
\Delta\Phi_+=b_i\left(
v_i(d)-v_i(o)
-a_i\rho_d\sum_{\substack{j\ne i\\s_j=d}}x_j
+a_i\rho_o\sum_{\substack{j\ne i\\s_j=o}}x_j
\right),
$$

which equals $b_i\Delta u_i$ by (A1). Since $b_i>0$, every strict utility
improvement by a player in $I_+$ strictly increases $\Phi_+$. $\square$

### Lemma 2: zero-complexity boundary

If $i\in I_0$, then $x_i=a_i b_i=0$. A unilateral move by $i$ changes no
other player's utility.

**Proof.** In (A1), player $i$ enters another player $j$'s externality only
through $x_i$. Since $x_i=0$, removing or adding $i$ to any node leaves every
$u_j$, $j\ne i$, unchanged. This holds for both $I_+$ and $I_0$ players.
$\square$

### Theorem 1: finite improvement and constrained equilibrium

Let

$$
\Psi_0(s)=\sum_{i\in I_0}u_i(s),
$$

and order feasible states by the lexicographic pair
$L(s)=(\Phi_+(s),\Psi_0(s))$.

Consider one permitted strict better-response move.

- If the mover belongs to $I_+$, Lemma 1 gives
  $\Delta\Phi_+=b_i\Delta u_i>0$. The secondary coordinate may change, but
  $L$ increases lexicographically because its first coordinate increases.
- If the mover belongs to $I_0$, Lemma 2 shows that all other zero-complexity
  utilities remain unchanged. Hence $\Delta\Phi_+=0$ and
  $\Delta\Psi_0=\Delta u_i>0$, so $L$ again increases lexicographically.

Thus every strict move strictly increases $L$. Returning to an earlier state
would return to the same value of $L$, contradicting strict increase. Since
$\mathcal F$ is finite, the sequence terminates. At termination no feasible
unilateral deviation improves any utility by more than $\varepsilon$.
Therefore the terminal state is an $\varepsilon$-constrained pure equilibrium.
For $\varepsilon=0$, it is an exact constrained pure equilibrium. $\square$

Under shared resource constraints this object is also called a pure
generalized Nash equilibrium. If $\mathcal F=\prod_i S_i$, it is the standard
pure-strategy Nash equilibrium requested by the reviewers.

### Corollary 1: finite state-change bound

No feasible assignment can be visited twice, so the number of strict state
changes is at most

$$
|\mathcal F|-1\le \prod_{i\in I}|S_i|-1\le |N|^{|I|}-1.
\tag{A4}
$$

This is a worst-case finite bound and can be exponential. The runtime's
four-round budget is an engineering cap, not the bound in (A4); only windows
that pass the logged equilibrium certificate should be labelled converged.

### Proposition 2: properties of the Eq. (20) gain

For nonnegative finite global load $g$ and $r_0>0$,

$$
\gamma(g)=r_0\tanh(g)
$$

satisfies $0\le\gamma(g)<r_0$, is strictly increasing for finite $g$, and has
diminishing sensitivity for $g\ge0$ because

$$
\gamma'(g)=r_0\operatorname{sech}^2(g)>0,
\qquad
\gamma''(g)=-2r_0\tanh(g)\operatorname{sech}^2(g)\le0.
$$

Hence Eq. (20) gives a bounded, monotone, saturating feedback gain. This is a
mathematical design property, not a convergence theorem.

### Proposition 3: common-multiplier invariance and nonrecursive bound

For an eligible positive reference $R$, finite current welfare $W\le R$, and
finite $\beta\ge0$, define

$$
\Delta=\frac{R-W}{R}\ge0,
\qquad
c=1+\gamma\beta\Delta,
\qquad
\widetilde p_n=p_n^0c.
\tag{A5}
$$

Then $c\ge1$. For positive baseline prices,

$$
\frac{\widetilde p_n}{\widetilde p_m}
=\frac{p_n^0}{p_m^0}.
\tag{A6}
$$

Thus the update preserves baseline node-price ratios while changing the common
price level. Because each round is re-anchored to $p_n^0$ rather than
multiplied recursively, a finite gap bound $\Delta\le\Delta_{\max}$ gives

$$
p_n^0\le\widetilde p_n
\le p_n^0(1+r_0\beta\Delta_{\max}).
\tag{A7}
$$

The finite fixed-snapshot state space supplies a finite $W_{\min}$ and hence
$\Delta_{\max}=(R-W_{\min})/R$ when $R>0$. If $R\le10^{-6}$, is unavailable,
or lies below current welfare beyond tolerance, the implementation applies no
feedback and retains the baseline price path.

Equation (A6) also identifies a limitation: the common multiplier does not
create new relative node discrimination. Equations (A5)--(A7) do not imply a
unique equilibrium, monotone welfare, or convergence of the outer mapping.

## Outer-Loop Definition and Non-Claim

Let $B(p)$ denote the deterministic, tie-broken inner equilibrium returned for
price vector $p$, and let $F(p,B(p))$ denote the Eq. (19)--(20) feedback map. A
strong Nash--Social equilibrium would be a pair $(s^\star,p^\star)$ satisfying

$$
s^\star=B(p^\star),
\qquad
p^\star=F(p^\star,s^\star).
\tag{A8}
$$

No current proof establishes existence or convergence to (A8). The runtime
uses a weaker stopping observation: two successive inner assignments are
identical, or the measured social gap is numerically zero. The revised paper
must call this **outer placement stability**, not a proved joint fixed point.

## Empirical Validation Bound to the Proof

The theorem is complemented, not replaced, by two preregistered products:

1. Across 19,509 active windows from 20 retained Q61--Q80 runs, inner
   stability was 100%, mean inner rounds were 1.7054, outer placement stability
   was 97.396%, nine windows (0.0461%) hit the outer cap, and zero oscillations
   were observed. The 508 non-stable outer windows comprise 499 below-current
   heuristic references and nine outer-cap cases.
2. Exhaustive enumeration of 300 constructed three-node games covered 737,100
   feasible assignments. Every game had at least one equilibrium, every
   deterministic trajectory reached one, and an independent implementation
   verified the potential identity. Exact worst-equilibrium PoA had median
   1.002848, p95 1.010731, and maximum 1.018114.

The offline estimator hit the exact optimum in 192/300 games; normalized
shortfall had median 0, p95 0.0935%, and maximum 0.2008%. These are
small-state validation results, not a universal large-state optimality bound.

## Corrections or Missing Assumptions

- Replace “finite and bounded therefore the whole algorithm converges” with
  Theorem 1 and its explicit fixed-snapshot assumptions.
- Use “resource-feasible constrained PNE” (or “pure GNE under shared
  capacity”) when joint container-memory feasibility is active.
- Reserve “Nash--Social equilibrium” for the strong fixed-point definition
  (A8). Report the implemented outer criterion as placement stability.
- State the complete-feasible-initialization condition and retain all
  infeasible, capped, or nonstable windows in empirical rates.

## Open Risks

- The theorem does not prove convergence while pressure, candidate sets,
  containers, or players change between scheduling windows.
- The theorem does not prove the outer feedback map is a contraction.
- The exact PoA distribution is population-specific and cannot be advertised
  as an analytic PoA upper bound.
- The large-state offline reference remains a heuristic estimate; the observed
  2.558% below-current incidence must be disclosed together with its fail-closed
  behavior.
