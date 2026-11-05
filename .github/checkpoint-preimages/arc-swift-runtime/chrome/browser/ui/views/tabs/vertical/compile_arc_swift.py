#!/usr/bin/env python3
"""Compile the isolated macOS SwiftUI surface without changing the C++ toolchain."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument('--source', required=True)
parser.add_argument('--output', required=True)
parser.add_argument('--header', required=True)
parser.add_argument('--sdk', required=True)
parser.add_argument('--arch', required=True)
args = parser.parse_args()
Path(args.output).parent.mkdir(parents=True, exist_ok=True)
subprocess.run(['xcrun', '--sdk', 'macosx', 'swiftc', '-parse-as-library',
    '-O', '-whole-module-optimization', '-module-name', 'HeliumNativeUI',
    '-target', args.arch + '-apple-macos13.0', '-sdk', str(Path(args.sdk).resolve()),
    '-module-cache-path', str(Path(args.output).parent / 'swift-module-cache'),
    '-emit-object', args.source, '-o', args.output,
    '-emit-objc-header-path', args.header], check=True)
