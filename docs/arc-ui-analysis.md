# Arc reference and native Helium implementation

## Observed in Arc

Inspection used Arc's live native UI, including empty input, tab prefixes,
commands, general search queries, inline completion, and arrow navigation.
Arc's internal implementation is closed source; the observations below do not
establish its indexing algorithms or framework choices.

The command bar is approximately 760 points wide. Its input is about 56 points
high, results about 46 points high, and the outside inset about 10 points.
Rounded corners, a thin divider, one-line results and quiet trailing actions
keep the hierarchy simple. It shows roughly five results before scrolling.
Its dark surface visibly picks up surrounding colors through native blur.
There is no persistent footer or separate search-engine selector in this view.

At empty input, recent/open destinations dominate. A matching tab prefix can
produce inline URL completion with the suffix selected and a Switch to Tab
row. A command prefix such as `new win` promotes the matching command. General
queries show the typed search and engine completions. Arrow keys change the
selected result and can change the displayed input. Exact ordering varies with
history and available tabs; observing one profile cannot reveal universal weights.

## Implemented behavior

The visible command bar is SwiftUI with an AppKit text field and native visual
effect view. The field preserves IME composition and keeps the raw query
separate from inline completion and keyboard presentation. Enter opens the
selected result; Command+Enter searches the original query. Escape and focus
loss close the palette. Repeated New Tab shortcuts reuse the existing palette.
Opening or cancelling the palette does not allocate a tab.

The C++ controller combines same-profile open tabs, Chromium's existing local
history/bookmark/shortcut providers, browser commands and default-engine search
suggestions. Exact commands, navigation intent and strong tab matches rank above
weak substring matches. Results deduplicate destination URLs. Explicit keyboard
selection retains its identity across asynchronous result updates.

There is no second history database. Chromium's HistoryQuickProvider uses its
existing in-memory URL index; history URL, bookmarks and shortcuts retain their
own native provider behavior. Accepted navigation matches update the shortcut
backend outside private windows. Open tabs are scanned locally using all query
tokens across title and URL, with recency breaking equal scores.

Online suggestions use the selected search engine's SearchProvider, with a
120 ms debounce. Query changes clear prior remote results; closing stops the
provider. Private windows never start remote requests. The native appearance
editor includes a switch for online suggestions, and managed prohibitions on
search suggestions still apply. The user explicitly approved this feature.

The URL field stays at the top of browsing pages and is hidden on Home. A
flexible spacer keeps the remaining toolbar controls aligned. Comfortable
spacing increases the browser gutter and tab height. The native appearance
editor controls gradient stops, intensity, grain, light/dark mode, density and
pinned tile sizes. Chat toggles its extension side panel closed on a second click.

## Stability and validation limits

The supplied crash was symbolicated against its matching framework dSYM. It
reached an anchored bubble's theme notification before the bubble had a Widget,
then called Widget::ThemeChanged with a null receiver. The guarded notification
preserves live-bubble updates. A focused regression binary covers both cases.
The Swift host also attaches only after NativeViewHost belongs to a Widget.

Syntax compilation and the isolated native UI harness validate compilation,
visible layout, focus and keyboard movement. The integrated browser still needs
runtime verification from the GitHub artifact: mixed web/native focus, sidebar
extension behavior, online responses, live spacing updates, and idle appearance
notifications. These are not established by a preview or source compilation.

## Next improvements to assess in the running browser

- Verify density and pinned-size changes under narrow and wide window layouts.
- Measure typing latency and animation frame times with a large history and many tabs.
- Add stable mouse hover selection without interrupting active keyboard navigation.
- Improve highlighted matching text and keyboard shortcut badges while keeping rows quiet.
- Consider tab folders, pinned destination management, and split views after the
  core navigation and focus behavior is reliable.

References: [Chromium history provider](https://www.chromium.org/omnibox-history-provider/),
[its index cache](https://www.chromium.org/omnibox-history-provider/caching/), and
[Arc command actions](https://start.arc.net/command-bar-actions).
