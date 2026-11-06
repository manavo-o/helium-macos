# Arc comparison and additions for Helium

Implementation follow-up: the user authorized code changes on November 6. See [Xenon implementation status](xenon-implementation.md) for the source changes and outstanding compilation/runtime gates. Statements below about the inspected build remain historical evidence, not validation of the new patch.

Research date: November 5, 2026. Checkout: `arc-helium`, HEAD `3bd423d99d0c78b82828aac44167d0c521021645`.

## Recommended direction

Use one centered command surface with two explicit entry modes: **edit this tab** from the address display/Cmd+L, and **new destination** from Cmd+T/New Tab. Keep a compact, readable origin display while browsing, with access to site security and permissions. The existing native palette is a useful foundation, but its current navigation disposition always creates a foreground tab. It cannot simply replace Cmd+L unchanged.

The best small additions are pointer hover selection, match highlighting, and better discovery of existing browser actions. Preserve the work already present for suggestions, appearance, pinning, split views, and Chat; validate it in the integrated browser before adding more systems. Spaces, automatic archiving, Peek and Little Arc have substantially wider state and recovery requirements.

This is a research deliverable. No application source, patches, dependencies, build configuration or builds were changed. Browser runtime parity remains unverified.

## Evidence and limits

Live inspection used Arc's native accessibility tree and three targeted screenshots. It covered the command surface, native preferences categories, Chromium settings for search/privacy/performance, and the View menu. Synthetic text was typed and cancelled; no test search or destination was submitted. Existing public favorite content was activated to inspect address editing. Private history, account addresses and profile names are omitted here.

Arc's internal settings page reports **156.0.8078.74 (Official Build), arm64**. This is the value displayed by its Chromium settings page; the native Arc marketing version was not separately established. An update notice was visible; it was not activated. Native settings were opened without changing values. More Settings opened a settings tab as part of inspection.

Confidence: **observed** means visible in this installation; **source** means present in Helium's prepared tree and/or tracked outer patches; **proposal** means a recommendation. Settings visibility establishes available controls, not every downstream behavior. No exhaustive audit of every nested Chromium setting, all 100 shortcut rows, theme editor, recovery menu or profile was completed. Narrow windows, fullscreen, split-pane focus and hidden-sidebar placement still need a controlled follow-up. No benchmark or local compilation was run.

## Centered interaction model

| Entry/state | Observation | Implication for Helium |
| --- | --- | --- |
| Reading a page | Toolbar displayed a compact host, navigation controls, site control and split-view control. Address was text rather than an always-editable URL field. | Keep identity/security visible; make the compact display an entry into editing. |
| Click address | Opened command-bar text field containing the complete URL, with all URL text selected. | Seed edit mode from the active tab, including scheme/path/query. |
| Cmd+L | After dismissal, reopened the same URL-filled state with full selection. | Share editing behavior with address click. |
| Cmd+T | Opened the same command surface empty over the current page; existing page remained behind it. | New mode must preserve the underlying page until acceptance. |
| Empty results | Several favorite/open destinations with “Switch to Tab”, plus a support command. | Existing-tab switching belongs in the shared surface. |
| Escape | Removed the surface and left the underlying page in place. | Cancellation should preserve tab count, URL and focus. |
| URL completion | A host prefix produced a completed host with only the suffix selected. | Preserve the original input separately from displayed completion. |
| Arrow down | Moved selection to the raw search row and restored the original typed prefix in the field. | Selection presentation must not overwrite raw input. |

Submission semantics were deliberately not exercised against the user's existing tabs. Current-tab replacement for address editing is a **Helium proposal consistent with the observed editing context**, not a measured Arc Enter outcome. Sidebar New Tab equivalence, repeated-open behavior and click-outside cancellation were not independently retested in this pass.

The screenshot shows the palette horizontally centered on the **whole window**, including the sidebar: approximately x=746–2278 in a 3024-pixel image. The content area starts near x=456. This differs from Helium's current content-area centering and one-third vertical placement. The palette's top remained near y=512 when result count changed, so calling it vertically centered would be misleading. The width is about 1532 image pixels. Approximately 766 points is plausible at 2× scale, but display scale was not independently measured; all screenshot coordinates here are pixels. Use a later point-based window measurement before setting exact geometry.

## Settings inventory

Scope is shown only where the UI makes it clear; remaining scope requires confirmation. “Reuse” below means inspect and expose the existing Chromium facility before designing a replacement.

