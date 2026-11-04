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
