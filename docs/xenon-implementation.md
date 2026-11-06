# Xenon native refinement implementation

November 6, 2026. Implementation follows the user's instruction after the research phase. Historical Arc observations and screenshots remain in `arc-gap-research.md`.

## Source changes

The append-only `patches/helium/macos/xenon-native-refinement.patch`, listed last in `patches/series`, contains the prepared source changes. Existing patches and the pinned submodule revision remain unchanged. Packaging changes also live in `sign_and_package_app.sh`, `.github/scripts/github_prepare_artifacts.sh` and `resources/dmg.json`.

| Requirement | Implemented source behavior |
| --- | --- |
| Xenon name | Product and installer branding, native appearance title, install-provider label, application packaging paths, DMG volume and artifact filenames use Xenon. Bundle ID, profile path, Keychain service/account and update feed retain their existing identities so the rename does not intentionally abandon user data. |
| Shared centered address interaction | Native compact address display opens the same palette as Cmd+L. Edit mode captures the original tab weakly and navigates that tab; a closed target cannot redirect into another tab. Cmd+T retains deferred navigation. A Home slot is reused on acceptance. |
| URL/security access | Full URL available on the native display's tooltip and selected in edit mode. A separate native site-information button opens Chromium Page Info anchored to the visible display. Generic location-bar bubbles use that display as their anchor. The real omnibox remains the internal model but is hidden in normal browsing UI. |
| Palette geometry and focus | Whole-window horizontal center, stable upper anchor, bounds/row-count updates on parent resize, minimum-window checks, parent-teardown handling, and focus fallback to toolbar when the previous view is no longer drawn. Parent activation notifications do not close the browser. |
| Results | Native pointer-driven selection with a stationary-pointer guard, matched text emphasis, additional existing-browser commands and lower empty-state appearance priority. Raw query and Command+Enter handling remain separate from presentation. |
| Sidebar state | Hidden browsing sidebar stays floating when temporarily revealed. Home forces visibility through the reveal state without changing the saved pin preference or treating it as docked. Leaving Home updates reveal logic from cursor/focus state. |
| Sidebar geometry and padding | Sidebar spans the top region instead of starting below the toolbar, with header clearance for controls. Docked toolbar uses the content region. Mac normal/maximized vertical layouts receive an outer inset independent of density. Existing overlay shadow machinery is reused. |
| Home and final-tab closure | Quiet native themed Home replaces the central Chromium shortcut page while retaining its underlying navigation slot. Home is labeled distinctly in the tab row. Closing the final regular non-private tab posts one Home insertion after tab-strip notification dispatch. Explicit window-close/shutdown and drag handling remain separate. |
| Sidebar utilities | Native appearance, downloads and settings controls in the lower sidebar area. No decorative Space controls or new organization database. |
| Material | Cached irregular static Retina grain replaces sparse regular dots. Grain and gradient share browser coordinates. Preview now includes intensity blending, light/dark handling and matching noise construction; exact Chromium/native surface-color agreement still needs visual validation. |
| Appearance controls | Pearl and Sand presets, profile/scope explanation, scrollable settings, native hosts following the browser's appearance, and a macOS-version-aware iCloud Passwords setup entry. Existing density/tile settings are retained. |
| Chat | Detect showing **or loading** entries, cancel a pending load on toggle before it becomes visible, track extension action launch without dispatching it twice, cancel eventual presentation if the user closes during action startup, and update labels after coordinator visibility transactions. A one-shot launch timeout prevents permanent pending state. |
| ChatGPT per profile | Existing official Store download defaults and profile-scoped provider are preserved. No duplicate component-extension installer or forced reinstallation after opt-out. |
| iCloud Passwords | Optional setup opens Apple's official extension listing on supported macOS. Existing Chrome native-messaging manifest discovery is preserved. Actual Apple helper authorization/filling compatibility has **not** been validated; the setup entry is not proof of working credential support. |
| Warn before quit | Already enabled by the inherited macOS `kConfirmToQuitEnabled` default and available in the native menu; no duplicate implementation. |

These are source implementations, not observations of a newly compiled browser. Fine visual tuning, accessibility and runtime acceptance checks remain necessary. Large features explicitly deferred by the research—Spaces, automatic archive, Peek, Little Arc, AI renaming and service previews—are not part of this refinement patch. Optional advanced gradient/texture editors and site-search mode also remain follow-up work rather than claimed implementations.

## Validation

- Swift native UI parsed and type-checked; Objective-C header generated for bridge checks. Existing macOS 14 deprecation warnings remain because the app supports macOS 13. No object build, preview app or browser compilation ran locally.
- C++/Objective-C++ syntax checks passed for the palette, native bridge, Chat button, side-panel coordinator, toolbar, frame layout, sidebar region, themed background, generic bubble anchor and BrowserView. The address/Home browser regression test file also passed syntax checking using adjacent browser-test target flags. New last-tab and Home visibility method bodies were separately checked against actual Chromium headers.
- Complete syntax checks of some large translation units/tests were blocked by missing generated headers in the local prepared tree (including browser buildflags, Read Anything/Lens Mojo headers and the generated side-panel extension API header). These are not passing full compile results.
- Added browser regression cases for address replacement, Home-slot reuse, last-tab fallback, Home visibility without a preference change, and cancelling a pending side-panel entry. These cases are **not executed yet**; do not substitute retained old test binaries for them.
- Existing lightweight safeguards passed: 8 checkpoint tests, 8 cached-test policy tests, 13 build-budget tests, 6 completion tests and 8 fresh-test-gate tests (43 total). Shell syntax checks passed for packaging/build scripts. Outer patch lint and actionlint passed. Unified-diff blank context markers are checked by the patch linter rather than treated as source trailing whitespace. The final outer patch replayed with zero fuzz against saved pre-edit files and reproduced the prepared sources.

## GitHub build baseline and gate

The latest completed browser run inspected was [42156459305](https://github.com/manavo-o/helium-macos/actions/runs/42156459305), at `8f0097e9e90fdb2a32d0336b88f519aff27b64c3`. Its artifacts include installable DMG `13510227838` and build checkpoint `13511187126` (checkpoint ZIP SHA-256 `fd5474ae6308b44065d92894c2b27343a00d1e76e3943fac1e15a6db9c6660b2`). This is the prior Helium Sidebar build, not a Xenon artifact.

The user subsequently requested tests followed by a build. Linux [audit 42258633447](https://github.com/manavo-o/helium-macos/actions/runs/42258633447) verified the checkpoint archive digest and all 25 source preimages. The manifest now records the appended feature delta and its exact preimages. The `xenon-native-v1` validation plan compiles and runs fresh browser/routing/bubble regressions within the existing phase budget before allowing browser/installer compilation. Retained link-only tests do not stand in for this validation. See `arc-build-recovery.md` for the gate and continuation policy.

## Runtime acceptance still required

Use a disposable profile on the GitHub-built Xenon artifact. Verify address click/Cmd+L/current-tab replacement, Cmd+T/no allocation on cancellation, raw Command+Enter, original-target closure, popup resizing and window teardown. Check Home → destination → final close with docked and hidden sidebar preferences, plus explicit Close Window, private windows, splits and multiple windows. Compare actual padding, grain, contrast and preview against the supplied Arc screenshots at measured point bounds.

Verify Chat open/loaded-close/loading-close/direct-close/reopen and label state, then two fresh profiles' official ChatGPT downloads and opt-out persistence. iCloud Passwords must be tested through Apple's normal user-completed authorization with a disposable credential; passkeys and private-window support need separate checks. Do not claim the full task is runtime-validated until these checks and compilation/packaging have completed.