| Location/control | Visible state | Purpose, scope and Helium relationship |
| --- | --- | --- |
| Account: default browser | Arc not default | App registration; expose existing default-browser path. |
| Account: Sync Sidebar | Off; encryption description and Recovery Card entry | Durable cross-device state; defer a new sync system. Recovery was not opened. |
| General: Warn before quitting | On | Prevent accidental session closure; candidate small preference after checking inherited behavior. |
| General: first switch | AX label “Info”, off | Insufficient label; do not infer its function. |
| General: Previews Settings | Sheet with individual choices | Folder, Google Calendar and Gmail enabled; Outlook mail/calendar, recent Linear/Notion/Figma pages and Notion Calendar disabled. Service previews introduce auth/data dependencies; defer. |
| Profiles | UI describes history/logins/cookies/extensions separation, one profile usable by multiple Spaces | Chromium profiles already provide isolation; Arc-style Space mapping is a separate feature. Do not imply it exists in this fork. |
| Profiles: default search engine | Google | Profile-related search preference; existing provider should remain authoritative. |
| Profiles: Include search engine suggestions | On | Profile-level discoverability in Arc; Helium already has an online-suggestions preference and policy/private checks in source. |
| Profiles: Archive tabs after | 12 hours (default) | Tab lifecycle, distinct from memory discarding. Missing Arc-style lifecycle was not established in source; defer until restoration rules exist. |
| Profiles: default document app / download location | Unset / Downloads | Convenience routing and storage; reuse existing downloads settings first. |
| Profiles: data controls | Privacy/security, passwords, cards, notifications, autofill, clear browsing data | Deep links to existing browser facilities are easier than new native implementations. Sensitive subpages were not explored. |
| Max: feature set | Enabled; automatic future features off | Separate opt-ins are valuable. Automatic enrollment is unnecessary for Helium. |
| Max: organize Today tabs, instant top-result search, link summaries, tidy pinned titles, rename downloads, ChatGPT suggestions | All shown enabled | AI partners receive data per visible disclosure. These are separate features; user-approved question routing does not authorize automatic content uploads for summaries/renaming. |
| Links: Little Arc | Global shortcut, modifier-link opening and external-app links on; archive after six hours | Auxiliary windows and external-link lifecycle; larger work. |
| Links: Peek | Shift-click on; external destinations from favorites/pins on | Transient navigation preserves pinned context; requires separate navigation/focus/recovery design. |
| Links: Air Traffic Control | Entry present | Routing configuration available; its rules were not inspected. Defer profile-routing proposals. |
| Shortcuts | Searchable list reports 100 actions; custom action shortcuts and website-vs-browser priority described | Search and command discovery useful. A full shortcut editor/conflict policy is medium work. |
| Icon | Original selected; several alternate icons visible | Cosmetic, low priority; no user workflow benefit comparable to navigation fixes. |
| Advanced: sounds / reorder haptics | Both on | Optional feedback; defer sounds, consider haptics only after drag behavior is stable. |
| Advanced: restore previous windows | Off | Session policy; check inherited startup/recovery controls before adding. |
| Advanced: drag window from webpage top | On | Native window interaction; requires hit-testing and selection checks. |
| Advanced: full URL with toolbar | Off | Confirms compact address display is intentional in this configuration. Full URL remains necessary when editing/copying and for security inspection. |
| Advanced: quote URL switch | On, label exposed as explanatory text | Visible shortcut for copying URL as quote; exact main label not reliably exposed. |
| Advanced: PiP on leaving video tab | On | Existing media infrastructure may help, but automatic lifecycle behavior is medium work and unverified in Helium. |
| Advanced: website theme data / Boosts | Both on | Distinct privacy/site-customization choices; not recommended additions now. |
| Advanced: More Settings / translation prompts / Export Data | Entries present | Native preferences link into Chromium settings. Export and reset were not invoked. |
| More Settings: Search engine | Google; manage engines/site search entry | Reuse site-search facility; no replacement engine registry needed. |
| More Settings: Privacy | Cookies allowed; Security and Site Settings entries | Preserve Chromium permission/security controls. No new privacy UI needed merely for Arc parity. |
| More Settings: Performance | Alerts on, inactive-tab appearance on, Memory Saver off; Energy Saver on at ≤20% battery; no always-active sites listed | Surface existing controls. Archiving and memory saving must remain conceptually separate. |
| More Settings: other categories | Autofill, AI innovations, appearance, default browser, languages, downloads, accessibility, system, reset, extensions | Categories observed, nested settings not inventoried. |
| View menu | Hide Sidebar, Hide Toolbar, Add Split View, fullscreen and appearance modes available | Current toolbar and sidebar visible. Split controls are already partly implemented in Helium. No settings were toggled. |

## Ranking and autofill experiment log

| Case | Observed results/input | Confidence/limit |
| --- | --- | --- |
| Empty Cmd+T | Open/favorite switch rows before support command | Observed in one profile; not a universal ranking rule. |
| `example.com` | Selected navigation row; separate raw search row; engine completions below | Screenshot distinguishes globe vs magnifier. No navigation submitted. |
| `new win` | “New Window ⌘N” selected; raw search below | Command priority observed. Some previous-query suggestion text remained in the immediate snapshot. |
| `yout` | Host completed to `youtube.com`; suffix `ube.com` selected; navigation/history rows and site-search affordance | Observed; private history row titles intentionally omitted. Active favorite did not show “Switch to Tab” in this case. |
| Down after host completion | Raw search selected; field returned to `yout` | Observed original text recovery. |
| Fast query replacement | Some earlier-query suggestions visible in immediate snapshots | Could be asynchronous arrival, retained rows or snapshot timing. Do not infer Arc cache design or copy this behavior. |
| Cmd+L vs address click | Full current URL selected in both | Observed opening state only. |
| Paths, punctuation, non-ASCII, title-vs-host conflict, duplicate sources, cross-profile scope, older-vs-recent ranking | Not controlled in this pass | Requires later tests; no invented weights or indexing conclusions. |

Arc's private index, weights and cache cannot be determined from this evidence. Helium already reuses Chromium autocomplete providers and a local tab scan; a second database is not justified. Preserve explicit keyboard selection across delayed results and reject responses for obsolete queries. These are product acceptance requirements, not claims about Arc internals.

## Feature matrix and focused additions

All source-present items below still need integrated-browser validation. Complexity is relative to this checkout, not a delivery estimate.

| Priority/addition | Current Helium status | Smallest useful scope, integration and acceptance |
| --- | --- | --- |
| P0: shared address editing | Partial: native new-destination palette; real omnibox for browsing-page Cmd+L; palette navigation always NEW_FOREGROUND_TAB | Medium. Explicit edit/new context across native bridge and Chromium navigation. Address click/Cmd+L selects full current URL; acceptance updates the original tab; Cmd+T creates one tab only on acceptance; Escape creates none. Handle underlying tab closure safely. Local state only; no new background work. |
| P0: palette placement | Partial: centers on content, vertical offset one third | Small-to-medium correction after point measurement. Specify whole-window horizontal anchor and fixed top region; clamp to available bounds; verify hidden sidebar, narrow window and split views. No polling or layout animation loop. |
| P1 easy: hover selection | No onHover handler in native result rows inspected | Small. Update selection on intentional pointer movement without overriding keyboard selection due to a stationary pointer. Enter and click activate the visibly selected row. No network or persistent state. |
| P1 easy: match emphasis | Native titles/details rendered as plain Text | Small-to-medium. Highlight matched spans in title/host while preserving quiet hierarchy and accessibility reading. No text reflow; long URLs truncate safely. Requires match metadata, not a new index. |
| P1 easy: expose existing actions | Ten palette commands already present, including history/downloads/reopen/settings | Small for additional supported command IDs and search aliases. Add useful existing split/sidebar/appearance/copy-URL actions only where enabled and supported. Command state must reflect active tab; existing commands should not be presented as new features. Official Arc action list supports the discoverability benefit. |
| P1 easy: direct settings links | Appearance editor exists; inherited browser settings available | Small. Provide clear paths to search/site search, downloads, permissions and performance using existing pages. Every link opens the expected profile-scoped setting without changing it. No duplicate settings storage. |
| P1 candidate: warn before quit | Arc on; Helium parity not established | Verify inherited preference first. Small only if existing machinery can be exposed; cancellation must retain every window/tab. No modal warning on ordinary tab close. |
| P1 validation: search and appearance | Source present | Validate debounce/cancellation/private exclusions, raw Command+Enter, gradients/density/pin size. Network requests only for approved engine suggestions; private windows excluded. Chat toggle has a separate unresolved priority gap below. |
| P1 validation: pins and splits | Source present in drag-pinning/split-drop patches | Confirm cancellation, unpinning, displaced tab retention, split resize/swap/session restoration. Adding folders before this is reliable expands state risk. |
| P2: Tab to site search | Arc showed Search YouTube, Tab; Helium palette parity not established | Medium: bridge existing TemplateURLService keyword search into native input state. Tab enters explicit site mode; Shift+Tab/Escape exit predictably; user can recover raw text. Requests go only to chosen provider. |
| P2: pin destination management/folders | Pinning exists; Arc destination-reset/folder parity unverified | Medium-to-large; first define saved destination vs current location, undo and session persistence. Avoid claiming folders are absent without a fuller source audit. |
| Defer: Spaces, auto-archive, Peek, Little Arc | Not established as implemented Arc-equivalent systems | Large: navigation/session/profile isolation, restore and window lifecycle. Archive requires recoverable history and exclusions for pinned/audible/active work; no periodic heavy indexing. |
| Omit for now: AI renaming, service previews, Boosts, extra icon gallery | Separate from current navigation goal | Privacy, authentication, support or customization cost exceeds the immediate benefit. Do not add these just because Arc exposes them. |

