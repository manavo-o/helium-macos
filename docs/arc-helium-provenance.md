# Arc-style Helium source provenance

This branch starts from `manavo-o/helium-macos` commit
`dadfa05e3ed69b3de1f96066bd23c1bd15a6ee66` (the successful Xcode 27.1
arm64 workflow run 41498043072). Its Helium submodule is pinned to
`imputnet/helium` commit `2f81b9cafa38a95071e20de3f9cd6b0aca6d3c65`.

| Source | Revision | License and intended use |
| --- | --- | --- |
| Helium | `2f81b9cafa38a95071e20de3f9cd6b0aca6d3c65` | GPL-3.0; vertical tabs and split-view patch foundations. Chromium and imported ungoogled Chromium portions retain their own licenses as described by Helium. |
| Biba | `4cad41cd388945fa532838d3daf543bb4fb2bb40` | GPL-3.0; reference for pinned tiles, sidebar presentation, drag-to-pin, and command-bar UI. No Spaces, Biba branding, assets, updater, or product identity are to be imported. |
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
from the address bar. Whether navigating directly to that URL submits or only
prefills must still be tested in the custom build, including signed-out use.
