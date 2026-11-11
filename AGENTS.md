# Validation policy

- Validate browser behavior visually in the GitHub-built macOS app. Do not make
  Chromium's full `browser_tests` suite a build or delivery gate. Helium removes
  upstream APIs and does not maintain every Chromium test fixture; do not expand
  fixture compatibility work merely to get that suite compiling.
- Keep local checks lightweight. Check persistent patch applicability, source
  integrity, and relevant build-script safeguards. Build and package on GitHub.
- For command-bar ChatGPT changes, visually check Home-tab reuse, a foreground
  destination from a regular page, current-tab address editing, command-bar
  closure, and destination focus. Preserve routing preferences and Cmd+Enter.
- Verify submission while signed in using a benign prompt. It must appear once
  as a sent message and ChatGPT must begin responding without a second Enter.
  Report composer-only prefilling separately from navigation or visibility.
- A successful build does not establish visual acceptance. Report visual checks
  as pending until observed. When work is complete and only CI is running, end
  the turn and let the user report results instead of waiting or polling.
