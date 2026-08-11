# E6 placement adaptations: CP-BR and OnSocMax-P

## Experimental boundary

E6 uses the same protocol as every other comparison:

\[
\text{placement policy}+\text{common HPA/cold-start/container runtime}.
\]

The registered scheduler names are `cp_br` and `onsocmax`. Both obtain their
only feasible nodes from `schedule_helper::placement_candidate_ids`, emit only
`ScheCmd`, process players in `(ReqId, FnId)` order, and use the smaller node ID
as their final tie-break. Neither policy can create or remove a container.

## Common post-hoc welfare basis

CP-BR and OnSocMax-P optimize different placement scores, so comparing their
native scores would not be a welfare comparison. After either policy has
returned its proposed `ScheCmd` assignment, a read-only evaluator applies the
same NSESche profile, baseline-price, externality, contribution, and social
welfare implementation used by `sche_nash`. It records, per scheduling window,

\[
W^{\mathrm{pre}}=W^{\mathrm{final,base}}=W(S;\mathbf p^{(0)}),
\qquad
g_{\mathrm{emp}}=
\frac{W^{\star}-W^{\mathrm{final,base}}}{W^{\star}},
\quad W^{\star}>0.
\]

The equality holds because the evaluator applies no price feedback. The
evaluator observes the returned assignment but cannot add, remove, or rewrite
commands. Its wall and thread-CPU costs are timed independently from both the
placement-policy call and the broader common mechanism.

An offline reference is state-dependent, and the state key includes the
evaluated assignment. Therefore every CP-BR/OnSocMax-P load and seed first runs
an identically configured `build` pass, then the formal `offline_required`
replay reads that method-specific, hash-bound reference table. Build/replay
assignment hashes and completion flags must match. A reference from an NSESche
trajectory is never reused for either comparator.

## CP-BR: constructed mechanism-matched comparator

`CP-BR` means **congestion-pricing best response**. Repository and paper
context did not identify CP-BR as a separately published end-to-end system, so
the manuscript must describe it as a comparator constructed in this study. It
must not be presented as a reproduction of prior work.

CP-BR shares NSESche's observable node pressure and fixed-window baseline
price:

\[
\rho_n=
u_n^{\mathrm{cpu}}+u_n^{\mathrm{mem}}+\frac{q_n}{12},
\]

\[
\pi_n=\bar h_n^r\,\frac{u_n^{\mathrm{cpu}}+u_n^{\mathrm{mem}}}{2},
\qquad
p_n=0.3(1+\rho_n)(1+\pi_n).
\]

For player \(i=(\mathrm{ReqId},\mathrm{FnId})\), its individual score is

\[
u_i(n)=10(h_i^r+h_i^c)-p_n(1+h_i^r)
+\frac{w_i^q(h_i^c+h_i^n)}{1+\rho_n}.
\]

The implementation performs at most four fixed-order best-response rounds and
stops early when the assignment does not change. It intentionally omits
externality, contribution, offline social reference, Nash-social coordination,
and the outer price-feedback loop. Consequently, CP-BR isolates the effect of
congestion pricing plus individual best response against full NSESche.

## OnSocMax-P: placement-only adaptation

The source mapping is the official article *Online Workload Scheduling for
Social Welfare Maximization in the Computing Continuum*, IEEE Transactions on
Services Computing, vol. 18, no. 4, 2025. The local source checked for this
implementation is `tmp/pdfs/onsocmax.pdf`, especially Algorithm 1, Eq. (22),
and the non-fractional discussion in Eqs. (40)-(41).

### Retained mapping

| OnSocMax element | Placement adaptation |
|---|---|
| Algorithm 1 receives jobs sequentially | Unsatisfied `(ReqId, FnId)` players are ordered by request arrival ID and function ID. |
| Available resource set \(\mathcal R_n\) | The shared HPA-created container candidate set. |
| Utilization \(\omega_r\) | Dominant normalized CPU/memory utilization, augmented by active indivisible function workload. |
| Workload \(x_{nr}\) | Dominant normalized CPU/memory demand of one indivisible function invocation. |
| Algorithm 1, line 7 | Selected-node utilization is updated immediately after each online decision. |
| Marginal scarcity price | Eq. (22) is implemented directly. |
| Non-fractional decision | Select one feasible node using marginal pseudo-welfare, consistent with the binary specialization in Eqs. (40)-(41). |

Resources are normalized to \(C_r=1\). We freeze
\(\iota=1\), \(\upsilon=4\), and deterministically solve Eq. (37) for
\(\hat\alpha\). The Eq. (22) price is

\[
\hat\phi_r(\omega)=
\begin{cases}
\iota,
&0\leq\omega<\hat\omega_r,\\[3pt]
\displaystyle
\frac{\upsilon-\iota}
{\exp(\hat\alpha)-\exp\!\left(\frac{\hat\alpha}{\hat\alpha-1}\right)}
\exp\!\left(\frac{\hat\alpha}{C_r}\omega\right)
+\frac{\iota}{\hat\alpha},
&\hat\omega_r\leq\omega\leq C_r,\\[6pt]
+\infty,&\omega>C_r,
\end{cases}
\qquad
\hat\omega_r=\frac{C_r}{\hat\alpha-1}.
\]

The original utility and provider-revenue functions have no one-to-one
observable counterpart in this simulator. We therefore expose, rather than
hide, the following bounded placement proxy:

\[
d_{i,n}=\iota+(\upsilon-\iota)
\left[0.55w_i^q+0.25a_{i,n}^{\mathrm{warm}}
+0.20a_{i,n}^{\mathrm{locality}}-0.20x_{i,n}\right]_{0}^{1},
\]

\[
\Delta\widetilde W_{i,n}=
\bigl(d_{i,n}-\hat\phi_n(\omega_n+x_{i,n})\bigr)x_{i,n}.
\]

The candidate with maximum \(\Delta\widetilde W_{i,n}\) is selected. The
quality term uses the frozen function-level \(w_i^q\) when heterogeneous QoS is
enabled; otherwise it uses the same frozen legacy load-level weight as NSESche
(0.5 for low and 0.6 for middle/high). The cost term uses the function's
normalized resource demand, and warm/locality terms are observable runtime
properties. If every common candidate lies above normalized capacity,
Eq. (22) assigns all of them infinite marginal cost. Because the common
simulator protocol queues requests and does not perform admission rejection,
the adaptation then uses the least-overflow candidate and records a normal
placement; this is a platform-semantic fallback, not part of the original
OnSocMax claim.

### Explicitly omitted claims

`OnSocMax-P` is not a complete reproduction of OnSocMax. It does not reproduce
continuous workload splitting, deadlines, parallelism bounds, a
time-expanded computing-continuum resource mesh, the full convex program
\(P_3\), ALM/KKT optimization, provider billing, or OnSocMax-controlled
provisioning. The paper and figure captions should call it a **placement-only
adaptation under the common HPA/runtime**. The original competitive-ratio
guarantee does not transfer to this adaptation.

## Tests and audit points

The two scheduler modules contain unit tests for deterministic tie-breaking,
selection confinement to the supplied common candidate set, `ScheCmd`-only
construction, and non-decreasing congestion/marginal prices. OnSocMax-P also
tests Eq. (37), the Eq. (22) capacity boundary, and the mandatory-placement
overflow fallback.
