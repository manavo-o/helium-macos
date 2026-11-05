# Arc-style Helium source provenance

This branch starts from `manavo-o/helium-macos` commit
`dadfa05e3ed69b3de1f96066bd23c1bd15a6ee66` (the successful Xcode 27.1
arm64 workflow run 41498043072). Its Helium submodule is pinned to
`imputnet/helium` commit `2f81b9cafa38a95071e20de3f9cd6b0aca6d3c65`.

| Source | Revision | License and intended use |
| --- | --- | --- |
| Helium | `2f81b9cafa38a95071e20de3f9cd6b0aca6d3c65` | GPL-3.0; vertical tabs and split-view patch foundations. Chromium and imported ungoogled Chromium portions retain their own licenses as described by Helium. |
| [Biba](https://github.com/weristvlad/biba-browser) | `4cad41cd388945fa532838d3daf543bb4fb2bb40` | GPL-3.0; reference for pinned tiles, sidebar presentation, drag-to-pin, and command-bar UI. No Spaces, Biba branding, assets, updater, or product identity are to be imported. |
| Helium PR #2367 | `ffb1e05af047f48c385cbcbf0fe7521d02158e2b` | Helium contributor patch under the repository's GPL-3.0 terms; reference for relocating the actual toolbar views into the sidebar. Closed, unmerged, and tested by its author on Linux only, so macOS adaptation and testing are required. |
| Helium PR #2747 | `c0ba3d247c01e5f77ccd726247275153d2f1be32` | Helium contributor patch under the repository's GPL-3.0 terms; reference for interface size constants. Open and unmerged at the time of pinning. |

The Biba command-bar patch is not directly portable: it creates a tab before
showing the palette and references Biba's Spaces controller. Any adapted code
must remove those dependencies and defer tab creation until navigation is
submitted. Record exact files and modifications here as the port proceeds.

The official ChatGPT extension observed in this Mac's existing Helium profile
is version `1.26.1020.11845`, ID
`hehggadaopoacecdllhhajmbjkdcmajg`. Its installed manifest declares an
`action` and a `side_panel` with `default_path: side-panel-loading.html`.
This ID also matches the OpenAI-published Chrome Web Store listing. The
custom browser must verify the action dispatch and panel behavior in its own
profile before wiring the dedicated button.

The separately installed official ChatGPT search extension is version `1.11`,
ID `ejcfepkfckglbgocfkanmcdngdijcgld`. Its manifest declares the search
provider URL `https://chatgpt.com/?q={searchTerms}&hints=search&ref=ext`.
OpenAI's search documentation says the extension starts a ChatGPT conversation
from the address bar. Direct navigation to that URL in the existing Helium
profile submitted a harmless test question and produced a conversation; it
did not invoke the extension's address-bar keyword. The custom build still
needs signed-out and encoding verification before release.


## Adapted native implementation

`arc-native-sidebar.patch` adapts the real-view reparenting approach from
PR #2367 without importing its entire patch or moving extension access out of
the toolbar. Biba's pinned-grid sizing and pinned-tab presentation inform
`PinnedTabContainerView`/`TabView` changes; Spaces and branding are excluded.
PR #2747 informs local interface-density preferences and layout constants;
pinned-tile sizing is independent. All donor revisions above remain pinned.

`arc-local-omnibox.patch` uses Chromium's existing local bookmark, history,
shortcuts and built-in providers; search/zero-suggest/extension providers are
excluded. `arc-chat-button.patch` uses the extension toolbar view model and
existing side-panel host. `arc-default-chat-extension.patch` uses Chromium's
first-run external-extension loader with the official Web Store update URL,
preserving ordinary acknowledgement and user opt-out. No extension CRX is
redistributed. `arc-app-identity.patch` separates the app, profile and keychain.
`arc-visual-theme.patch` implements the supplied Arc visual references using
native controls; see [visual design](arc-visual-design.md).

No third-party runtime dependency is introduced by these adaptations. Imported
Chromium files retain BSD notices; original Helium additions carry GPL headers.
Runtime extension authentication, private permission and panel conversation
continuity still require checking in the separately identified app.


`arc-split-drop.patch` keeps native swap/separate/resize/session machinery,
adds outer-quarter horizontal previews, and uses `UpdateTabInSplit(kSwap)` to
retain the displaced tab. `arc-drag-pinning.patch` selectively adapts Biba's
sidebar drag region and post-drag pin conversion, using native orientation
rather than class-name strings, handling unpinning and cancellation, and
excluding all Spaces dependencies. `arc-release-identity.patch` removes the
inherited upstream Apple team; signed builds must set their own public
`ARC_MACOS_TEAM_ID` and signing/notarization secrets.


`arc-sidebar-focus.patch` reveals the real omnibox before Cmd+L focus and holds
the sidebar open for keyboard focus and anchored permission/security bubbles.
`arc-native-url-classification.patch` uses native, local omnibox parsing to
recognize explicit URLs before question routing, including URL query spaces.
No suggestion provider is started by that parsing step.
