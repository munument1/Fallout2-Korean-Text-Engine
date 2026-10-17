"""Metadata-only tests. No copyrighted game EXEs are required."""
import json
from pathlib import Path
import unittest

from tools.sfall_upstream_evidence import summarize_profiles, verify_executable


ROOT = Path(__file__).resolve().parents[1]


class SfallProposalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))

    def test_canonical_korean_exe_has_stable_proposed_crc(self):
        crc = summarize_profiles(self.manifest)
        self.assertEqual({e["profile"] for e in crc["0xFCDC75E0"]},
                         {"stock", "rpu", "ettu", "resurrection"})
        self.assertEqual(len(crc), 5)

    def test_each_patched_exe_has_expected_sha_and_crc(self):
        crc = summarize_profiles(self.manifest)
        for group in crc.values():
            for entry in group:
                spec = self.manifest["profiles"][entry["profile"]]
                self.assertEqual(spec["patched_sha256"], entry["sha256"])
                self.assertEqual(len(entry["sha256"]), 64)

    def test_bad_executable_cannot_produce_upstream_evidence(self):
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verify_executable(b"unverified game executable", "stock", self.manifest)

    def test_unknown_profile_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Unsupported profile"):
            verify_executable(b"ignored", "nonexistent", self.manifest)


if __name__ == "__main__":
    unittest.main()
