# Grain repaint and lower content corners

November 10, 2026. Base: `85d643fed783b061c366872c01e83f2310978988`.

The grain bitmap remains a shared immutable 128 × 128 pixel image at scale 2,
with its existing deterministic alpha values, toggle and presets. The patch
replaces repeated `DrawImageInt` calls with one `TileImageInt` call using the
browser-relative origin as its source offset. Chromium's pinned implementation
initializes a repeating image shader and records a rectangle. Disabled grain
never enters this code. At 1,440 × 900 DIP with an aligned origin, the previous
loop issues 345 image draws per painted surface.

A shared 10 DIP radius now supplies the website, common content-container clip
and native Home mask. Upper corners remain square against the revealed toolbar
and follow the existing reveal ratio as the toolbar slides away. The common
clip includes the outer content background and docked DevTools. Home also masks
its AppKit host, accounting for flipped coordinates and resizing. Masks are
reused when geometry is unchanged. Leaving single-page macOS vertical layout
removes the common clip/layer and clears Home's mask; split view retains its
existing per-pane rounding. Content fullscreen disables shared rounding.

## Verification record

- Patch order, patch parser, headers and whitespace lint: passed.
- Zero-fuzz replay of the appended patch: passed; all seven postimages match.
- Checkpoint replay/idempotence/fail-closed tests: 8 passed.
- Cached-test policy tests: 8 passed.
- Build-budget tests: 16 passed.
- Completion tests: 6 passed.
- Shell syntax and `git diff --check`: passed.
- No local Chromium compilation, linking or preview build was performed.

The source audit, compilation, packaging, visual matrix and runtime measurements
must be recorded separately; passing script checks do not establish UI or
performance correctness. The branch retains the base commit's `visual-only`
validation policy, without presenting retained executables as fresh test builds.

## Packaged-app comparison

Use the GitHub-built base app and fixed app with the same explicit preset,
intensity, light/dark appearance, window dimensions and display scale. New and
guest profiles currently have an unset-appearance glitch; an unset theme is not
a valid grain baseline. Keep private-window suggestions local.

Capture four traces (base/fixed × grain off/on), with identical live-resize and
sidebar-reveal sequences. Record UI-thread paint duration, compositor raster
duration and missed/presented frames, with trace categories and sample counts.
Inspect paint operations for one grain shader rectangle per painted surface and
no grain-related SaveLayerOp or nested DrawRecordOp. Report measured deltas only
after traces exist; source operation counts are not a latency measurement.

Inspect both lower corners on a high-contrast local page and Home in light and
dark mode. Include navigation between them, resizing, docked DevTools on each
edge, browser/content fullscreen transitions, split view and leaving vertical
layout. Exercise command-bar typing, raw-query Cmd+Enter, tab switching and
sidebar reveal. Record package hashes and screenshots alongside any failures.
