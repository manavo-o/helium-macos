"""Create a Xenon candidate from an immutable upstream macOS release."""
import json
import os
from pathlib import Path
import re
import subprocess

FORK = "manavo-o/helium-macos"
UPSTREAM = "imputnet/helium-macos"
PIN = Path(".github/xenon-upstream.json")
BLOCKER = Path(".github/xenon-upstream-blocked.txt")
RELEASE_FILES = {
    "helium-chromium", "revision.txt", "downloads.ini",
    "downloads.arm64.ini", "downloads.x64.ini",
}


def command(*args, **options):
    return subprocess.run(args, check=True, **options)


def output(*args):
    return command(*args, text=True, stdout=subprocess.PIPE).stdout.strip()


def summary(message):
    print(message, flush=True)
    with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a") as stream:
        stream.write(message + "\n")


def version(tag):
    if not re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", tag):
        raise ValueError(f"Unexpected Helium tag: {tag}")
    return tuple(map(int, tag.split(".")))


def dispatch(branch, sha):
    candidate = json.loads(output("git", "show", f"{sha}:{PIN}"))
    if (branch != f"codex/helium-{candidate['tag']}" or
            output("git", "rev-parse", f"{sha}:helium-chromium") != candidate["helium_commit"]):
        raise SystemExit("The candidate branch and pinned upstream source differ.")
    if output("git", "ls-tree", sha, "--", str(BLOCKER)):
        raise SystemExit(f"{branch} needs a manual compatibility fix. See {BLOCKER}.")
    runs = json.loads(output("gh", "run", "list", "--repo", FORK, "--workflow", "build.yml",
                             "--branch", branch, "--commit", sha, "--json", "url,status,conclusion"))
    if runs:
        run = runs[0]
        summary(f"Existing candidate build: {run['url']} ({run['conclusion'] or run['status']})")
        return
    command("gh", "workflow", "run", "build.yml", "--repo", FORK, "--ref", branch,
            "-f", "xenon-fresh=true")
    summary(f"Dispatched build for [{branch}](https://github.com/{FORK}/tree/{branch}).")


def main():
    if os.environ.get("GITHUB_REPOSITORY") != FORK:
        raise SystemExit("This workflow only maintains the Xenon fork")
    latest = json.loads(output("gh", "api", f"repos/{UPSTREAM}/releases/latest"))
    tag = latest["tag_name"]
    pinned = json.loads(PIN.read_text())
    if version(tag) <= version(pinned["tag"]):
        summary(f"Xenon already tracks Helium {pinned['tag']}.")
        return

    branch = f"codex/helium-{tag}"
    remote_ref = f"refs/heads/{branch}"
    existing = output("git", "ls-remote", "origin", remote_ref)
    if existing:
        command("git", "fetch", "--no-tags", "origin", remote_ref)
        dispatch(branch, output("git", "rev-parse", "FETCH_HEAD"))
        return

    # Fetch the release tag into FETCH_HEAD without overwriting fork tags.
    command("git", "fetch", "--no-tags", f"https://github.com/{UPSTREAM}.git",
            f"refs/tags/{tag}")
    upstream = output("git", "rev-parse", "FETCH_HEAD^{commit}")
    old = pinned["macos_commit"]
    command("git", "merge-base", "--is-ancestor", old, upstream)
    upstream_gitlink = output("git", "ls-tree", upstream, "helium-chromium").split()
    if len(upstream_gitlink) != 4 or upstream_gitlink[:2] != ["160000", "commit"]:
        raise SystemExit("Helium release is missing its pinned Chromium submodule")
    helium = upstream_gitlink[2]
    if output("git", "rev-parse", "HEAD:helium-chromium") != pinned["helium_commit"]:
        raise SystemExit("The fork's submodule differs from its recorded upstream baseline")

    changed = set(output("git", "diff", "--name-only", old, upstream).splitlines())
    blocked = changed - RELEASE_FILES
    if blocked:
        BLOCKER.write_text(
            f"Review the upstream changes between {old} and {upstream}:\n" +
            "\n".join(sorted(blocked)) + "\n"
        )
    command("git", "update-index", "--cacheinfo", f"160000,{helium},helium-chromium")
    patch = subprocess.check_output(
        ["git", "diff", "--binary", old, upstream, "--", *sorted(RELEASE_FILES - {"helium-chromium"})])
    if patch and not blocked:
        applied = subprocess.run(["git", "apply", "--3way", "--index"], input=patch)
        if applied.returncode:
            command("git", "restore", "--source=HEAD", "--staged", "--worktree", "--",
                    *sorted(changed & (RELEASE_FILES - {"helium-chromium"})))
            BLOCKER.write_text(f"Reconcile the platform inputs for Helium {tag} ({upstream}).\n")
    PIN.write_text(json.dumps(dict(tag=tag, macos_commit=upstream, helium_commit=helium),
                              indent=2) + "\n")
    command("git", "add", str(PIN))
    if BLOCKER.exists():
        command("git", "add", str(BLOCKER))
    command("git", "-c", "user.name=github-actions", "-c",
            "user.email=41898282+github-actions[bot]@users.noreply.github.com",
            "commit", "-m", f"Prepare Xenon for Helium {tag}")
    sha = output("git", "rev-parse", "HEAD")
    command("git", "push", "origin", f"HEAD:{remote_ref}")
    summary(f"Created [{branch}](https://github.com/{FORK}/tree/{branch}) at {sha}.")
    dispatch(branch, sha)


if __name__ == "__main__":
    main()
