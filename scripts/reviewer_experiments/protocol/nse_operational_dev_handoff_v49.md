# NSESche operational development handoff — V49

V49 is a closed, immutable middle-load development cohort. It bracketed the
QPR/throughput tradeoff but did not produce a profile that was strictly first
in both metrics. All valid evidence is retained and no seed was replaced.

## Frozen identities

- Mechanism commit: `ac30997dd60a01be569ce1eb94f3c43ae21d0f69`
- Plan commit/runtime identity: `1a982a113221aa0b45ad19e40a61a2de8994cd84`
- Source blob: `f5744748d5787dba35fd4ab9613a94ae52bd9c34`
- Source SHA-256: `fd408905ea7962616ecfb7ba98a6d43dc2d9e9af6beb511532ae267e40e5d9e9`
- Release binary SHA-256: `d103d8c9946052b63cb81da5b8d17af6951e838e34f8f55c5f842b0dc02c4cb3`
- Plan SHA-256: `515eca2a0eb752476696eb58d46472b401fbcf9561db87c7a3efc52210e7df3a`
- Development seeds: E165–E169; confirmation seeds E120–E129 remained sealed.

## Execution and result-blind gate

- Five base tapes, 15 offline references, and 60 online runs completed on
  first attempts with zero quarantine.
- Joint pairing: `tmp/nse_operational_dev_20260824_v49/pairing.v49-joint-result-blind.json`
- Pairing SHA-256: `4a5c0c4614029da90597000f9839551034f3692051a0dbd9737f910690b0dc62`
- Pairing audit hash: `68f4072f6f732b44961003bc1f5cfe46b71161bea309a862cf47c798118e9168`
- The gate covered 60 runs, 12 methods, and five paired seeds before metrics
  were consulted.

## Revealed result

Result artifact:
`tmp/nse_operational_dev_20260824_v49/paired-screen.v49-middle.json`
(SHA-256 `4970a8927e257a53c77ad5198677fc1dffe54edf38ce5733a5cd4c0c377c548f`).

The density-6 candidate (`v49c-repeat-jiagu-low6`) was strictly first in both
QPR definitions at 0.0117149045. It led the best baseline, Jiagu at
0.0104116716, by approximately 12.52%. It did not close throughput: 0.6734
requests/ms, rank 4, versus Jiagu at 0.7488 requests/ms, about 10.07% lower.
All five QPR values were finite and both QPR conventions produced the same
ranking. Thus `selection=none` and `freeze_middle=false`.

## Next bounded hypothesis

V48 density 8 led throughput with a small QPR deficit, while V49 density 6
led QPR with a throughput deficit. V50 should use a new paired cohort to test
the existing density-8 profile plus density-12 and density-16 extensions.
This wider fixed dose screen is justified because V49 thresholds 2, 4, and 6
were identical on three seeds and differed materially mainly on E166; a
one-unit interpolation is unlikely to recover the observed 10% throughput
gap. The router remains outcome-blind and all older profile names stay valid.
