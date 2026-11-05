# Incremental Arc-style Helium builds

The Arc workflow requires a verified compatible checkpoint. It stops if source
fingerprints, patch hashes, substitution rules, or source preimages differ;
it does not silently fall back to a full Chromium build.

## Current baseline

The native UI patch set reuses successful run `41956948198`, commit
`8689a4d336a5bde7b1fb2caad64d207504b56765`. Audit run `42035346056`
extracted affected source files from that exact build archive. The manifest in
`.github/arc-checkpoint-delta.json` records three appended patches and all 28
source preimages and outputs.

The patches add the SwiftUI/AppKit command bar and appearance editor, restore
top navigation, toggle the Chat side panel, guard the anchored-bubble theme
notification crash, refresh native presentation and spacing, and complete
addresses from host-only prefixes.

## What restoration does

1. Match tracked build inputs and domain-substitution rules against the manifest.
2. Restore the pinned build archive, including compiled objects and build metadata.
3. Verify every affected source preimage.
4. Replay the entire ordered patch chain with zero fuzz in a temporary mirror.
5. Verify all output hashes before patching the real restored source.
6. Regenerate GN while retaining existing output files.
7. Let Ninja/Siso rebuild changed sources and affected dependents, then relink.

The Swift surface has an isolated compile action. It does not change the global
C++ toolchain. Preferences use a small dedicated header rather than adding new
constants to the broadly included common preference header.

## Checks and failed-build recovery

`test_arc_checkpoint.py` exercises actual patch replay, idempotence, preservation
of an existing object file, rejection of unexpected source/patch/domain inputs,
and refusal of a full-build fallback. Run it after updating the manifest.

CI compiles both the palette controller and native bridge before the main
browser build. It then runs focused routing and anchored-bubble lifecycle test
binaries. A failed preflight enters the failed-build archive path without
starting the main browser compilation. Existing compiled outputs are uploaded
for recovery. Cancelled jobs do not archive, because runner shutdown may not
leave time to save the large checkpoint.

The prior completion marker is removed after restoration. A failed new build
cannot package a previous binary as its result.

## Recording another delta

Use an append-only outer patch; leave earlier patches intact. Stage the patch
and `patches/series` before generating the manifest, because the fingerprint
covers tracked build inputs. Obtain affected source files from the exact
successful or recoverable checkpoint and verify the archive digest.

Run `github_create_arc_delta_manifest.py` with the baseline commit, run ID, and
`--baseline-source` directory. The generator verifies normalized quilt preimages
against that snapshot. Then run `test_arc_checkpoint.py` and select with
`--select --require-checkpoint` before committing.

Checkpoint sources have already passed Helium domain substitution. The repair
normalizes only hunk payloads for paths in the pinned substitution list; raw
outer patches remain unchanged for fresh builds. Rule and list hashes are part
of checkpoint compatibility. Source hash checks must not be relaxed.

This is bounded reuse across a recorded patch set. Changing the Chromium/Helium
revision, architecture, SDK, or toolchain requires a separate compatibility
audit. Rebuilding affected dependents and relinking remain necessary.
