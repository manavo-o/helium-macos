"""Prepare updater metadata before signing and create a Sparkle appcast."""
import argparse
import base64
from datetime import datetime, timezone
from email.utils import format_datetime
from pathlib import Path
import plistlib
import re
import xml.etree.ElementTree as ET

BUNDLE = "io.github.manavo.helium-sidebar"
SPARKLE = "http://www.andymatuschak.org/xml-namespaces/sparkle"
RELEASES = "https://github.com/manavo-o/helium-macos/releases"
ET.register_namespace("sparkle", SPARKLE)


def prepare(path, run_id):
    data = plistlib.loads(path.read_bytes())
    if "SUPublicEDKey" not in data:
        return
    if not re.fullmatch(r"[1-9][0-9]*", run_id):
        raise ValueError("Invalid build run ID")
    build = data["CFBundleVersion"]
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+){3}", build):
        data["CFBundleVersion"] = f"{build}.{run_id}"
    elif not re.fullmatch(rf"[0-9]+(?:\.[0-9]+){{3}}\.{run_id}", build):
        raise ValueError("Expected a Chromium bundle version for this build run")
    data["SURequireSignedFeed"] = True
    data["SUVerifyUpdateBeforeExtraction"] = True
    data["SUAutomaticallyUpdate"] = False
    data["SUSignedFeedFailureExpirationInterval"] = 0
    path.write_bytes(plistlib.dumps(data, fmt=plistlib.FMT_BINARY))


def version(data):
    build = data["CFBundleVersion"]
    if (data["CFBundleIdentifier"] != BUNDLE or
            not re.fullmatch(r"[0-9]+(?:\.[0-9]+){4}", build) or
            not data.get("SURequireSignedFeed") or
            not data.get("SUVerifyUpdateBeforeExtraction")):
        raise ValueError("Disk image is missing verified Xenon updater metadata")
    return build


def appcast(path, data, dmg, signature, install):
    build = version(data)
    if len(base64.b64decode(signature, validate=True)) != 64:
        raise ValueError("Invalid archive signature")
    tag = f"xenon-{build}"
    rss = ET.Element("rss", version="2.0")
    channel = ET.SubElement(rss, "channel")
    ET.SubElement(channel, "title").text = "Xenon Updates"
    item = ET.SubElement(channel, "item")
    ET.SubElement(item, "title").text = f"Xenon {build}"
    ET.SubElement(item, "link").text = f"{RELEASES}/tag/{tag}"
    ET.SubElement(item, "pubDate").text = format_datetime(datetime.now(timezone.utc))
    ET.SubElement(item, f"{{{SPARKLE}}}version").text = build
    ET.SubElement(item, f"{{{SPARKLE}}}shortVersionString").text = data["CFBundleShortVersionString"]
    ET.SubElement(item, f"{{{SPARKLE}}}minimumSystemVersion").text = data["LSMinimumSystemVersion"]
    if install:
        ET.SubElement(item, "enclosure", {
            "url": f"{RELEASES}/download/{tag}/{dmg.name}",
            "length": str(dmg.stat().st_size),
            "type": "application/octet-stream",
            f"{{{SPARKLE}}}edSignature": signature,
        })
    ET.ElementTree(rss).write(path, encoding="utf-8", xml_declaration=True)


def newer(data, feed):
    current = tuple(map(int, version(data).split(".")))
    # Sparkle signs the XML with a leading comment. ElementTree ignores it.
    versions = ET.parse(feed).findall(f"./channel/item/{{{SPARKLE}}}version")
    if len(versions) != 1:
        raise ValueError("Expected one release in the existing Xenon feed")
    published = tuple(map(int, versions[0].text.split(".")))
    if current <= published:
        raise ValueError("The feed already offers this version or a newer one")


def main():
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("prepare", "version", "appcast", "newer"):
        command = commands.add_parser(name)
        command.add_argument("plist", type=Path)
    commands.choices["prepare"].add_argument("run_id")
    commands.choices["newer"].add_argument("feed", type=Path)
    feed = commands.choices["appcast"]
    feed.add_argument("output", type=Path)
    feed.add_argument("dmg", type=Path)
    feed.add_argument("signature")
    feed.add_argument("--install", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare(args.plist, args.run_id)
    else:
        data = plistlib.loads(args.plist.read_bytes())
        if args.command == "version":
            print(version(data))
        elif args.command == "newer":
            newer(data, args.feed)
        else:
            appcast(args.output, data, args.dmg, args.signature, args.install)


if __name__ == "__main__":
    main()
