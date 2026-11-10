"""Bind a clean-build checkpoint to its source and originating Actions run."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import zipfile

# prepare-environment copies this module to the checkout root. Imports from an
# inline Python step can select that copy before PYTHONPATH. Resolve the owning
# checkout through Git so both locations have the same meaning.
ROOT = Path(subprocess.check_output(
    ["git", "-C", str(Path(__file__).resolve().parent),
     "rev-parse", "--show-toplevel"], text=True).strip())
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


RECOVERY_ONLY_FILES = (
    ".github/scripts/github_build.sh",
    ".github/scripts/github_xenon_fresh_checkpoint.py",
    ".github/workflows/build-phase.yml",
    ".github/workflows/build.yml",
    ".github/workflows/building.yml",
    ".github/xenon-checkpoint-recovery.json",
)
CONTEXT_ONLY_PATCHES = (
    "patches/helium/macos/updater/xenon-update-consent.patch",
    "patches/helium/macos/xenon-theme-presets.patch",
)


def recovery_policy(run):
    policy = json.loads((ROOT / ".github/xenon-checkpoint-recovery.json").read_text())
    if run != policy["run"]:
        raise SystemExit("This Xenon source run has no pinned recovery artifact.")
    return policy


def download(policy):
    print(f"Downloading pinned checkpoint {policy['artifact']} into {ROOT}", flush=True)
    with tempfile.TemporaryDirectory(dir=ROOT) as stage:
        archive = Path(stage) / "checkpoint.zip"
        with archive.open("wb") as stream:
            subprocess.run([
                "gh", "api",
                f"repos/{os.environ['GITHUB_REPOSITORY']}/actions/artifacts/{policy['artifact']}/zip",
            ], stdout=stream, check=True)
        with archive.open("rb") as stream:
            actual = hashlib.file_digest(stream, "sha256").hexdigest()
        if actual != policy["sha256"]:
            raise SystemExit("Pinned Xenon artifact ZIP hash differs.")
        # Validate both members before publishing either one. Do not extract
        # arbitrary archive paths or leave a partial checkpoint after an error.
        members = ("build_src.tar.zst", "sums.txt")
        with zipfile.ZipFile(archive) as bundle:
            for name in members:
                if bundle.namelist().count(name) != 1 or bundle.getinfo(name).is_dir():
                    raise SystemExit(f"Pinned checkpoint must contain exactly one {name}.")
            for name in members:
                with bundle.open(name) as source, (Path(stage) / name).open("wb") as target:
                    shutil.copyfileobj(source, target)
        for name in members:
            (Path(stage) / name).replace(ROOT / name)
        print(f"Verified checkpoint ZIP and extracted {', '.join(members)} into {ROOT}",
              flush=True)


def download_arc(run, arch):
    path = ROOT / ".github/arc-checkpoint-delta.json"
    manifest = json.loads(path.read_text()) if path.is_file() else {}
    if (run == manifest.get("source_run") and
            manifest.get("checkpoint_artifact_id") and
            manifest.get("checkpoint_artifact_sha256")):
        download({"artifact": manifest["checkpoint_artifact_id"],
                  "sha256": manifest["checkpoint_artifact_sha256"]})
    else:
        subprocess.run(["gh", "run", "download", run, "--name",
                        "github_build_artifact_" + arch], cwd=ROOT, check=True)


def verify_recovery(policy, retained, current):
    expected = dict(current, run=policy["run"], commit=policy["commit"])
    if retained != expected:
        raise SystemExit("Recovered Xenon inputs differ from their original source audit.")
    # Allow workflow-only repairs and the two changes to blank patch context.
    subprocess.run([
        "git", "diff", "--exit-code", policy["commit"], current["commit"], "--", ".",
        *[f":(exclude){path}" for path in RECOVERY_ONLY_FILES + CONTEXT_ONLY_PATCHES],
    ], cwd=ROOT, check=True)
    for path in CONTEXT_ONLY_PATCHES:
        old = subprocess.check_output(["git", "show", f"{policy['commit']}:{path}"], cwd=ROOT)
        new = (ROOT / path).read_bytes()
        if re.sub(rb"^ $", b"", old, flags=re.MULTILINE) != re.sub(rb"^ $", b"", new, flags=re.MULTILINE):
            raise SystemExit(f"Patch content changed since the recovery build: {path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["record", "verify", "download", "download-arc"])
    args = parser.parse_args()
    source_run = os.environ.get("XENON_SOURCE_RUN")
    if args.operation == "download-arc":
        download_arc(os.environ["SOURCE_RUN"], os.environ["TARGET_ARCH"])
        return
    if args.operation == "download":
        download(recovery_policy(source_run))
        return
    current = snapshot()
    if args.operation == "record":
        if MANIFEST.exists():
            raise SystemExit("Unexpected existing checkpoint audit")
        MANIFEST.write_text(json.dumps(current, sort_keys=True) + "\n")
    elif source_run:
        verify_recovery(recovery_policy(source_run), json.loads(MANIFEST.read_text()), current)
        MANIFEST.write_text(json.dumps(current, sort_keys=True) + "\n")
    elif current != json.loads(MANIFEST.read_text()):
        raise SystemExit("Fresh checkpoint source, configuration, or run differs from the audit")
    print(f"Fresh checkpoint audit: {args.operation} succeeded")


if __name__ == "__main__":
    main()
