# Incremental Arc-style Helium builds

The Arc workflow requires a verified compatible checkpoint. It stops if source
fingerprints, patch hashes, substitution rules, or source preimages differ;
it does not silently fall back to a full Chromium build.

## Current baseline

The Swift runtime link recovery reuses failed run `42042324498`, commit
`f4b4ec5940d1cc95e729465922a3def410b105cb`. Audit run `42056862800`
verified that archive's digest and extracted all 28 affected native UI sources.
Their hashes match the source manifest verified by the failed build.

The active checkpoint delta changes two files: native link configuration and a
build-helper license comment added after the failed run. The exact preimages
are retained under `.github/checkpoint-preimages/arc-swift-runtime/`; replay
checks verify their hashes. Fresh builds receive the link fix through the
appended `arc-swift-runtime-link.patch` in the normal outer patch series.

The original native UI patches were checked against successful run
`41956948198`; this recovery retains the newer failed run's compiled objects
and ThinLTO cache rather than repeating that earlier source compilation.

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


## Swift runtime link recovery

Run `42042324498` compiled the native surface and passed all seven focused
routing/bubble tests, then failed at the final framework link. GN does not
propagate `ldflags` from source sets; the Swift library search path never reached
the linker. The repair uses inherited `lib_dirs`, explicitly links `swiftCore`,
and propagates the runtime rpath through an `all_dependent_configs` entry.

Recovery reuses that failed run's compiled output. Its checkpoint-specific delta
also includes the build helper license comment added after the failed run's
commit. Exact preimages accompany the delta for reproducible replay tests; the
runtime repair still checks the restored source hashes before making changes.

The new preflight checks the real framework Ninja flags and links only the
native Swift object with Chromium's bundled clang/lld. This catches runtime link
configuration errors before the expensive full framework ThinLTO link. The
previous local link check used Apple's linker and did not cover this path.
All compilation and linking for this recovery runs on GitHub.
