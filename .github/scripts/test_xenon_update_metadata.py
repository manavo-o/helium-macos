"""Check ordering and the distinction between informational and install feeds."""
import base64
from pathlib import Path
import plistlib
import tempfile
import unittest
import xml.etree.ElementTree as ET

import xenon_update_metadata as metadata


class UpdateMetadataTest(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.plist = root / "Info.plist"
        self.feed = root / "appcast.xml"
        self.dmg = root / "xenon_arm64-macos.dmg"
        self.dmg.write_bytes(b"disk image")
        self.signature = base64.b64encode(bytes(64)).decode()
        self.original = {
            "CFBundleIdentifier": metadata.BUNDLE,
            "CFBundleVersion": "156.0.8078.79",
            "CFBundleShortVersionString": "0.20.3.1",
            "LSMinimumSystemVersion": "27.0",
            "SUPublicEDKey": "fixture",
        }
        self.plist.write_bytes(plistlib.dumps(self.original))

    def prepared(self, run):
        self.plist.write_bytes(plistlib.dumps(self.original))
        metadata.prepare(self.plist, run)
        return plistlib.loads(self.plist.read_bytes())

    def test_same_run_can_package_again(self):
        data = self.prepared("124")
        metadata.prepare(self.plist, "124")
        self.assertEqual(plistlib.loads(self.plist.read_bytes()), data)
        with self.assertRaises(ValueError):
            metadata.prepare(self.plist, "125")

    def test_informational_feed_cannot_offer_an_install(self):
        metadata.appcast(self.feed, self.prepared("124"), self.dmg,
                         self.signature, install=False)
        item = ET.parse(self.feed).find("./channel/item")
        self.assertIsNone(item.find("enclosure"))
        self.assertTrue(item.findtext("link").endswith("/xenon-156.0.8078.79.124"))

    def test_enclosure_is_signed_and_stale_promotion_rejected(self):
        data = self.prepared("99")
        metadata.appcast(self.feed, data, self.dmg, self.signature, install=True)
        enclosure = ET.parse(self.feed).find("./channel/item/enclosure")
        self.assertEqual(enclosure.get(f"{{{metadata.SPARKLE}}}edSignature"), self.signature)
        self.assertEqual(int(enclosure.get("length")), self.dmg.stat().st_size)
        for run in ("98", "99"):
            with self.assertRaises(ValueError):
                metadata.newer(self.prepared(run), self.feed)
        metadata.newer(self.prepared("100"), self.feed)


if __name__ == "__main__":
    unittest.main()
