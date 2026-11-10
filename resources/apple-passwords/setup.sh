#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="$HOME/.local/share/xenon/apple-passwords"

echo "=== Xenon Apple Passwords Setup ==="
mkdir -p "$TARGET_DIR"

# 1. Compile native C bridge
echo "Compiling native bridge binary..."
clang -O2 "$SCRIPT_DIR/bridge.c" -o "$TARGET_DIR/xenon-apple-passwords-bridge"
chmod +x "$TARGET_DIR/xenon-apple-passwords-bridge"

# 2. Copy daemon script
echo "Installing relay daemon..."
cp "$SCRIPT_DIR/daemon.js" "$TARGET_DIR/daemon.js"
chmod +x "$TARGET_DIR/daemon.js"

# 3. Locate and stage Apple Passwords extension
echo "Staging Apple Passwords extension..."
EXT_DEST="$TARGET_DIR/extension"
mkdir -p "$EXT_DEST"

FOUND_EXT=""
for search_path in \
  "$HOME/Library/Application Support/io.github.manavo.helium-sidebar/Default/Extensions/pejdijmoenmkgeppbflobdenhhabjlaj" \
  "$HOME/Library/Application Support/net.imput.helium/Profile 1/Extensions/pejdijmoenmkgeppbflobdenhhabjlaj" \
  "$HOME/Library/Application Support/net.imput.helium/Default/Extensions/pejdijmoenmkgeppbflobdenhhabjlaj" \
  "$HOME/Library/Application Support/Google/Chrome/Default/Extensions/pejdijmoenmkgeppbflobdenhhabjlaj" \
  "$HOME/Library/Application Support/BraveSoftware/Brave-Browser/Default/Extensions/pejdijmoenmkgeppbflobdenhhabjlaj"; do
  if [ -d "$search_path" ]; then
    VERSION_DIR=$(ls -1 "$search_path" 2>/dev/null | sort -V | tail -n 1)
    if [ -n "$VERSION_DIR" ] && [ -f "$search_path/$VERSION_DIR/background.js" ]; then
      FOUND_EXT="$search_path/$VERSION_DIR"
      break
    fi
  fi
done

if [ -n "$FOUND_EXT" ]; then
  echo "Found extension at $FOUND_EXT"
  cp -R "$FOUND_EXT/"* "$EXT_DEST/"
  rm -rf "$EXT_DEST/_metadata"
else
  echo "Note: Extension pejdijmoenmkgeppbflobdenhhabjlaj not found in local profiles yet."
  echo "Please install it in Xenon or Chrome from the Chrome Web Store."
fi

# 4. Install NativeMessagingHosts manifest for Xenon ONLY
# Note: Never install into net.imput.helium or Google/Chrome, as they have native Apple entitlements.
MANIFEST_JSON='{
  "name": "com.apple.passwordmanager",
  "description": "PasswordManagerBrowserExtensionHelper",
  "path": "'"$TARGET_DIR/xenon-apple-passwords-bridge"'",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://pejdijmoenmkgeppbflobdenhhabjlaj/",
    "chrome-extension://mfbcdcnpokpoajjciilocoachedjkima/"
  ]
}'

# Clean up any accidental entries in Helium or Chrome
rm -f "$HOME/Library/Application Support/net.imput.helium/NativeMessagingHosts/com.apple.passwordmanager.json" \
      "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.apple.passwordmanager.json" \
      "$HOME/Library/Application Support/Chromium/NativeMessagingHosts/com.apple.passwordmanager.json"

XENON_HOSTS_DIR="$HOME/Library/Application Support/io.github.manavo.helium-sidebar/NativeMessagingHosts"
mkdir -p "$XENON_HOSTS_DIR"
echo "$MANIFEST_JSON" > "$XENON_HOSTS_DIR/com.apple.passwordmanager.json"

# 5. Configure silent background LaunchAgent so Chrome never "opens" when Xenon starts
LAUNCH_AGENT="$HOME/Library/LaunchAgents/io.github.manavo.xenon.apple-passwords.plist"
if [ "${INSTALL_LAUNCH_AGENT:-1}" = "1" ]; then
  mkdir -p "$HOME/Library/LaunchAgents"
  NODE_BIN="$(command -v node || true)"
  if [ -z "$NODE_BIN" ]; then
    for p in /opt/homebrew/bin/node /usr/local/bin/node /usr/bin/node; do
      if [ -x "$p" ]; then NODE_BIN="$p"; break; fi
    done
  fi
  if [ -n "$NODE_BIN" ]; then
    cat <<EOF > "$LAUNCH_AGENT"
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>io.github.manavo.xenon.apple-passwords</string>
    <key>ProgramArguments</key>
    <array>
        <string>$NODE_BIN</string>
        <string>$TARGET_DIR/daemon.js</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/xenon_passwords_daemon.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/xenon_passwords_daemon.err</string>
</dict>
</plist>
EOF
    launchctl unload "$LAUNCH_AGENT" 2>/dev/null || true
    launchctl load "$LAUNCH_AGENT" 2>/dev/null || true
    echo "LaunchAgent installed: daemon runs silently in background at login."
  fi
fi

echo "=== Setup complete! ==="
echo "Restart Xenon or reload the Apple Passwords extension in chrome://extensions to pair."
