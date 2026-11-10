#!/usr/bin/env bash
set -euo pipefail

repo=manavo-o/helium-macos
[[ "${GITHUB_REPOSITORY:-}" == "$repo" ]]
[[ "$RUN_ID" =~ ^[0-9]+$ && "$SOURCE_SHA" =~ ^[a-f0-9]{40}$ ]]
[[ "$CHANNEL" == personal || "$CHANNEL" == test ]]
: "${XENON_UPDATE_PRIVATE_KEY:?Configure the Xenon release environment signing key}"

scripts="$(cd "$(dirname "$0")" && pwd)"
stage="$(mktemp -d)"
mount="$stage/mount"
cleanup() {
  hdiutil detach "$mount" >/dev/null 2>&1 || true
  rm -rf "$stage"
}
trap cleanup EXIT
cd "$stage"

gh api "repos/$repo/actions/runs/$RUN_ID" | jq -e --arg sha "$SOURCE_SHA" '
  .head_sha == $sha and .status == "completed" and .conclusion == "success" and
  .head_repository.full_name == "manavo-o/helium-macos" and
  (.path == ".github/workflows/arc-helium-ci.yml" or .path == ".github/workflows/build.yml") and
  (.head_branch == "arc-helium" or (.head_branch | startswith("codex/helium-")) or (.head_branch == "codex/xenon-updates"))
' >/dev/null
artifact=$(gh api --paginate "repos/$repo/actions/runs/$RUN_ID/artifacts" |
  jq -es '[.[].artifacts[] | select(.expired == false and
    (.name | test("^xenon_[0-9.]+_arm64-macos[.]dmg$")))] |
    if length == 1 then .[0].name else error("Expected one final arm64 disk image") end' -r)
gh run download "$RUN_ID" --repo "$repo" --name "$artifact"
test -s "$artifact"
hash=$(awk '$1 == "sha256:" {print $2}' "$artifact.hashes.md")
[[ "$hash" =~ ^[a-f0-9]{64}$ ]]
printf '%s  %s\n' "$hash" "$artifact" | shasum -a 256 -c -

mkdir "$mount"
hdiutil attach -readonly -nobrowse -mountpoint "$mount" "$artifact" >/dev/null
app="$mount/Xenon.app"
codesign --verify --deep --strict "$app"
test "$(lipo -archs "$app/Contents/MacOS/Xenon")" = arm64
cp "$app/Contents/Info.plist" "$stage/Xenon.plist"
hdiutil detach "$mount" >/dev/null

version=$(python3 "$scripts/xenon_update_metadata.py" version Xenon.plist)
test "${version##*.}" = "$RUN_ID"
public_key=$(/usr/libexec/PlistBuddy -c 'Print :SUPublicEDKey' Xenon.plist)
tag="xenon-$version"
feed=appcast-arm64.xml
mode=()
if [[ "$CHANNEL" == test ]]; then
  feed=appcast-test-arm64.xml
fi
if [[ "$CHANNEL" == test || "$REPLACEMENT_VERIFIED" == true ]]; then
  mode=(--install)
fi

curl --fail --silent --show-error --location --retry 3 \
  https://github.com/sparkle-project/Sparkle/releases/download/2.10.0/Sparkle-2.10.0.tar.xz \
  -o sparkle.tar.xz
printf '%s  %s\n' c2bf58aa8387266ac179357b1415d6f2635f044da8be41042af32425dae6da0c sparkle.tar.xz |
  shasum -a 256 -c -
mkdir sparkle
tar -xf sparkle.tar.xz -C sparkle
sign=$(find "$stage/sparkle" -type f -path '*/bin/sign_update' -print -quit)
test -x "$sign"
sign_with_key() {
  printf '%s\n' "$XENON_UPDATE_PRIVATE_KEY" | "$sign" --ed-key-file - "$@"
}
signature=$(sign_with_key -p "$artifact")
swift "$scripts/xenon_verify_update.swift" "$artifact" "$public_key" "$signature"

gh auth setup-git
git init --initial-branch=arc-updates "$stage/feed"
git -C feed remote add origin "https://github.com/$repo.git"
case "$(git -C feed ls-remote --heads origin refs/heads/arc-updates)" in
  '') ;;
  *)
    git -C feed fetch --depth=1 origin arc-updates
    git -C feed reset --hard FETCH_HEAD
    ;;
esac
if [[ -f "feed/$feed" ]]; then
  sign_with_key --verify "feed/$feed"
  python3 "$scripts/xenon_update_metadata.py" newer Xenon.plist "feed/$feed"
fi
python3 "$scripts/xenon_update_metadata.py" appcast Xenon.plist \
  "feed/$feed" "$artifact" "$signature" "${mode[@]}"
sign_with_key "feed/$feed"
sign_with_key --verify "feed/$feed"
git -C feed add -- "$feed"
git -C feed -c user.name=github-actions -c user.email=41898282+github-actions[bot]@users.noreply.github.com \
  commit -m "Publish $tag to the $CHANNEL feed"

printf '%s  %s\n' "$hash" "$artifact" > "$artifact.sha256"
printf '%s\n' "$signature" > "$artifact.ed25519"
if ! gh release view "$tag" --repo "$repo" >/dev/null 2>&1; then
  gh release create "$tag" "$artifact" "$artifact.sha256" "$artifact.ed25519" \
    --repo "$repo" --target "$SOURCE_SHA" --title "Xenon $version" --prerelease \
    --notes "Personal Apple Silicon build. GitHub Actions run $RUN_ID. Source $SOURCE_SHA."
fi

# Check the published asset against the approved bytes, including on retries.
test "$(gh api "repos/$repo/commits/$tag" --jq .sha)" = "$SOURCE_SHA"
gh release view "$tag" --repo "$repo" --json assets,isDraft |
  jq -e --arg asset "$artifact" --arg digest "sha256:$hash" '
    .isDraft == false and any(.assets[]; .name == $asset and .digest == $digest)' >/dev/null
git -C feed push origin HEAD:refs/heads/arc-updates
