# NSESche operational development V22 handoff

V22 used a fresh, permanently non-formal E21-E25 development cohort. Five new tapes were captured before performance inspection. Nine baselines (45 runs) and three NSESche candidates at operational indifference epsilon 12, 15, and 18 (15 runs) then ran result-blind on identical tapes and common HPA.

All 60 online runs canonicalized on attempt 1, all QC and pairing gates passed, online quarantine was empty, and `serverless_sim/records` remained empty. Four reference-build technical attempts remain quarantined: concurrent startup caused two pre-simulation JSON parse failures for V22a/E21 and V22c/E21 before both canonicalized on attempt 3. This exposed a shared `module_conf_es.json` writer, so all online simulations were subsequently serialized.

No candidate passed. Jiagu led throughput at `1.3446` thousand requests/s and Greedy led QPR at `0.0478380`. V22a/V22b/V22c achieved throughput `1.3062`/`1.3062`/`1.3060` and QPR `0.0405705`/`0.0405874`/`0.0406064`; none ranked first in either metric. The epsilon axis is therefore closed without subdivision and E11-E20 remain sealed.

The V22 plan SHA-256 is `62512b91dd13b9265170430e3a76b3dcc78671047f23de0f7f2b5691f4c65197`; the result screen SHA-256 is `dde4a6a830f511ec067627c1adb63a02a51660def53aaaf15d0c5e8e11ff7947`; baseline pairing SHA-256 is `91f3c50d890a4b4f5f17ced1aa80ffe1566c59600223a74209dd3cc0bdaebe24`.

Any further development must not reuse E21-E25 for tuning. E26-E30 were declared in the V22 source manifest but never captured or executed and may serve as the next fresh development cohort. A defensible next mechanism is an outcome-blind operational proxy that combines Greedy's memory-first placement with Jiagu's warm-container/current-demand ordering; it must be implemented and preregistered before any E26-E30 tape capture or performance run.