## Source map

Prepared files inspected: `build/src/chrome/browser/ui/views/tabs/vertical/arc_command_bar_view.cc` (commands, results, navigation and geometry), `arc_native_ui.swift` (input, rows and accessibility), `chrome/browser/ui/views/frame/browser_view.cc` (focus entry points). Prepared files are inspection aids, not the tracked delivery source.

Tracked delivery map: `patches/series`; `arc-navigation-polish.patch` for native command UI/navigation/appearance, `arc-native-state-polish.patch` for presentation state, `arc-host-prefix-completion.patch` for completion, `arc-sidebar-focus.patch` for real omnibox focus, `arc-split-drop.patch` and `arc-drag-pinning.patch` for existing split/pin work. See `docs/arc-helium-provenance.md` for origins. Earlier `docs/arc-ui-analysis.md` remains historical and does not override the centered interaction findings.

## Styling and grain: deeper inspection

Follow-up inspection on November 5 opened **Spaces → Edit Theme…**, inspected its native accessibility tree and screenshot, then dismissed it with Escape. No colors, sliders, presets or texture choices were changed. This establishes the available editor and current appearance; it does not establish the effect of every texture mode. The earlier limitation about the theme editor is superseded by this section.

### What Arc actually exposes

| Element | Evidence | Interpretation and limits |
| --- | --- | --- |
| Theme entry point | Edit Theme under Spaces; popover opens inside the browser window | The editor is associated with a Space. How its values persist or propagate to other windows was not tested. Helium currently reads its theme from profile preferences. |
| Mode controls | Three top buttons visually represented by sparkle, sun and moon; first appears selected | Likely automatic/light/dark choices, but accessibility labels are absent. Treat exact mode semantics as unconfirmed. |
| Color workspace | Large dotted editing area with a ringed color handle; Add and Remove controls below | Supports editing color composition. The screenshot shows one handle. Maximum colors, handle positioning semantics and gradient interpolation were not tested. The workspace's regular dot grid is an editor guide, distinct from the frame's irregular grain. |
| Presets | Paged circular swatches; AX exposes Brand, Pastel, Drab and Greyscale families | Broader palette than Helium's four presets. Internal asset labels do not disclose actual color values or rendering code. No preset was selected. |
| Color intensity | Horizontal slider; AX help explicitly says Intensity | Independent control is present, but exact numeric value, range and transfer function are not exposed in this snapshot. Do not equate its position to a known saturation or opacity percentage. |
| Noise texture | AX label explicitly says “Cycle noise texture” | Confirms selectable texture variation rather than only a grain on/off switch. Number and character of variants remain untested. |
| Texture-area control | Circular noisy swatch with surrounding dots and a radial white marker; second AX slider has no useful label | A separate adjustable control is visible beside the intensity slider. Whether it adjusts amount, scale or another parameter cannot be established without changing it. Do not label it definitively as grain opacity. |

### Visible styling layers

Arc's frame in the current configuration is pale lavender/gray with fine irregular luminance variation. The grain is easiest to see in the wide sidebar's empty regions and the outer window gutter. It reads as a continuous material rather than isolated evenly spaced dots. The result combines a broad, slowly varying color field with fine texture; texture alone would not reproduce the appearance. The screenshot cannot identify whether that texture comes from a bitmap, shader, generated noise, material compositing or multiple layers.

The browser's surfaces have distinct roles:

| Surface | Direct visual observation | Consequence for Helium styling |
| --- | --- | --- |
| Outer frame/sidebar | Continuous pale textured region, rounded window boundary; little hard separation around the sidebar | Share a consistent coordinate space for color and grain. Avoid restarting a visible pattern at each child view. |
| Web content | Dark settings page sits in an inset rounded rectangle with a soft shadow; its own flat backgrounds remain distinguishable | Keep chrome texture out of website pixels. The page's dark theme and browser-frame color are separate choices. |
| Favorites | Large rounded translucent tiles with centered icons; tile boundaries are quiet | Use a restrained veil over the common material, with icon clarity stronger than tile decoration. |
| Selected sidebar tab | Rounded lighter fill, aligned icon and single-line title | Selection is an additional state layer. It should not require regenerating the underlying texture. |
| Toolbar | Dark strip belonging visually to the content rectangle in this configuration; compact centered URL and faint lower divider | Do not assume every browser surface shares the sidebar's pale color or the same texture strength. |
| Theme popover | Dark translucent rounded panel with a broad shadow; the underlying blue page selection appears as a blurred band through it | Backdrop influence is observable. Native blur is a suitable Helium mechanism, but this does not prove Arc's framework or exact blur recipe. |
| Command surface | Previously observed dark panel, thin edge, soft shadow, restrained separator, one-line rows and quiet unselected actions | Preserve strong text contrast and selected-row hierarchy. Carrying dense frame grain into result text would reduce clarity. |

