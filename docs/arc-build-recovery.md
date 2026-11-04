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
