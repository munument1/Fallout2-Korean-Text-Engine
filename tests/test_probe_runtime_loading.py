"""Read-only PE comparison tool tests; do not require copyrighted executables."""
import unittest

from tools.probe_runtime_loading import (assess_legacy_font_hooks, diff_spans,
                                         build_report, sha256)


class PEProbeTests(unittest.TestCase):
    def test_identical_bytes_have_no_spans(self):
        self.assertEqual(diff_spans(b"abc", b"abc"),
                         {"changed_bytes": 0, "span_count": 0, "first_spans": []})

    def test_disjoint_deltas(self):
        result = diff_spans(b"abcdefgh", b"abXdeYZh")
        self.assertEqual(result["changed_bytes"], 3)
        self.assertEqual(result["span_count"], 2)
        self.assertEqual(result["first_spans"], [
            {"relative_offset": 2, "length": 1},
            {"relative_offset": 5, "length": 2},
        ])

    def test_unequal_size_reported_without_contents(self):
        result = diff_spans(b"abc", b"abcXYZ")
        self.assertEqual(result["changed_bytes"], 3)
        self.assertEqual(result["first_spans"], [
            {"relative_offset": 3, "length": 3, "unequal_size": True},
        ])

    def test_preview_is_bounded(self):
        result = diff_spans(b"abcdef", b"xbydyf", limit=1)
        self.assertEqual(result["span_count"], 3)
        self.assertEqual(len(result["first_spans"]), 1)

    def test_known_render_functions_map_to_original_executable_code(self):
        description = {
            "image_base": 0x400000,
            "sections": [
                {"name": "BEGTEXT", "rva": 0x40000, "raw_size": 0xF0000,
                 "virtual_size": 0xF0000, "executable": True},
            ],
        }
        result = assess_legacy_font_hooks(description)
        self.assertEqual(len(result), 6)
        self.assertTrue(all(x["in_executable_section"] for x in result))
        self.assertTrue(all(x["verified_instruction_signature"] is False for x in result))

    def test_address_outside_executable_section_is_rejected_as_candidate(self):
        description = {"image_base": 0x400000, "sections": [
            {"name": "data", "rva": 0x40000, "raw_size": 0xF0000,
             "virtual_size": 0xF0000, "executable": False},
        ]}
        result = assess_legacy_font_hooks(description)
        self.assertFalse(any(x["in_executable_section"] for x in result))
    def test_hash_verification_rejects_nonreference_binaries(self):
        manifest = {"stock_sha256": sha256(b"private-original"),
                    "cjk_exe_sha256": sha256(b"private-cjk")}
        with self.assertRaisesRegex(ValueError, "hashes"):
            build_report(b"wrong-original", b"private-cjk", manifest)


if __name__ == "__main__":
    unittest.main()