The theme popover itself spans roughly x=482–1196 and y=416–1434 in the 3024×1700 screenshot: about 714×1018 image pixels. These are screenshot measurements, not confirmed macOS points. Corner radii, shadows and exact spacing should be measured in points later. Current screenshots are adequate to describe hierarchy and texture character, not establish production design tokens or exact color values.

The observed pale frame uses white/light labels, which can look subdued against it, while the dark content and popover have clearer text contrast. Reproducing the appearance should include explicit contrast checks for sidebar titles, disabled icons and selection states. Do not copy a low-contrast combination simply because it appears in Arc's current theme. Active/inactive window appearance is another unresolved variable in earlier screenshots; muted chrome must not automatically be attributed to theme intensity.

### How our current styling works in source

This section describes **Helium**, not Arc internals. `themed_background.cc` reads up to three hexadecimal theme colors and mixes each into the system surface. Intensity is clamped to 10–100 and converted to an alpha using different light/dark factors. Multiple colors form a diagonal linear gradient spanning browser-view bounds; the view-origin conversion keeps that gradient aligned across child surfaces. A single color produces a flat field.

When grain is enabled, the current painter draws 1×1 rectangles in an approximately 8-unit grid, with a small row offset, using constant gray at alpha 9/255. It is deterministic, sparse and has no animation timer. This is a subtle patterned stipple. It does not reproduce the dense, irregular visual character observed in Arc. Its coordinates also start at each view's local origin, unlike the globally aligned gradient; adjoining surfaces can therefore restart the stipple phase. A screenshot of the actual Helium build is still needed to determine whether that discontinuity is visible.

The native appearance editor currently offers four presets, one to three color stops, intensity, system/light/dark and a Boolean grain toggle. Its preview draws the raw selected colors as a linear gradient and overlays a mock content rectangle. It does **not** show the frame's intensity-to-system-surface blending or its grain painter. The preview therefore cannot currently be trusted as a faithful material preview. The native command surface separately uses a translucent surface tint and respects reduced transparency; grain painted into Chromium chrome does not automatically become grain in that native panel.

### Styling additions and corrections worth doing

| Priority | Proposal | Size/dependency | Acceptance criterion |
| --- | --- | --- | --- |
| P1, easiest useful correction | Make the appearance preview represent the actual intensity, appearance mode and grain | Small-to-medium; share a visual specification between native preview and frame painter | At representative mint, coral and neutral settings, preview and browser chrome have the same material character and relative brightness. Verify in light and dark. |
| P1 | Replace the regular stipple with subtle irregular static grain | Medium; a small cached texture or equivalent native rendering is a Helium proposal, not a discovered Arc technique | No obvious grid, repeated stripes or seams at normal and Retina scale; texture does not obscure labels; identical settings stay visually stable while typing and scrolling. |
| P1 | Align grain to the same window coordinate system as the gradient | Small if retaining the current painter; verify actual view composition | No phase discontinuity where sidebar, top frame and gutters meet; resizing does not make the texture crawl. |
| P1 | Define surface roles and contrast together | Small-to-medium; theme palette/state handling | Sidebar, content frame, toolbar, popover and selection remain distinguishable in pale and dark themes, active/inactive windows and increased contrast. Websites retain their own painting. |
| P2 | Offer a small number of texture variants or a strength setting | Medium; depends on the new material and accurate preview | Each choice has a clear label and visible purpose; setting zero removes texture; defaults remain quiet. Arc's cycling control is evidence of variation, not a requirement to copy its unlabeled dial. |
| P2 | Add a few curated neutral/pastel presets | Small after material correction | Every preset passes the same contrast and state checks. Reuse existing color storage; avoid a large palette gallery before material quality is right. |
| Defer | Free-position color handles or a complex gradient workspace | Larger editor and persistence change; benefit not established by current observation | Only add after a controlled Arc experiment demonstrates a useful result the current three-stop gradient cannot achieve. |

For energy use, prefer a static material cached by scale/theme/texture parameters, invalidated only when those inputs change. Avoid generating fresh randomness per paint, continuous animation or per-pixel work on every pointer event. This is an implementation recommendation for later work. No rendering changes or performance measurements were made in this research task.

A later disposable-profile experiment should compare each Arc texture option, the unlabeled radial control, intensity extremes and mode changes against a fixed background. That would distinguish hue/intensity effects, texture amount/scale and backdrop influence. The read-only pass deliberately leaves those effects unresolved. Official documentation searches did not provide a primary technical description of Arc's grain algorithm; no internal blend mode, noise distribution, asset resolution or framework is claimed here.

## Compiled Helium Sidebar inspection — November 6, 2026

Inspected the running **Helium Sidebar**, bundle ID `io.github.manavo.helium-sidebar`, using `/Applications/Helium Sidebar.app`, version **0.20.3.1**. Ordinary Helium is a separate running app and was not used for this comparison. A second Sidebar copy is mounted at `/Volumes/Helium Sidebar/Helium Sidebar.app`; both report the same version. A new Sidebar ZIP is present in Downloads dated November 6. The running app was not cryptographically matched to that ZIP or a CI commit, so these findings describe the installed running build, not a proven exact build revision.

The existing profile initially contained one New Tab. Inspection opened the native palette and appearance window, examined the tab context menu, created one disposable public Example Domain tab, checked Cmd+L and Chat, then closed that disposable tab and the Chat panel. No theme, spacing, pins, extensions or profile settings were changed. Arc comparisons refer to the November 5 observations above; Arc was not relaunched during this pass. No local build or heavy profiling was performed.

### Concrete amendments

