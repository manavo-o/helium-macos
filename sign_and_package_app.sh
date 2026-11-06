#!/bin/bash -eux

_root_dir="$(dirname "$(greadlink -f "$0")")"
_app="out/Default/Xenon.app"
_packaging="out/Default/Xenon Packaging"

if [ -n "${MACOS_CERTIFICATE_NAME:-}" ]; then
  if [ -n "${PROD_MACOS_SPECIAL_ENTITLEMENTS_PROFILE_PATH:-}" ]; then
    # Chromium embeds this profile from its packaging inputs during signing.
    cp "$PROD_MACOS_SPECIAL_ENTITLEMENTS_PROFILE_PATH" "$_packaging/Xenon.provisionprofile"
  fi

  CREDENTIAL_ARGS=(store-credentials notarytool-profile)
  NOTARY_ARGS=(--notary-arg=--keychain-profile=notarytool-profile)
  DMG_NOTARY_KEYCHAIN_ARGS=()
  if [ -n "${CI:-}" ]; then
    CREDENTIAL_ARGS+=("--keychain=$HOME/Library/Keychains/build.keychain-db")
    NOTARY_ARGS+=("--notary-arg=--keychain=$HOME/Library/Keychains/build.keychain-db")
    DMG_NOTARY_KEYCHAIN_ARGS+=("--keychain=$HOME/Library/Keychains/build.keychain-db")
  fi

  xcrun notarytool \
    "${CREDENTIAL_ARGS[@]}" \
    --apple-id "$PROD_MACOS_NOTARIZATION_APPLE_ID" \
    --team-id "$PROD_MACOS_NOTARIZATION_TEAM_ID" \
    --password "$PROD_MACOS_NOTARIZATION_PWD"

  python3 "$_packaging/sign_chrome.py" \
    --input out/Default \
    --output out/Default/signed \
    --identity "$MACOS_CERTIFICATE_NAME" \
    --disable-packaging --notarize \
    "${NOTARY_ARGS[@]}"

  _app="out/Default/signed/stable/Xenon.app"
else
  echo "warn: MACOS_CERTIFICATE_NAME is missing; skipping notarization" >&2
  codesign --force --deep --sign - "$_app"
fi

_bundle_id=$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$_app/Contents/Info.plist")
if [ "$_bundle_id" != io.github.manavo.helium-sidebar ]; then
  echo "Unexpected bundle identity: $_bundle_id" >&2
  exit 1
fi
codesign --verify --deep --strict --verbose=2 "$_app"
if [ -n "${MACOS_CERTIFICATE_NAME:-}" ]; then
  xcrun stapler validate "$_app"
  spctl --assess --type execute --verbose=2 "$_app"
fi

if [ -z "${OUT_DMG_PATH:-}" ]; then
  _chromium_version=$(cat "$_root_dir/helium-chromium/chromium_version.txt")
  _helium_revision=$(cat "$_root_dir/helium-chromium/revision.txt")
  _platform_revision=$(cat "$_root_dir/revision.txt")
  OUT_DMG_PATH="$_root_dir/build/xenon_${_chromium_version}-${_helium_revision}.${_platform_revision}_macos.dmg"
fi

# Package the app
chrome/installer/mac/pkg-dmg \
  --sourcefile --source "$_app" \
  --target "$OUT_DMG_PATH" \
  --volname "Xenon" --format ULMO \
  --icon "$_app/Contents/Resources/app.icns" \
  --symlink /Applications:/Applications \
  --mkdir .background \
  --copy "$_root_dir/resources/dmg_background.png:/.background/dmg_background.png" \
  --verbosity 2

if [ -n "${MACOS_CERTIFICATE_NAME:-}" ]; then
  codesign \
    --sign "$MACOS_CERTIFICATE_NAME" \
    --identifier io.github.manavo.helium-sidebar --force \
    "$OUT_DMG_PATH"
  xcrun notarytool submit "$OUT_DMG_PATH" --wait \
    --keychain-profile notarytool-profile "${DMG_NOTARY_KEYCHAIN_ARGS[@]}"
  xcrun stapler staple "$OUT_DMG_PATH"
  xcrun stapler validate "$OUT_DMG_PATH"
fi
