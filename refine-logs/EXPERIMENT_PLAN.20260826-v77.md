# V77 formal E2 low/n100 NSESche overlay

V76 closed operational mechanism selection on twenty untouched E450--E469
workloads. Those runs are validation evidence only and are never reclassified as
formal samples. V77 binds the frozen V76 profile to the existing formal E2
low-load, homogeneous, 100-node, scale-5 cell on E01--E20.

The nine baseline methods are immutable reuse sources: 90 E01--E10 runs from
the audited initial E2 composite and 90 E11--E20 runs from the extension
workspace. All 180 baseline runs already exist on the exact formal tapes. No
baseline process is rerun. The twenty old `sche_nash` runs remain archived as a
historical implementation and are excluded from the V77 comparison; they are
not deleted or overwritten.

V77 creates exactly twenty new NSESche runs and twenty state-matched offline
references. Each new run reuses the corresponding E01--E20 formal scale-5 tape,
common-HPA contract, frozen FaaSRank model payload and simulator configuration.
The candidate pins every environment value in
`nse_operational_selected_profile_v76.json` and the exact V74 release binary.

This is a versioned-method overlay, not a claim that old baselines and new
NSESche used the same executable. The baseline executable remains
`ee07c609...e0d5`; NSESche uses `c6de3550...68ea`. Outside `sche_nash.rs`, the
Rust source delta is limited to an isolated-port selector in `network.rs` and
visibility-only exposure of two unchanged FaaSRank helpers. The audit must
verify identical tapes, common-HPA hash, workload profile, FaaSRank model
payload, simulation and cluster semantics before metrics are opened.

The gate is preregistered: across paired E01--E20, the V77 NSESche arithmetic
mean must be strictly largest among all ten publication methods for fixed-window
throughput, finite-only QPR and zero-as-zero QPR. BCa intervals and paired
differences are reported but do not change that mean-ranking gate. All twenty
candidate runs must pass on attempt one with zero quarantine. No seed deletion,
replacement, subgroup selection, candidate switch or post-reveal tuning is
allowed. A failure is retained and reported; it is not repaired by editing
results.