| Priority | Difference visible in the compiled app | Proposed amendment and acceptance |
| --- | --- | --- |
| P0 | Browsing pages show a long editable Chromium address field across the top. Cmd+L selects that field; it does not open the native floating surface. | Implement the shared current-tab edit mode described above. Keep a compact clickable address display and site-security access. Cmd+L/address click must use the same native editor; submitting must replace the original tab. This gap is now runtime-confirmed. |
| P1 | Navigation, address, extensions, profile, menu and an outlined labeled Chat button occupy a toolbar across the entire window, including above the sidebar. Arc's observed content toolbar begins after the sidebar and leaves its sidebar header visually separate. | Define sidebar-header and content-toolbar ownership. Align content navigation with the content frame; keep sidebar toggle accessible. Verify draggable window regions, traffic lights and keyboard access before moving controls. Medium work, not a simple spacing tweak. |
| P1 | The starting New Tab is a real tab, with a close affordance, while a separate “+ New Tab” action sits below the tab list. The content shows Chromium shortcut tiles. Arc's observed Home/New Tab presentation was quieter. | Decide whether Home is a durable tab or an empty-window state. Avoid two visually similar New Tab entries in the initial state. Cmd+T should keep its current deferred allocation behavior. Removing a pre-existing Home tab automatically needs explicit session rules; it should not be inferred from this screenshot. |
| P1, small | The sidebar begins immediately with ordinary tabs; no visible section heading or compact organizational header appears in this empty profile. Arc has a favorites region, Space heading/context control and a separate tab region. | Add a restrained header or section affordance appropriate to Helium's actual model. Expose appearance/organization near the sidebar without adding a nonfunctional Space picker. Do not infer that pinning is absent: the context menu already exposes Pin. |
| P1, small | Appearance is available through the palette, but no dedicated appearance entry is visible in the sidebar. | Add a discoverable sidebar context/header action for the existing native editor. Opening it should not allocate a tab. No new settings engine is needed. |
| P1 | The sidebar/background shows a faint regular pattern; it lacks Arc's dense irregular material character. Selected tabs use a broad blue-gray rounded fill. | Apply the grain and preview corrections above, then tune selection as a separate overlay. Require continuous material across adjoining chrome and readable selected/unselected labels. Compare equivalent themes; Arc's pale theme versus this graphite theme is not a valid color-match test. |
| P1, small | The current appearance preference is **Compact**, with 48 pt pinned tiles, System appearance, intensity 67 and grain enabled. This differs from the comfortable default described in the handoff. | Treat current density as profile state, not proof that the default failed. Compare both densities later. Align row padding, icon baseline and close hit target with the chosen density; do not merely inflate every control. |
| P1 | The native palette opens successfully and shows five visible result rows. With no query in the initial profile, Edit appearance is selected above New Window and other commands. Arc's observed empty state prioritized existing destinations. | Define empty-state priorities deliberately. Use existing tabs/recent destinations when useful, with commands lower; retain an accessible appearance action. No-history profiles need a sensible fallback. Do not duplicate commands already present. |
| P1 | Palette is centered over the content region and sits in its upper portion; its material is visibly flatter gray than Arc's observed dark surface. | Correct placement per the earlier geometry finding, then tune neutral veil, border and shadow against light/dark backdrops. Screenshot capture scales differed, so exact point-size differences are not established here. |
| P2 | Sidebar/context menu uses Chromium groups and standard tab actions rather than Arc folders/archiving language. It already exposes New Split View, Copy URL, Duplicate, Pin, Mute and close-above/below actions. | Preserve these working capabilities. Improve grouping and discovery before proposing replacement folders. Labels should describe actual behavior: do not rename Close to Archive without durable archive/restore semantics. |

### Color and appearance customization differences

These compare Arc's inspected editor with the running Helium editor. Arc's pale lavender/gray configuration and Helium's graphite configuration are different user choices; the color difference alone is not a defect. No preset or mode was changed to force a visual match.

| Area | Arc observed | Helium compiled/source evidence | Useful amendment |
| --- | --- | --- | --- |
| Editing experience | In-window translucent popover, opened from Spaces → Edit Theme; current browser remains visible behind it | Separate native Appearance floating window, with a miniature frame preview and ordinary labeled controls | Keep controls understandable. A compact anchored editor could improve live context, but fixing preview fidelity has higher priority than replacing the window. |
| Theme scope | Entry belongs to Spaces; exact sharing across windows/profiles untested | Theme stored in profile preferences in the inspected source | State the actual scope in the editor. If Spaces are later added, decide inheritance and overrides before adding independent Space colors. |
| Presets | Paged Brand, Pastel, Drab and Greyscale families; circular swatches | Four labeled presets: Mint, Coral, Lavender and Graphite | Add a few tested neutral/pastel choices after material rendering is corrected. Keep preset names and selected-state indication accessible. A large gallery is optional. |
| Custom color input | Spatial color workspace with ringed handle plus add/remove controls | Explicit Color 1…3 native color wells; add/remove limited to one–three colors in source | Current color wells are a useful precise editing path. Preserve them. Arc's workspace may offer spatial control, but that behavior was not tested; do not claim the current gradient is equivalent. |
| Gradient geometry | Editor has a two-dimensional dotted workspace; interpolation and direction semantics unresolved | Fixed top-leading → bottom-trailing linear gradient, evenly distributed stops, window-aligned in the source | A direction control could be medium-sized follow-up if users need it. Free-position gradients are larger work and need evidence of benefit. |
| Intensity | Independent labeled slider; numeric value/range unavailable | Slider at 67 in this profile, source range 10–100; colors blended toward system surface with distinct light/dark factors | Explain intensity consistently and show its effect in the preview. Current intensity is not simply the original color's saturation or a direct opacity percentage. Consider reset-to-preset intensity and a readable value if useful. |
| Grain choices | Explicit Cycle noise texture action and a separate unlabeled slider/radial control | Boolean Subtle grain only; currently enabled. Source uses sparse deterministic gray dots | Highest material-quality gap: replace the regular stipple with irregular static grain. Add texture/strength choices only when they produce useful, clearly labeled differences. The Arc dial's exact function remains unconfirmed. |
| Appearance mode | Sparkle/sun/moon buttons; exact automatic semantics unconfirmed | Clearly labeled System/Light/Dark; System selected | Helium already exposes the basic choices well. Validate automatic updates and contrast rather than adding another mode selector. |
| Preview fidelity | Editing occurs over the actual browser chrome; no separate miniature preview in the inspected popover | Miniature uses raw colors, while frame uses system-surface blending and grain; preview omits both treatments | Small-to-medium correction with immediate value: make preview and frame follow the same color/material specification. Include mode, intensity and texture. |
| Surface color relationships | Pale textured sidebar/frame, dark content toolbar and dark translucent popover in observed configuration | Dark neutral sidebar/toolbar, blue-gray Home/content frame, separate gray native palette in current configuration | Define related but distinct colors for frame, toolbar, Home, palette and selection. Verify propagation after edits; changing frame color should not accidentally recolor websites or flatten selection contrast. Current screenshots do not establish how Arc derives these colors. |
| Density and tile sizing | No corresponding density/tile-size controls found in Arc's theme popover | Compact/Comfortable spacing and 40–72 pt pinned-tile choices in source; current values Compact/48 pt | These are existing Helium customization strengths. Keep layout settings visually separate from color/material settings so color editing stays focused. |
| Reset and unrelated choices | No reset control identified in inspected Arc popover | Reset appearance and Done present; online search suggestions also placed in Appearance | Keep reset predictable and indicate its scope. Move search suggestions into navigation/search preferences eventually; they have no visual effect and currently make appearance settings less focused. |

