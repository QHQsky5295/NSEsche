# M1 Completion-Guard Implementation Receipt

Date: 2026-09-02 (Asia/Shanghai)

Status: sealed before release build, D21--D40 tape capture, or online execution

- Preregistration: `M1_COMPLETION_GUARD_PREREGISTRATION.md`.
- Parent commit: `9773791`.
- Modified scheduler source: `serverless_sim/src/sche/sche_nash.rs`.
- Scheduler source SHA-256 before this receipt commit:
  `4974f71ed0db65963584e53ffc4fb8765bf45c11fdac09ebb69eb8951e3fc77d`.
- Modified config validator: `serverless_sim/src/config.rs`.
- Config source SHA-256 before this receipt commit:
  `90039ee14785e8e85b576882459e28666c5790f3359aabd0693532e95fdd17aa`.
- Two-file implementation patch SHA-256:
  `72bf044ce2bb3d6e51adabe575a1cf921e8baa82f5c75bb8e33bfea208aeffae`.
- Paper equations, paper utility, price feedback, HPA, QPR, and baseline
  implementations changed: no.

Implemented exactly two new operational variants:

- `guarded_finish_05`, relative utility-regret radius 0.05;
- `guarded_finish_15`, relative utility-regret radius 0.15.

Both variants evaluate the existing dynamically admissible candidates and
unchanged paper utility.  A candidate must remain above the preregistered
relative utility floor.  The implementation then minimizes the existing
projected-finish score, with higher utility, current node, and node ID as the
frozen deterministic tie order.  It keeps the original utility-best result
unless projected finish improves beyond the existing numerical epsilon.

The reference-key candidate tag is distinct for both guards, and operational
refinement observation schema is advanced from 2 to 3.  The run-config record
explicitly reports the radius and marks guarded decisions as not strict paper-
utility best responses.

Verification before sealing:

- `cargo fmt`: passed.
- NSESche scheduler tests: 29/29 passed, including utility-floor and
  finish-improvement/determinism tests.
- Full Rust suite: 102/105 passed.  The unrelated metric file test passed when
  rerun alone.  The pre-existing mechanism-thread timing test still failed its
  wall-clock assertion; the Python consistency test used an interpreter without
  NumPy.  Neither failure touches NSESche or the new config values.
- Git whitespace check: passed with only normal Windows LF-to-CRLF notices.

No D21--D40 tape, offline reference, screen result, or baseline result existed
when this receipt was written.
