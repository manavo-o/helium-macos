# Implementation status — November 4, 2026

The downloadable artifact from run 41840388482 contains the earlier palette
foundation. The changes described below are local source changes awaiting a
new full browser build; they have not been validated in that downloaded app.

| Area | Source state | Validation remaining |
| --- | --- | --- |
| Sidebar | Real navigation/omnibox views, fixed vertical layout, 200–480 width, pinned tile sizing and density preferences | Native runtime, security/permission bubbles, fullscreen, accessibility |
| Chat | Official ID, toolbar action dispatch, existing-panel focus, availability popover, private permission checks | Installed extension action parity, tab context, conversation continuity, updates/removal |
| Extension setup | First-run Web Store installation through native loader, normal acknowledgement, user opt-out | Fresh profile installation and restart; loader test execution |
| Palette | Deferred tab creation, native local providers, tabs across same-profile windows, commands, routing override, focus restoration | Browser test execution, keyboard/VoiceOver and actual network assertions |
| Visuals | Theme-colored home, inset rounded content, themed floating palette, dock/hide/reveal sidebar, top Chat control | Packaged light/dark/custom-theme screenshot comparison |
| Routing | Local detection/provider allowlist; built-in official search-provider handoff | Run focused tests; signed-out and encoding behavior in separate profile |
| Split | Upstream Helium foundation retained | Quarter-width previews, replacement retaining displaced tabs, and drop-completion pin/unpin are implemented; browser/drag and session tests remain to run |
| App identity | Separate name, bundle/profile/keychain identifiers, own update feed path | Personal ad-hoc packaging selected by the user; validate own identity/profile and manual upgrades. Developer ID/notarization are optional. Controlled feed publication remains pending. |
| Incremental CI | Existing bounded one-line checkpoint repair retained | Verified source-delta reuse of run 41840388482 is implemented and passes three recovery tests; validate in CI |

Validation completed for this source work: patch/license/header lint; GN
generation and toolbar/palette header dependency checks; actual generated
compiler-command syntax checks for Chat, palette, toolbar, question routing, sidebar, split handler/controller/preview and pin-drag controller. The broader frame-target GN check also exposes inherited header dependency failures; these are not claimed as passing.
These are not a substitute for a complete browser link or macOS runtime tests.
