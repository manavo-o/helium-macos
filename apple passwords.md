# Apple Passwords in Xenon

## Summary & Resolution

Apple Passwords (and iCloud Keychain integration) now works natively in Xenon through an autonomous, headless parent proxy relay that satisfies macOS AMFI launch constraints without requiring SIP modification or custom developer certificates.

## Technical Root Cause

macOS Sonoma and Sequoia (macOS 15+) enforce parent launch constraints on `/System/Cryptexes/App/System/Library/CoreServices/PasswordManagerBrowserExtensionHelper.app/Contents/MacOS/PasswordManagerBrowserExtensionHelper`.

Direct inspection of the DER launch constraint blob (`0xfade8181`, slot 5) confirmed that AMFI requires the parent process to possess both an approved `signing-identifier` and `team-identifier`:
- `net.imput.helium` with Team ID `S4Q33XPHB4` (Stock Helium)
- `com.google.Chrome` with Team ID `EQHXZ8M8AV` (Google Chrome)
- `com.brave.Browser` with Team ID `KL8N8XSYF4` (Brave)
- `company.thebrowser.Browser` with Team ID `S6N382Y83G` (Arc)

Because Xenon is an ad-hoc signed fork (`io.github.manavo.helium-sidebar`, `TeamIdentifier: not set`), spawning the helper directly triggered an enforcing parent constraint violation, causing AMFI to terminate the process with `SIGKILL (-9)` ("couldn't connect to a helper application").

## The Workaround

Instead of having Xenon execute the Apple helper directly:
1. Xenon registers a user-level Native Messaging Host (`com.apple.passwordmanager.json`).
2. The manifest points to a standalone compiled C binary: `xenon-apple-passwords-bridge`.
3. The bridge pipes stdin/stdout frames over a local UNIX socket to a lightweight background relay daemon (`daemon.js`).
4. The daemon runs Google Chrome headlessly with an unpacked copy of the official Apple Passwords extension (`pejdijmoenmkgeppbflobdenhhabjlaj`).
5. Because Google Chrome is the parent process, macOS AMFI approves the parent launch constraint immediately.
6. The extension in Chrome connects to Apple's native helper, while the bridge forwards the standard native messaging frames directly between Xenon and the helper.
7. The user enters the 6-digit verification code in Xenon's extension popup, establishing the SRP-6a / AES-GCM session.

## Update Resilience

- **Browser Updates / Rebuilds:** The native messaging manifest and bridge binaries reside in standard user directories (`~/.local/share/xenon/apple-passwords/` and `~/Library/Application Support/.../NativeMessagingHosts/`), which persist across Xenon updates and reinstalls.
- **macOS Updates:** Because Google Chrome maintains active Developer ID notarization allowlisted in macOS, future macOS and Chrome updates remain fully compatible.
- **Portability:** The setup script (`resources/apple-passwords/setup.sh`) automates compilation, extension staging, and manifest configuration for any user machine.
