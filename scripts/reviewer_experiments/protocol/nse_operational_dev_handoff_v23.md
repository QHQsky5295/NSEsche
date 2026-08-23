# NSESche operational development V23 handoff

V23 evaluated three preregistered, outcome-blind state proxies on the fresh, permanently non-formal E26–E30 cohort. Five new tapes were captured before performance inspection. Nine baselines (45 runs) and the Greedy-memory, Jiagu-current-demand, and fixed current-demand ensemble candidates (15 runs) then ran result-blind on identical tapes and common HPA.

All five tape captures, 15 reference builds, and 60 online runs canonicalized on attempt 1. All QC and pairing gates passed, every quarantine was empty, execution was strictly serial, and `serverless_sim/records` remained empty.

No candidate passed. LoadLeast led throughput at `1.4872` thousand requests/s and OCS led QPR at `0.0367492`. The closest candidate, Jiagu-current-demand, achieved throughput `1.4532` and QPR `0.0357517`, ranking second in both; it was respectively 2.34% and 2.79% below the two leaders. The fixed Greedy/Jiagu ensemble ranked fourth in throughput and fifth in QPR, while Greedy-memory ranked ninth in both. V23 is therefore closed without retuning on E26–E30, and E11–E20 remain sealed.

The V23 plan SHA-256 is `28ae87f13f9b1ff4159deedf3c57aa60d0f291968cc751db8790d059387acaaf`; the result screen SHA-256 is `50fe182a820ad6cba3c5dbdefd598adab84237c754ad840bb3d1dab397313683`; the baseline pairing SHA-256 is `dd3e47cf558e5b0b0cf24a1f1348bb3e2d467b3f906f0547df46f4a09df62e60`.

Any further development must not reuse E21–E30 for tuning. E04–E10 remain unused, and E11–E20 remain the only confirmation cohort. A defensible next development epoch may use fresh E31–E35 seeds and must be preregistered before capture. The result-informed mechanism hypothesis is narrow: retain Jiagu's current-demand/container-state ordering, but test a fixed load-balancing prefix or an OCS-style current-placement affinity signal to close the observed 2–3% gaps. It must not tune thresholds on V23 outcomes after E31–E35 are observed.
