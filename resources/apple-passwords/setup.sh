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

# 4. Install NativeMessagingHosts manifest for Xenon and Chrome
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

for hosts_dir in \
  "$HOME/Library/Application Support/io.github.manavo.helium-sidebar/NativeMessagingHosts" \
  "$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts" \
  "$HOME/Library/Application Support/Chromium/NativeMessagingHosts" \
  "$HOME/Library/Application Support/net.imput.helium/NativeMessagingHosts"; do
  mkdir -p "$hosts_dir"
  echo "$MANIFEST_JSON" > "$hosts_dir/com.apple.passwordmanager.json"
done

echo "=== Setup complete! ==="
echo "Restart Xenon or reload the Apple Passwords extension in chrome://extensions to pair."
