"""Bind a clean-build checkpoint to its source and originating Actions run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/src"
MANIFEST = SOURCE / "out/Default/xenon-fresh-checkpoint.json"


def digest(path):
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_paths():
    paths = {
        "out/Default/args.gn",
        "chrome/app/theme/chromium/mac/Assets.car",
        "chrome/app/theme/chromium/mac/app.icns",
        "chrome/app/theme/chromium/BRANDING",
    }
    patches = ROOT / "patches"
    for line in (patches / "series").read_text().splitlines():
        if not line or line.startswith("#"):
            continue
        for header in (patches / line).read_text().splitlines():
            if not header.startswith(("--- ", "+++ ")):
                continue
            name = header[4:].split("\t", 1)[0].split(" ", 1)[0]
            if name == "/dev/null":
                continue
            _, _, name = name.partition("/")
            path = Path(name)
            if not name or path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Invalid patch source path: {header}")
            paths.add(name)
    return paths


def snapshot():
    return {
        "run": os.environ["GITHUB_RUN_ID"],
        "commit": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT,
                                          text=True).strip(),
        "sources": {name: digest(SOURCE / name) for name in sorted(source_paths())},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["record", "verify"])
    args = parser.parse_args()
    current = snapshot()
    if args.operation == "record":
        if MANIFEST.exists():
            raise SystemExit("Unexpected existing checkpoint audit")
        MANIFEST.write_text(json.dumps(current, sort_keys=True) + "\n")
    elif current != json.loads(MANIFEST.read_text()):
        raise SystemExit("Fresh checkpoint source, configuration, or run differs from the audit")
    print(f"Fresh checkpoint audit: {args.operation} succeeded")


if __name__ == "__main__":
    main()