Suggested order: **accurate preview → irregular grain and seamless alignment → coherent surface/selection colors → a few additional presets → optional gradient direction or texture strength**. The first three improve the result for every theme. A bigger color editor would add controls before those underlying differences are resolved.

### Runtime findings that change the earlier matrix

- **Native UI opens:** command palette and appearance window are now observed in the integrated app. This verifies these entry points only; it does not establish general idle stability, all focus paths or all preference updates.
- **New-destination navigation:** submitting `example.com` through Cmd+T created a second tab while retaining the initial New Tab. The disposable tab was later closed. This confirms that path's basic allocation behavior.
- **Appearance preview mismatch:** the running editor shows the simplified flat preview described in source. Its grain checkbox is enabled, but the preview contains no visible corresponding grain treatment. The mismatch is therefore visible in the compiled app as well as source.
- **Pins/splits/groups available as actions:** the tab menu confirms their discoverability. Dragging, pin conversion, resizing and persistence were not exercised, so those remain unverified.
- **Chat opens, close behavior remains suspect:** the toolbar button opened the official extension side panel. Subsequent rapid clicks left the panel in the tree and appeared to recreate its extension content; its accessible label changed to Close Chat with a delay. The explicit side-panel close control eventually removed the panel, confirmed by a later screenshot. A stale Close Chat label still appeared after the panel had disappeared. This is evidence of asynchronous visibility/label behavior, not a proven root cause. Do not count second-click close as validated. A controlled open → wait until loaded → click once → inspect after settling test is needed before deciding whether dispatch, visibility tracking or just observation timing is responsible. No prompt was submitted.

The most useful small amendments are **sidebar access to appearance, clearer initial Home/New Tab presentation, empty-palette priorities, and consistent tab-state styling**. Shared address editing and toolbar ownership have greater impact but require navigation/focus work. Populating favorites, implementing Spaces or rewriting tab organization is not justified by this empty profile alone.

## Explicit product requirements added November 6

### P1: Chat toggle visibility and stale label

**Flagged unresolved in the compiled build.** The November 6 inspection opened the ChatGPT panel, but repeated toolbar clicks did not establish reliable second-click closure; extension content appeared to be recreated, and the accessible Close Chat label lagged behind actual panel visibility. An explicit panel-close action eventually closed it. The issue was already recorded in the runtime notes and is promoted here to a first-class gap. Root cause is unknown; asynchronous loading and observation timing remain possible contributors.

Required behavior: one click opens Chat; a second click closes it, including while loading. Reopening should preserve the extension's normal conversation behavior. Closing via the panel's own control must immediately reconcile the toolbar's visible/accessibility state. Acceptance: verify opening, loaded second-click close, loading-time second-click close, direct close, reopen, and profile/window switching; no duplicate panels, unintended reload loop or stale Open/Close label. Integration points: `arc_chat_button.cc`, extension action dispatch and side-panel visibility observation. Complexity: medium until the event sequence is isolated. No prompts or credentials are needed for the toggle test.

### P1: iCloud Passwords support

User-requested compatibility gap; **not yet validated in Helium Sidebar/Xenon**. Start with Apple's official [iCloud Passwords extension](https://chromewebstore.google.com/detail/icloud-passwords/pejdijmoenmkgeppbflobdenhhabjlaj?hl=ena), ID `pejdijmoenmkgeppbflobdenhhabjlaj`. Apple's Store listing describes filling/saving iCloud Keychain passwords and verification-code support, and specifies macOS Sonoma or later. This establishes the extension's documented Chrome capabilities, not support for this custom Chromium app.

Smallest useful scope: an optional setup path to the official extension plus verification that this browser identity can communicate with Apple's supported password integration. Investigate native messaging/helper discovery, signing and browser identity requirements before promising compatibility; no specific helper workaround is established by this research. Do not copy credentials into a browser-owned database or bypass Apple's authorization. Password and verification-code tests require a user-controlled test account and user-completed unlock/approval. Private-window support and passkeys must be verified separately rather than inferred from password filling.

Acceptance: supported macOS configuration can install the official extension, complete Apple's normal authorization, fill and save/update a disposable credential, and expose available verification-code behavior without leaking state across browser profiles. Document any platform or custom-browser limitation with a clear unsupported state. Test interaction with Chromium's password prompts to avoid duplicate saving. Complexity: unknown/medium-to-large pending compatibility investigation. No automatic iCloud Passwords installation or access to the user's vault is requested here.

### P1: automatically download the official ChatGPT extension in each profile

