# Native sidebar visual design

Reference: user screenshots supplied November 4, 2026, showing mint and coral
Arc themes, a floating dark command bar, docked sidebar, and a revealed floating
sidebar. Product behavior references checked November 4:

- https://start.arc.net/find-focus — sidebar toggle and focus mode.
- https://start.arc.net/command-bar-actions — tab switching and command actions.
- https://start.arc.net/release-notes — theme color extending to command bars.

## Implementation

The existing Chromium theme color provider supplies the frame and sidebar.
The home page uses the active frame color and remains quiet, with pinned sites
in the sidebar. Custom new-tab background images remain supported. Webpage
colors are controlled by the website. Content uses a 6-point frame inset and
10-point native corner radii. Sidebar header padding is 10 points vertically
and 8 points horizontally; pinned tiles have their independent size preference.

The native floating palette has an 820-point maximum width, 16-point corners,
a 58-point input row, 48-point result rows, search/action icons, an accent-colored
selection, and a native drop shadow. Its surface mixes the frame color with a
light or dark neutral veil to preserve contrast. Its row count shrinks to fit
shorter windows. It uses native system fonts and controls.

Helium's existing zen-mode controller provides the docked/hidden/revealed
sidebar. The sidebar and compact top toolbar start pinned. The toolbar's
sidebar button toggles docking; the existing Command-S shortcut also works.
The Chat control remains at the trailing edge of the compact top toolbar,
with rounded corners and padding, outside webpage content and the sidebar.

No package or runtime dependency was added for this styling. Existing native
Views, theme colors, vector icons, layout, and zen-mode controllers are reused.
The pinned Chromium/Helium/toolchain revisions are intentionally retained for
build reproducibility; this does not claim all upstream dependencies were
updated to their latest versions. Check current supported releases before any
future dependency addition and pin the chosen version with provenance.

## Validation

C++ syntax checks use the actual generated Chromium compiler command. GN header
dependency checks cover the palette and toolbar targets. Browser integration
coverage checks sidebar hide/restore while leaving top chrome pinned. Runtime
visual checks remain required for mint/coral and custom themes in light/dark
mode, docked/hover-revealed states, narrow windows, fullscreen, VoiceOver,
permission bubbles, and extension panel activation. Do not describe screenshots
of a mockup as validation of the compiled application.
