#!/usr/bin/env bash
set -euo pipefail

assets="$(cd "$(dirname "$0")/assets" && pwd)"
output="$1"
stage="$(mktemp -d)"
trap 'rm -rf "$stage"' EXIT
mkdir "$stage/AppIcon.iconset"
python3 - "$assets/xenon-discharge.png" "$stage/AppIcon.iconset" <<'PYICON'
from pathlib import Path
import sys

from PIL import Image

image = Image.open(sys.argv[1]).convert("RGBA")
output = Path(sys.argv[2])
for size in (16, 32, 128, 256, 512):
    for scale, suffix in ((1, ""), (2, "@2x")):
        dimensions = (size * scale, size * scale)
        resized = image.resize(dimensions, Image.Resampling.LANCZOS)
        resized.save(output / f"icon_{size}x{size}{suffix}.png")
PYICON

iconutil -c icns "$stage/AppIcon.iconset" -o "$stage/app.icns"
xcrun actool --output-format human-readable-text --warnings --errors \
  --platform macosx --target-device mac --minimum-deployment-target 27.0 \
  --lightweight-asset-runtime-mode=enabled --app-icon AppIcon \
  --output-partial-info-plist "$stage/Info.plist" --compile "$stage" \
  "$assets/AppIcon.icon"

test -s "$stage/Assets.car"
test -s "$stage/app.icns"
install -m 644 "$stage/Assets.car" "$stage/app.icns" "$output/"
