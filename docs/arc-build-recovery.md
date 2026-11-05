# Arc palette compiler repair

Run `41707908336` reached the Arc palette source and failed because
`Textfield::GetText()` returns `std::u16string_view`, while `Submit` accepted
`const std::u16string&`. The repair makes `Submit` accept a string view.

The run has a 5.29 GB `github_build_artifact_arm64` checkpoint from the last
completed build phase. The failed phase did not upload a newer checkpoint, so
its additional compiled objects cannot be restored from that run.

The Arc workflow selects that checkpoint only when all tracked build inputs
match this specific repaired version. CI scripts and documentation do not
affect that comparison. A source or configuration change makes the workflow
fall back to a fresh build. This is a bounded recovery for this failure, not
general incremental reuse across arbitrary source changes.

After restoring the checkpoint, the repair script verifies the palette's
original source hash, changes its parameter type, and checks the resulting
hash against the committed fixed source. It leaves compiled outputs intact.
It compiles the palette object before continuing the remaining browser work.

The shared build action now saves checkpoints after compiler failures as well
as successful phases, so future compiler errors need not discard a whole
phase's progress. Cancelled jobs are excluded because runner shutdown may
leave insufficient time to archive the build.


## Native UI checkpoint delta

The next native UI build can reuse successful run `41840388482`, at commit
`73343879470b7a090b5fce8d803809fa781120f9`. The committed manifest
`.github/arc-checkpoint-delta.json` records the exact current build-input
fingerprint, ordered patch hashes, and complete before/after source hashes.
The selector falls back to a fresh build if any build input differs.

Restoration verifies every affected source preimage, applies all twelve patches
in a temporary mirror, and checks the complete output hashes before modifying
the checkpoint. It then patches the restored source, rechecks hashes, and
regenerates GN with the current configuration. Existing compiled outputs remain
available for Ninja/Siso dependency analysis. Changed files, generated resources
and affected dependents are rebuilt; relinking the renamed app is still required.
This is bounded reuse for this recorded patch set, not arbitrary cross-version
cache compatibility. A four-case test exercises the real patch chain,
idempotence/output retention, and rejection of changed sources or patches.

To record a future append-only delta from a prepared local quilt tree, stage all
build inputs first, then run `github_create_arc_delta_manifest.py` with the
successful baseline commit and run ID, plus `--baseline-source` pointing to source files extracted from that exact verified artifact. Run `test_arc_checkpoint.py` before
committing. Do not reuse a checkpoint with a different Chromium/Helium revision,
architecture or toolchain without a new compatibility audit.


The first native-UI replay stopped because the checkpoint had already passed
Helium's domain-substitution step. Four preimages differed from the local raw
quilt copies: three split-view test files and one example in a preference
comment. Linux audit run `41922858223` verified the original archive digest and
captured all 51 affected source paths. The manifest generator now requires that
verified snapshot and compares it with quilt preimages after applying the
pinned Helium rules. Cached patch hunks are normalized only for files in the
pinned substitution list; raw patches remain unchanged for fresh builds.
Rule/list hashes are checked before cache selection. Full source hashes and
zero-fuzz patch verification remain mandatory. There is no relaxed hash check.
