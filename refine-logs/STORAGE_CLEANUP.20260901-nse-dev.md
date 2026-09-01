# Storage Cleanup: Redundant `serverless_sim_game_nse_dev`

`C:\Users\99349\Desktop\serverless_sim_game_nse_dev` was an old isolated
development copy, not a registered Git worktree and not the active experiment
workspace. On 2026-09-01 it had been recreated only partially from an earlier
archive; no restore or experiment process was still using it.

Before removal, all non-`tmp`, non-build content was archived to
`E:\NSEsche_experiment_archives\nse_dev_historical_20260831\nse_dev_nonbuild_snapshot_20260901.zip`.
The archive contains 1280 files (40,295,235 uncompressed bytes), has SHA-256
`a3fba071ba9e6a0b670c68320121df8bf3dd402706695c76e72ff2fee2432371`,
and passed ZIP CRC plus restored-stream SHA-256 verification for every file.

The historical `tmp` tree was already preserved in
`E:\NSEsche_experiment_archives\nse_dev_historical_20260831\nse_dev_tmp_history_20260831.zip`.
That archive contains 156,556 files, has SHA-256
`060ad285a58b31a87918747a59ff50511c7fe6420444375ffd50a90803091bf1`,
and its receipt records full CRC and restored-file SHA-256 verification.

After confirming exact paths, zero reparse points, zero live process references,
both archive hashes and both verification receipts, the redundant directory was
removed. It contained 14,945 files and 7,977,887,115 bytes; C-drive free space
rose from 318.521 GiB to 325.960 GiB. Valid experiment artifacts in the active
closure worktree were not touched.
