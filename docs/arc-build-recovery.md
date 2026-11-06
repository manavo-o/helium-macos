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

## Preventing the six-hour preflight timeout

Run `42059648704` was cancelled at roughly six hours while building the regression
executables. Its test dependency graph scheduled about 31,000 steps, including
content/Blink objects. That compilation was outside the normal phase deadline,
so the job never reached its checkpoint-saving action. It uploaded no new build
checkpoint; recovery must still use retained run `42042324498`.

For this exact link-only recovery, production CI now runs the retained test
executables directly. The reuse policy requires that baseline run and the exact
audited after-hashes for the two changed files. Application/test source changes
or a different GN delta fail this policy check. This is reuse of the seven
previously passing tests, not a fresh test compilation. Future functional changes
need fresh regression validation; do not reintroduce an unbounded test build in
the production job.

The native preflight links the retained Swift object with Chromium clang/lld;
it no longer invokes Ninja. The production build compiles any affected objects
inside the normal phase budget. Compiler-cache credentials and architecture
settings are configured before any compilation rather than only afterward.

Compilation stops at 4h30 elapsed job time, including setup/preflight, leaving
90 minutes for packing and uploads. Exhausted budgets save a resumable phase
without starting a compiler; forced termination at the deadline also resumes.
Early compiler failures remain failures. The existing next-phase workflow restores
saved outputs and continues. Checkpoint compression uses level 6 instead of 11
to reduce save-time CPU work; archives may be somewhat larger.

Eight cached-test policy/result tests, seven mocked build-budget tests, and five checkpoint
replay tests run before macOS resources are allocated. The budget tests invoke
no compiler. Workflow/action metadata is also checked with actionlint before
pushing changes. Diagnostics upload independently when checkpoint packaging fails.

The CI compile command now requests only `chrome` and `chrome/installer/mac`.
ChromeDriver is not part of this browser disk image and is no longer built as
an additional target. Existing driver outputs in checkpoints are preserved.

## Resuming the saved phase instead of reporting false success

Run `42121217689` saved checkpoint artifact `13474086644` after completing
20,457 additional build steps. Exit 124 was the intentional phase deadline;
there were no compiler failures and 57,363 steps remained. Its later phases
were incorrectly skipped because continuation conditions inherited GitHub's
implicit success check through a skipped resource-preparation ancestor.

Every continuation now explicitly checks cancellation, the previous phase's
successful result, and its `running` output. A final completion check fails
the workflow unless a phase actually reports `finished`; an uploaded checkpoint
alone is insufficient. Six tests cover this completion policy and continuation
conditions alongside eight checkpoint replay/selection tests.

The manifest now selects this newer checkpoint, which already contains the
audited native source delta. Exact resumes verify the patched source hashes
and preserve the saved GN configuration rather than running configuration
again. This retains the latest compiled outputs; it does not establish the
cause of earlier broad compiler-cache misses. The manual resume entry point
uses the same continuation workflow and Xcode 27 runner as production CI.