User requirement: each regular browser profile should receive the official [ChatGPT extension](https://chromewebstore.google.com/detail/chatgpt/hehggadaopoacecdllhhajmbjkdcmajg?hl=en), ID `hehggadaopoacecdllhhajmbjkdcmajg`, by default, analogous to the convenience of uBlock Origin being available. Preserve user removal/disable choices and normal extension permission acknowledgement; private-window access is separate. Do not substitute the different ChatGPT Search extension.

**Already configured in source; runtime completion unverified.** `arc-default-chat-extension.patch` is included in `patches/series`. It registers the ChatGPT ID as the profile preference's initial-install default. `ExternalProviderImpl` constructs its loader using `profile->GetPrefs()`, and `kInitialExternalExtensions` is enabled by default in `chrome/browser/browser_features.cc`. The loader supplies the official Web Store update URL. This is a per-profile download/install path, not merely a first-window Chat button, and is distinct from uBlock's component-extension mechanism. Its provider explicitly uses `set_auto_acknowledge(false)`, so automatic download must not be represented as silent permission approval or guaranteed immediate activation.

No duplicate implementation was added: the requested download behavior is already represented by this tracked patch. Acceptance remains: create two disposable regular profiles in a compiled test build; verify each independently downloads the exact official ID and updates normally, with clear pending/failed/offline states. Restart after removal/disable to ensure the user's choice is respected. Check an existing profile upgrade and any previously persisted empty initial-install list separately; do not assume preference defaults overwrite existing stored values. A successful panel opening in one existing profile does not prove these cases. No production profile was created or modified for this research.

### P1: rename the product to Xenon

User-selected product name: **Xenon**. This is a planned product rename; historical observations above retain “Helium Sidebar” to identify the build actually inspected. No binary or source identity has been renamed by this research edit.

Scope: application/menu/About titles, Dock and Finder display name, settings and first-run copy, installer/DMG/archive names, download/release labels, default-browser registration and any extension-install provider branding. Audit remaining user-facing “Helium Sidebar” and inherited Helium names while preserving required license and attribution notices. Repository/upstream technical identifiers do not all need cosmetic renaming.

Choose the bundle ID, signing identity, profile-directory and Keychain migration strategy explicitly before implementation. A display-name change must not silently strand existing profiles, saved credentials, extension state or session data. Retaining the current stable technical identity may make migration simpler; a new identity requires a documented migration and coexistence policy. iCloud Passwords compatibility checks must use the intended final app identity.

Acceptance: a release identifies itself as Xenon across application UI, Finder/Dock and installer; existing users retain their browsing data and extensions through the supported upgrade; ordinary upstream Helium remains separate; default-browser links open the intended Xenon app. Confirm signed/notarized distribution and updater/release paths use consistent identity. Complexity: small for visible wording, medium-to-large if bundle/signing/storage identities also change. Add no new branding assets without a separate design decision.

## Screenshot follow-up: padding and closing the last tab

User-supplied evidence, November 6: `Screenshot 2026-11-06 at 10.08.10 AM.png` (Helium Sidebar) and `Screenshot 2026-11-06 at 10.08.15 AM.png` (Arc). Both originals are 3248×1922; the chat displays resized 2048×1212 versions. The estimates below refer to the **displayed image pixels**, not macOS points or original-file pixels. Their window bounds are approximately equal, making relative layout comparison useful. Exact point values still require window-scale measurement.

### P1: content-frame padding and toolbar alignment

| Relationship | Helium screenshot | Arc screenshot | Amendment |
| --- | --- | --- | --- |
| Top of content frame relative to outer window | Window begins near y=49; content begins near y=101, roughly 52 displayed pixels below it | Window begins near y=49; content frame begins near y=60, roughly 11 pixels below it; navigation sits inside that frame | Integrate the content toolbar into the rounded content region so the frame can begin near the window top. This is structural toolbar placement, not simply reducing the toolbar height. |
| Right and bottom outer gutters | Content nearly touches the outer window boundary: roughly 3–5 displayed pixels | Approximately 11–13 displayed pixels remain around the content frame | Increase and unify the exposed frame inset at right/bottom. Use one inset rule with intentional corner treatment, then validate at actual display scale. |
| Sidebar/content boundary | Content begins near x=399, versus outer left x=71 | Content begins near x=358, versus outer left x=71 | Arc's sidebar region is narrower in this pair. Treat sidebar width as independently adjustable; it is not all “padding.” Do not hard-code a width from a single user configuration. |
| Sidebar top region | Ordinary selected New Tab begins directly below the global toolbar | Favorites occupy the top, followed by a heading and New Tab action | Preserve room for actual organizational sections. Avoid adding blank vertical padding merely to imitate a populated Arc sidebar. |
| Content edge treatment | Fine visible outline and small rounded corners, with very little surrounding frame at the bottom/right | Rounded inset panel and soft shadow visibly separate it from the textured frame | Tune inset, corner radius, outline and shadow together. Increasing radius alone will not reproduce the framing. |

The practical target is a continuous outer material around an inset content panel, with balanced top/right/bottom breathing room and a coherent sidebar boundary. The sidebar's width and internal row padding are separate controls. Keep page content, toolbar content and outer frame insets distinct in the design specification. Verify narrow windows, hidden sidebar, splits and fullscreen before adopting fixed values. Avoid claiming a precise point-based padding target from these resized images.

Acceptance: in comparable window bounds, the content panel has a deliberate, consistent exposed frame on its top/right/bottom; its toolbar belongs visually to the panel; corner/shadow transitions are clean; sidebar resizing does not change the outer gutter unexpectedly. Existing density preferences should affect rows and controls without accidentally collapsing the content-frame inset.

### P1: closing the last tab should return to New Tab

**User-confirmed Arc behavior:** closing all tabs opens a New Tab state. The supplied Arc screenshot shows an empty main area with the “Search or Enter URL…” display and the sidebar's New Tab action. It does not show an ordinary selected New Tab row with its own close button. The image establishes the visible final state; the transition is supplied by the user's observation rather than independently replayed here.

Required Xenon behavior: closing the last ordinary tab should keep the browser window available and transition to a usable Home/New Tab state. Avoid leaving a blank unusable window or requiring the user to create a new window. The final close must not create a stack of redundant New Tab entries. This sharpens the earlier Home/New Tab proposal: the destination should be an intentional empty-window browsing state, with the exact internal tab allocation left to implementation.

Distinguish this from Cmd+T: invoking the command surface over an existing page must still allocate no tab until a destination is accepted. Likewise, cancelling the surface in the last-tab Home state must leave that Home state usable. Do not infer that Arc automatically opens the floating command surface after last-tab closure—the supplied screenshot shows its placeholder display, not an open palette.

Acceptance: close the final ordinary tab with its close button and Cmd+W; the window remains on Home/New Tab with a clear search entry. Enter a destination and get exactly one ordinary tab. Repeat closure without accumulating Home tabs. Reopening a closed tab restores the prior destination according to normal session rules. Explicit Close Window/Quit must still close the window/app. Test pinned-only, multi-window, private-window and split-view cases separately; the desired policy for those cases has not yet been established. Chromium's last-tab/window lifecycle and session restore are likely integration points; complexity is medium until those interactions are specified.

## Screenshot follow-up: sidebar states and vertical position

Additional user evidence, November 6: screenshots at **10.09.55** (Helium's inset/revealed-looking sidebar), **10.10.33** (Arc Home with sidebar visible), **10.10.40** (Arc webpage with sidebar overlay), and **10.11.50** (Arc webpage with sidebar hidden). Images are displayed at 2048×1212 from 3248×1922 originals. Positions below are approximate displayed-image pixels; they are not macOS points. A still image establishes appearance, not the exact hover trigger or animation timing.

### P1: define separate docked, hidden, revealed and Home states

| State | Evidence and desired Xenon behavior |
| --- | --- |
| Docked | Sidebar has its own reserved width; content begins beside it. Retain distinct docked layout rather than treating every visible sidebar as an overlay. Previous screenshots establish this reference. |
| Hidden while browsing | Arc's 10.11.50 screenshot gives the webpage nearly the full inset panel width. The sidebar is absent, but its toggle remains at the top left of the content toolbar. Xenon should retain an obvious reveal/toggle route and keyboard access. |
| Temporarily revealed while browsing | Arc's 10.10.40 screenshot shows a rounded elevated sidebar covering the left portion of the existing page, including the beginning of its headline. Comparison with 10.11.50 shows matching page content positions, consistent with an overlay rather than a layout that shrinks the page. Preserve the webpage viewport during temporary reveal; reserve reflow for a deliberate docking change. |
| Home/New Tab with hidden preference | **User-confirmed behavior:** Arc keeps the sidebar visible on New Tab even when hidden mode is selected. The 10.10.33 screenshot shows that visible Home state. Xenon should temporarily require sidebar visibility on Home, preserving access to favorites and New Tab, while retaining the user's hidden preference for browsing pages. This should be a context override, not silently changing the saved preference to docked. |

Proposed transitions: hidden browsing → Home keeps/reveals the sidebar; accepting a destination from Home restores the user's browsing visibility preference; a temporary reveal leaves the webpage viewport unchanged; pointer dismissal must not hide the sidebar while focus or an anchored menu/dialog is inside it. Exact hover delays, animation and Arc's focus behavior remain unmeasured. These are Xenon acceptance requirements, not reverse-engineered Arc timing.

Acceptance: exercise docked and hidden preferences through Home → destination → last-tab close → Home, with Cmd+T/Escape in each state. Home stays usable and visible; destination pages recover the selected browsing preference. Test keyboard focus, menus, permission bubbles and drag operations without accidental dismissal. Do not let repeated transitions overwrite the stored preference, accumulate Home tabs or resize the page during temporary reveal. Integrate with the existing zen/sidebar controller and Home/last-tab lifecycle rather than adding a second visibility system. Complexity: medium.

### P1: raise the revealed sidebar to the window's top inset

Helium's 10.09.55 sidebar begins near **y=103**, below the global toolbar. Arc's revealed sidebar begins near **y=56**, close to the outer window top at y=49. Arc's panel includes the traffic-light/header region; Helium's panel begins beneath it. This roughly 47 displayed-pixel difference is primarily ownership of the top chrome, not merely excess padding above the first tab.

Amendment: let the revealed sidebar span from the window's top inset to its bottom inset, with a header containing safe space for window controls and the sidebar toggle. Keep traffic-light hit targets, window dragging and content-toolbar controls functional. Do not move only the first tab upward while leaving its enclosing panel beneath the toolbar. The earlier toolbar-ownership and frame-inset proposals are dependencies.

### Other differences to amend

| Difference | Evidence | Proposed correction |
| --- | --- | --- |
| Overlay elevation | Arc's revealed panel has rounded outer corners and a visible soft edge shadow over the page; Helium's inset panel is primarily outlined and reads as another rectangle within Home | Use a consistent overlay material, subtle border and shadow to distinguish temporary reveal from docking. Keep the surrounding outer inset coherent. |
| Sidebar header and footer | Arc includes top window controls/favorites and a bottom utility row; Helium's shown panel contains ordinary tabs and New Tab, with no corresponding footer | Keep essential navigation and appearance/organization actions discoverable in the sidebar. Add only working utilities; Space controls depend on an actual Spaces feature. Pin footer actions to the bottom while the tab area scrolls. |
| Home composition | Arc's Home is a quiet themed field, with destinations concentrated in sidebar favorites. Helium also shows shortcut tiles in the central page and an ordinary New Tab row | Specify one coherent Home model. Prioritize sidebar destinations and a clear search entry; decide how existing Chromium shortcuts are retained or optionally shown rather than displaying redundant destination systems by accident. |
| Toolbar when sidebar is hidden | Arc's sidebar toggle, back/forward and reload occupy the upper-left content toolbar; the compact address remains centered. Helium keeps a separate global toolbar in the supplied state | Keep navigation anchored to the content panel across visibility states. Opening an overlay should not shift the centered address or page layout. |
| Selection within favorites | Arc's webpage screenshot shows a colored outline/fill on the active favorite tile, while Home shows no matching active destination | Preserve distinct active-tab, hover and keyboard-focus treatments. Returning Home must clear the prior destination's active treatment without unpinning it. Helium favorite/pin runtime states still need a populated disposable-profile test. |

These screenshots strengthen the existing layout recommendations but do not prove Helium lacks hidden/reveal machinery: source already contains a zen-mode controller. The gap is the state-specific geometry and Home policy, plus validation that the existing controller produces them consistently.

## Controlled follow-up

Use disposable tabs and a small explicit fixture set after the integrated artifact is stable. Verify current/new-tab Enter behavior, Command+Enter raw query, Tab/Shift+Tab site search, Backspace on selected suffix, IME composition, repeated open, click outside and focus restoration. Then check exact/partial title and host matches, deduplication, recency and late responses with a known profile. Do not seed a large private history dataset.

Measure window/palette bounds in points and repeat with sidebar shown/hidden, narrow bounds, fullscreen and splits. Check VoiceOver, reduced motion/transparency, high contrast and pointer/keyboard coexistence. Helium already reads reduced-motion/transparency preferences in its native view; runtime behavior still needs inspection. Test session recovery before enabling automatic archiving or auxiliary windows.

No CI status was needed for these findings, so the historical build was not polled or modified. This report makes no claim about successful integration, object-cache reuse or build completion.

## Primary references

- [Arc command bar actions](https://start.arc.net/command-bar-actions): discoverable browser actions through the command bar; used only for the action-discovery recommendation.
- [Arc toolbar instructions](https://resources.arc.net/hc/en-us/articles/25625617866263-How-Do-You-Move-Your-Pinned-Extensions-to-the-Top-Right): documents enabling the toolbar on macOS. Current toolbar presence and compact URL behavior above were observed directly.

Live observations and local source inspection supply the remaining evidence. Historical release notes are not treated as proof that a feature is available in this installation.
