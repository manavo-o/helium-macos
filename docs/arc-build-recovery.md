# Incremental Arc-style Helium builds

## Restored avatar-fixture compatibility — November 6, 2026

Run [42294427007](https://github.com/manavo-o/helium-macos/actions/runs/42294427007)
passed fixture restoration and graph verification, then failed in the WebUI
`cr_elements` TypeScript test target. Its five TS2739 errors came from upstream
Chromium avatar objects missing `isCustomAvatar` and `isPlaceholder`, which
Helium's existing custom-avatar patches require on `AvatarIcon`. No browser
regression suite ran. The failed run retained its generated and compiled outputs.

The fixture restoration manifest now records explicit adaptations for four
upstream avatar fixtures (14 avatar objects) and the corresponding settings
mock's custom-avatar method. This changes test fixtures only. Product interfaces
are not weakened, assertions are retained, and no test target is skipped.
Exact upstream preimages are retained under
`.github/checkpoint-preimages/xenon-test-fixtures/`. Each adaptation verifies the
original file hash, replacement occurrence counts and final file hash before
writing; all outputs are checked before any fixture changes. An already adapted
file is accepted only by its exact postimage hash.

The previous fixture stamp migrates only when its package manifest exactly
matches the original pinned policy and every retained file still matches its
recorded hash. The stamp then records the adapted hashes for later phases.
Browser-source, GN and compiled-output preservation remain unchanged; these
explicitly audited test fixtures are the exception to leaving restored files
untouched. A targeted local type check reproduced all five original errors and
then passed all 14 updated objects against the actual Helium interface, using
the pinned TypeScript compiler. This was not a full WebUI/browser test build.
61 lightweight checks passed, including 15 fixture recovery/compatibility cases.

Continuation selects checkpoint `13542957750` from failed run `42294427007`,
SHA-256 `43eede4ba1c68538b03224dc99539ec093f08d479fc1fcedbcd41fb16b3bbb69`.
[Audit 42298748071](https://github.com/manavo-o/helium-macos/actions/runs/42298748071)
verified its archive, 25 product-source postimages and all four original avatar
fixtures. The resumed build preserves GN and compiled outputs, verifies the
retained fixture stamp, applies the exact adaptations and continues fresh tests.

## Missing test-source recovery — November 6, 2026

Run [42260582785](https://github.com/manavo-o/helium-macos/actions/runs/42260582785)
failed before compilation because source preparation prunes test fixtures:
`chrome/test/data/webui/chai_assert.ts` was the first missing dependency.
A graph inspection found 1,466 missing static inputs, including WebUI/PDF test
sources and the DEPS-pinned test font bundle. This was not a compiler failure
and no browser regressions ran in that attempt.

Before compiling fresh regressions, `github_restore_xenon_test_inputs.py` now
restores the required fixture packages from immutable Chromium revision
`a21ce95c24ce3964416f09ae1862f53f319eb4d0` (156.0.8078.79), plus the exact
33 MB font object and generation pinned in Chromium DEPS. The manifest binds
file names and bytes; Gitiles archive request timestamps are deliberately
excluded from the content digest. The font archive additionally retains its
DEPS SHA-256. Existing product sources, GN configuration and compiled outputs
are never overwritten; the explicit fixture adaptations above use verified
preimages and postimages. The MEI binary is restored solely as a test dependency;
the inherited production dependency removals remain in effect.

A read-only Ninja input-graph check rejects remaining missing source inputs
before compilation. Restoration shares the phase deadline, and errors remain
failures. Retained fixture files are hashed on subsequent phases. Regression
result signatures also bind the fixture manifest and restoration script.

The next build resumes checkpoint `13526212928` from the failed run, SHA-256
`2bf101ff9300ad0cefa9f3cd3c8164e26d7517b967749288e1792327199a0666`.
[Audit 42293524385](https://github.com/manavo-o/helium-macos/actions/runs/42293524385)
verified the archive and all 25 delta postimages. The checkpoint already contains
the source changes and regenerated GN files, so the restart preserves that
configuration. The original baseline/preimage audit below remains the provenance
for the delta itself. No passing test stamp exists yet; fresh regressions remain
mandatory before production compilation and packaging.

## Xenon functional changes — November 6, 2026

The new native refinement delta uses successful build `42156459305`, commit
`8f0097e9e90fdb2a32d0336b88f519aff27b64c3`. Linux audit
[`42258633447`](https://github.com/manavo-o/helium-macos/actions/runs/42258633447)
verified checkpoint artifact `13511187126` against its published SHA-256
`fd5474ae6308b44065d92894c2b27343a00d1e76e3943fac1e15a6db9c6660b2`.
All 25 required source preimages matched. Exact extracted preimages are retained
under `.github/checkpoint-preimages/xenon-native/`, with their hashes in the new
delta manifest. The ordered patch still replays with zero fuzz and verifies
postimages before changing restored source files.

This is a functional change, so the manifest specifies `xenon-native-v1`.
Retained link-only tests are not used as its validation. The normal phase
budget first compiles `browser_tests`, `arc_routing_tests` and
`arc_bubble_lifecycle_tests`, then runs all Arc command-bar cases and the new
pending-panel cancellation case, plus the routing and bubble suites. A passing
stamp binds results to source hashes, patch hashes, architecture and required
test names. Production browser/installer compilation runs only after that stamp
verifies. A failed test or missing result remains a failure.

Test compilation, execution and production compilation share the existing
4h30 deadline; timeout retains outputs and continues in the next phase. Fresh
test work is not an unbounded preflight. Completed test results can carry across
phases only with an identical validated signature. The historical link-only
policy below remains available for its original audited input; it does not
authorize skipping fresh tests for this delta.

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
