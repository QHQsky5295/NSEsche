# Storage Cleanup: Recreated `serverless_sim_game_nse_dev`

The non-Git directory
`C:\Users\99349\Desktop\serverless_sim_game_nse_dev` reappeared after the
earlier 2026-09-01 cleanup.  It was not a registered worktree, contained no
reparse points, and had no external process references at deletion preflight.

The current snapshot was archived to:

`E:\NSEsche_experiment_archives\nse_dev_recreated_20260902\nse_dev_recreated_nonbuild_20260902.zip`

Verification evidence:

- preserved files: 66,158;
- preserved source bytes: 10,470,468,018 (9.751 GiB);
- archive bytes: 927,799,040 (0.864 GiB);
- archive SHA-256:
  `12a0462bad0342ee36e435222eb99f936fead2da69a27055b98b5dd2c48438b3`;
- inventory hash:
  `2eecff04a126240518be97c2fb772a69e70a357a79dfb55b0140036b63f01672`;
- final receipt hash:
  `80a44e80542f147d428cab318cd09f40e113db6dc8327824e359da104129b36f`;
- ZIP CRC: passed;
- every decompressed file SHA-256 and byte count: passed;
- source tree re-hashed against the archive immediately before deletion:
  passed;
- final `source_deleted`: true.

Excluded paths were limited to reproducible build/cache directories such as
`serverless_sim/target`, `serverless_sim/target_dev`, `target_*`,
`__pycache__`, and test/tool caches.  The historical `tmp` tree, source,
scripts, result receipts and figures were included in the archive.

The exact source directory was removed only after the two verification passes.
C-drive free space increased from 321.24 GiB immediately before deletion to
334.86 GiB after deletion.  The stable repository, the active historical
closure worktree and the new revision worktree were not touched.
