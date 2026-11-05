#!/usr/bin/env python3
"""Check the native Swift object's link with Chromium's actual bundled linker."""
from pathlib import Path
import re
import subprocess
import tempfile

output = Path('out/Default')
ninja = (output / 'obj/chrome/chrome_framework_shared_library.ninja').read_text()
flags = next(line for line in ninja.splitlines() if line.startswith('  ldflags = '))
libs = next(line for line in ninja.splitlines() if line.startswith('  libs = '))
sdk = re.search(r'-isysroot (\S+)', flags).group(1)
swift_directory = sdk + '/usr/lib/swift'
if '-L' + swift_directory not in flags:
    raise SystemExit('Swift SDK library search path did not reach the framework link.')
if '-Wl,-rpath,/usr/lib/swift' not in flags or '-lswiftCore' not in libs:
    raise SystemExit('Swift runtime linkage did not reach the framework link.')
with tempfile.TemporaryDirectory(prefix='arc-swift-link-') as temporary:
    subprocess.run([
        '../../third_party/llvm-build/Release+Asserts/bin/clang++',
        '-shared', '-fuse-ld=lld', '--target=arm64-apple-macos',
        '-nostdlib++', '-isysroot', sdk, '-mmacos-version-min=13.0',
        '-Wl,--strict-auto-link', '-L' + swift_directory,
        '-Wl,-rpath,/usr/lib/swift',
        'gen/chrome/browser/ui/views/tabs/vertical/arc_native_swift.o',
        '-lswiftCore', '-framework', 'AppKit', '-framework', 'SwiftUI',
        '-framework', 'Combine', '-o', str(Path(temporary) / 'native.dylib'),
    ], cwd=output, check=True)
print('Native Swift object links with Chromium clang/lld and framework runtime flags.')
