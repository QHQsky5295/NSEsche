# NSESche operational development handoff V37

V37 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E96--E99/E00 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `bb8ee718c5d6f2387c70f1cc3ffcc0aebaccff4f`
- plan SHA-256: `3c4461907dc12ce6816b13fbb78bd466abd3f5bfaf5eeab525c351a7600843d3`
- scheduler code commit: `255517f44d5a474e60959b85b36ada0907bf9003`
- scheduler source SHA-256: `dd62798f2f427aa4ae4f1cfa85084ad965fcfde94c291d4eab889147dec422a0`
- scheduler source blob: `6e62acc44b1d7421a27004360be4778347d5d0b8`
- release binary SHA-256: `5ce90361a9e914a5293ccd8bd97ff57d03f52e8a57be4360771c76497a53f2fe`
- result: `tmp/nse_operational_dev_20260824_v37/candidate-screen.v37-fifth-vote.json`
- result SHA-256: `3d9a4fd6363bc9bd8471ff1283c9422a249979f165056e73f022f4b0009e0635`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 60 online runs passed QC and pairing; capture,
online, and reference quarantine counts were zero. Execution was strictly
serial, and `serverless_sim/records` remained empty. All 60 online runs shared
one Git, binary, Python, and Cargo.lock identity.

Two external directory-name artifacts were repaired without editing or
rerunning content:

- the V37b E98 reference directory was renamed from `attempt-01` to its unique
  catalog/ledger reference key; receipt SHA-256
  `d5bb23c98b7d41457c95692d40f86a71cfce99f986a6bc90a0b696b198d05ac7`;
- the Hash/E96 online canonical directory was renamed from `attempt-01` to its
  embedded and ledger-declared run ID; receipt SHA-256
  `528b00c3f0612c1ce17196903dda4cbc33858a6bf4a591cccdfaccc8b09fbf96`.

Both operations were same-parent atomic renames with before/after content-tree
hash equality. Catalogs and ledgers were unchanged.

## Revealed result

Greedy led E96--E99/E00 baseline mean fixed-window throughput at `1.4892`.
OCS led baseline mean per-run QPR at `0.0329070392`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V37a hybrid3 + Jiagu + Jiagu | 1.4260 | 2 | 0.0258257151 | 6 | no |
| V37b hybrid3 + Jiagu + Orion | 1.3936 | 7 | 0.0244280246 | 8 | no |
| V37c hybrid3 + Jiagu + FaaSRank | 1.4222 | 4 | 0.0291379701 | 3 | no |

No candidate strictly beat every baseline on either mean metric. V37a was
second in throughput but sixth in QPR; V37c had the best combined rank, fourth
in throughput and third in QPR. The preregistered fifth-vote family is closed
without subdivision. Frozen V8 remains the middle/high rollback winner and V11
remains the best low-load rollback point. E96--E99/E00 must not be reused for
candidate selection.

The two-digit development seed namespace is now exhausted. Any later
development cohort must first preregister and validate a disjoint extended seed
namespace; confirmation seeds E11--E20 remain sealed until a development
candidate passes both gates.
