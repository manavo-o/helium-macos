# Helium Sidebar signing and release setup

The user selected a personal, ad-hoc-signed build on November 4, 2026. No Apple
Developer account, Developer ID signature or notarization is required for that
scope. The repository has no Actions signing secrets; current packaging uses
the ad-hoc path. The optional setup below is only for a future notarized release.

Configure these in this repository's Settings →
Secrets and variables → Actions, using this app owner's Apple Developer account.
Never paste private credentials into chat or commit them to the repository.

| Secret | Value |
| --- | --- |
| `PROD_MACOS_CERTIFICATE` | Base64-encoded export of the owner's Developer ID Application certificate and private key as a `.p12` |
| `PROD_MACOS_CERTIFICATE_PWD` | Password protecting that `.p12` |
| `PROD_MACOS_CERTIFICATE_NAME` | Exact Developer ID Application certificate common name |
| `PROD_MACOS_CI_KEYCHAIN_PWD` | Dedicated random password for the temporary CI keychain |
| `PROD_MACOS_NOTARIZATION_APPLE_ID` | Apple account used for notarization |
| `PROD_MACOS_NOTARIZATION_TEAM_ID` | Owner's ten-character Apple Developer team ID |
| `PROD_MACOS_NOTARIZATION_PWD` | Apple app-specific password for notarization |

Optionally set public Actions variable `ARC_MACOS_TEAM_ID` to that same team ID;
otherwise the notarization team secret supplies the build identity. The fork
must not use Helium upstream's team or provisioning profile. A special
entitlements profile is optional and must belong to this app/team if used.

The signing script verifies the bundle ID `io.github.manavo.helium-sidebar`,
checks the application signature, validates its notarization ticket and
Gatekeeper assessment, then signs, notarizes and staples the distribution DMG.
An ad-hoc preview is never described as a notarized release.

Automatic updates are disabled unless this fork's separate
`ARC_MACOS_SPARKLE_ED_PUB_KEY` secret is configured. The private Sparkle signing
key must stay with the release owner. Before enabling updates, publish a signed
`appcast-arm64.xml` and this app's own signed artifacts on the controlled
`arc-updates` channel, verify the signature and an upgrade from an earlier
Helium Sidebar build, and verify profile/session preservation. Do not point the
fork at standard Helium's releases. Feed publication and upgrade validation are
still pending; configuring a public key alone does not complete release setup.

The preview DMG uses Finder's default layout rather than the old `.DS_Store`,
which refers to `Helium.app`. The existing optional `appdmg@0.6.6` layout helper
is not invoked by CI. No new installer-generation package was added.

## Personal Xenon updates

The personal release pipeline uses ad-hoc macOS signing and Sparkle Ed25519
signatures. The latter come from a free Xenon-specific keypair. Keep the
private key in the owner's keychain and back it up securely. Set the public
key in the `ARC_MACOS_SPARKLE_ED_PUB_KEY` Actions secret. Configure the private
key as `XENON_UPDATE_PRIVATE_KEY` in the `xenon-release` Actions environment.
Use Sparkle's `generate_keys --account xenon-personal` and its `-p` and `-x`
options. Export temporarily with restrictive permissions, pass the key file
to `gh secret set` through stdin, and remove that temporary export.

Deploy the Xenon changes to `arc-helium`. Install
`.github/workflows/xenon-upstream.yml` and
`.github/workflows/xenon-promote.yml` on the default branch. Both workflows
check out `arc-helium` for their implementation. Enable scheduled workflows
for this fork if GitHub has disabled them. The upstream watcher checks the
published macOS release, creates one candidate branch per tag and dispatches
the existing build workflow. Conflicts or unsupported upstream platform
changes are listed in the candidate's blocker file. If the clean preparation
fails, review the build log, port the fork patches and audit the matching
test fixtures on the candidate, then rerun the workflow with
`xenon-fresh=true`. Keep production release approval manual.

To test replacements, install the older updater-enabled DMG on the target Mac.
Use an isolated copy of Xenon and launch it with both
`--user-data-dir=<disposable-profile>` and `--xenon-test-updates`.
Keep the existing Helium update-check preference enabled for that profile.
Promote the newer build to the **test** feed with its successful run ID and
full commit SHA. Check About and verify that the update can be downloaded,
installed and relaunched. Verify version, session, bookmarks, settings, and
profile preservation. Check that Cancel preserves the installed version.
Exercise the manual download flow and inspect the packaged icon and theme
on that Mac. Validate rejection of an older feed item and of an archive or
feed altered after signing before enabling replacement on the personal feed.

The **personal** promotion defaults to a signed informational update that
opens the matching GitHub release. Set **Enable in-app replacement** only
after passing the target-Mac checks. The same build can be promoted from test
to personal. Every promotion publishes a versioned prerelease before it
advances its feed. A failed feed push can be retried with the same run as
long as its version is still newer than the current feed. Old release assets
remain available. Gatekeeper may require an initial manual approval for
personal ad-hoc builds.
