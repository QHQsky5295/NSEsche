# P3 Low-Load Root-Cause Diagnosis Result Audit

Date: 2026-09-05 (Asia/Shanghai)

Status: `complete_no_p3_successor_authorized`

## 1. Scope and immutable population

P3 is a read-only diagnosis of all 25 first-QC-valid P2 low-load runs. It adds
no simulator run, offline reference, seed, setting, or paper-eligible result.
The population is exactly five settings (`centre`, `r0_minus`, `r0_plus`,
`wq_minus`, and `wq_plus`) on D121--D125, with 1,000 aligned scheduler windows
per run and 25,000 windows in total.

The source P2 canonical tree remains 375 files and 23,386,180 bytes with
inventory hash
`7a06b6a3ce83ef8c4beea21f0f26b1f486c1a87a671c075c3e46565383fd1e98`.
The P3 preregistration is commit
`5dca3a21acad8281db9fce69c6ac2097e0394805` and file SHA-256
`a4c565889c55f489c5aba2f8b92c6b837d571956b8fbce1b53214370338ed492`.

## 2. Transparent technical correction

The first analyzer invocation failed before creating any result file because
the initial implementation rejected the simulator's legitimate empty
outer-feedback trace in an inactive `A=0` window. The failed source, selection,
and absence of output are retained in
`P3_LOW_ROOT_CAUSE_ANALYZER_CORRECTION_AUDIT.md`.

The corrected implementation permits an empty trace only for `A=0`; all
24,345 active windows still require and contain a nonempty trace. No population,
metric, threshold, direction, or stopping rule changed. The corrected analyzer
is commit `72a12d8ea389540125654b7f3f49e1ff91b5497b`, file SHA-256
`baf9ff91fdcadc0d025455247ea94ec9d2e945ef49756ba446c8e142c14d17eb`.
The corrected selection is commit
`10ebd9ab233e88e6723e03b2b6191e3daa64a54c`, file SHA-256
`d1d7f5044bb8b05a3f92049b862c09b304d49621beb7dba9fc0d0447dd1b399b`,
and document hash
`84ba0b09273cf093c022d68aee14a88d3586df5532d8077bdacddbbc5be7f545`.

## 3. D1 and D2 parameter-path results

Both `r0` neighbours are operationally dormant under the frozen rule: all ten
seed/candidate pairs have the same final assignment hash and prepared-command
count as the centre in all 1,000 windows. Price signatures still differ while
assignments remain equal in 166--631 windows per pair, so the conclusion is
specifically that this local price-feedback perturbation does not change the
realized decisions in P2, not that Eq. (20) is globally irrelevant.

Both `wq` neighbours are decision-active. Relative to the centre, `wq_minus`
changes 48.38%--86.76% of aligned active-window assignments and `wq_plus`
changes 18.68%--86.54%. P2 nevertheless showed worse mean throughput/QPR for
both settings, so activity cannot be relabelled as success.

## 4. D3 centre-path results

All `A=R+S+C`, `B<=W<=A`, and `D<=P<=A` invariants pass in every retained
centre window.

| Seed | `D/P` | `(S+C)/A` | Non-running share, `D>0` | Non-running share, `D=0` | Direction passes |
|---|---:|---:|---:|---:|---|
| D121 | 1.7026% | 16.8637% | 11.6032% | 17.5976% | no |
| D122 | 2.2046% | 18.6637% | 9.2559% | 19.6253% | no |
| D123 | 2.7879% | 14.0307% | 5.1995% | 16.4563% | no |
| D124 | 0.5569% | 61.4871% | 54.6512% | 61.6548% | no |
| D125 | 1.4010% | 32.4155% | 19.0476% | 33.2819% | no |

The pooled descriptive rates are `D/P=1.8973%`, `(S+C)/A=23.8502%`,
running-warm availability `W/A=90.1047%`, and warm bypass `B/W=15.4874%`.
The pooled non-running share cannot replace the preregistered seed-level test:
only D124 and D125 reach 20%. No seed reaches the 5% differentiation threshold,
and in all five seeds the non-running share is lower, not higher, in `D>0`
windows than in `D=0` windows.

## 5. Frozen six-condition decision

The final conjunction is:

1. population, identity, alignment, and invariants: pass;
2. `D/P>=0.05` in at least four seeds: fail, 0/5;
3. `(S+C)/A>=0.20` in at least four seeds: fail, 2/5;
4. `D>0` non-running share nondecrease in at least three seeds: fail, 0/5;
5. both `r0` neighbours dormant: pass, 10/10 pairs; and
6. failed `wq` neighbours not relabelled: pass.

Because conditions 2--4 fail, contribution tempering (`mu=0.75/0.50`) is not
authorized for implementation, sampling, or a new preregistration. The closed
warm-init, lookahead, order, backpressure, remaining-work, and ready-cap/valve
families are not reopened.

## 6. Result identity and independent recomputation

The machine report is 58,482 bytes with file SHA-256
`b29488857646cd2de7cfd61ce369ef7f43a0b4fe13cb4416234d8ab6b1fb9ca2`
and canonical document hash
`45326991203070fdcae505fe15849d5a8424127db3784459180c441e1cce7410`.
Its four CSV file hashes are:

- D1: `e06fc4b18e9892e7e660db36844e1b0cfe3bd3534a2e2d12029c624b7a28fafe`;
- D2: `214b88575e0cb5fe094212f525057477fd75ac034229c1e7bbb07c1f69125395`;
- D3: `3b60262af1c7f06d87986d340efc3f54e7b2c224bb856b772262a037c0b859cd`;
- D4: `cecd2a228681801e68436236609072cd991e6bdd898e7458a1aaa33c5722c2b3`.

A separate script that did not import the P3 analyzer independently reloaded
the centre and paired compressed streams. The maximum absolute error over the
four D3 ratios was zero, all ten `r0` dormancy checks matched, all ten `wq`
changed-assignment counts matched, and the report document hash recomputed
exactly.

## 7. Paper and experiment consequence

P3 is internal negative development evidence, not a paper figure or performance
claim. It closes the remaining preregistered low-load local parameter-recovery
route. P2 formal Q81--Q100, strong-baseline sampling, E7 figures, and a renewed
low-load superiority statement remain blocked. The retained formal low-load
result must continue to report that FaaSRank leads the NSESche centre on both
primary means.
