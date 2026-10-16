"""No copyrighted Fallout binaries required: conservative sfall INI editing tests."""
import unittest

from tools.install_engine import ensure_sfall_crc
from tools.runtime import decode_ini

KOREAN_CRC = "0xFCDC75E0"


class ExtraCRCEditTests(unittest.TestCase):
    def test_append_preserves_existing_crcs_comments_and_cp949_crlf(self):
        raw = ("[Main]\r\nTranslationsINI=translations\\custom.ini\r\n"
               "[Debugging]\r\n"
               "; ExtraCRC=0xBADF00D\r\n"
               "ExtraCRC=0xFC1D8E6E,0xFCF5A9F9 ; old CJK\r\n"
               "[Mod Settings]\r\n; 한글 주석\r\nSave=1\r\n").encode("cp949")
        before, encoding = decode_ini(raw)
        after = ensure_sfall_crc(before, KOREAN_CRC)
        result = after.encode(encoding)
        expected = raw.replace(b"0xFCF5A9F9 ; old CJK",
                               b"0xFCF5A9F9,0xFCDC75E0 ; old CJK")
        self.assertEqual(result, expected)
        self.assertEqual(ensure_sfall_crc(after, KOREAN_CRC), after)

    def test_mixed_case_and_leading_zero_crc_is_not_duplicated(self):
        ini = "[Debugging]\r\nExtraCRC=0Xfcdc75e0 ; same value\r\n"
        self.assertEqual(ensure_sfall_crc(ini, KOREAN_CRC), ini)

    def test_legacy_list_is_preserved_without_reformatting(self):
        ini = "[Debugging]\n  ExtraCRC = 0xE620CEBA, 0xE6C8E92D  # legacy\n"
        result = ensure_sfall_crc(ini, KOREAN_CRC)
        self.assertEqual(result, "[Debugging]\n  ExtraCRC = 0xE620CEBA, 0xE6C8E92D,0xFCDC75E0  # legacy\n")

    def test_missing_key_inserted_only_in_debugging_section(self):
        ini = "[Main]\nName=keep\n[Debugging]\nEnable=0\n[Fonts]\nSize=11\n"
        actual = ensure_sfall_crc(ini, KOREAN_CRC)
        self.assertEqual(actual, "[Main]\nName=keep\n[Debugging]\nEnable=0\n"
                                 "ExtraCRC=0xFCDC75E0\n[Fonts]\nSize=11\n")

    def test_missing_debugging_section_appended(self):
        self.assertEqual(ensure_sfall_crc("[Main]\nFoo=Bar", KOREAN_CRC),
                         "[Main]\nFoo=Bar\n[Debugging]\nExtraCRC=0xFCDC75E0\n")

    def test_empty_extra_crc_value_populated(self):
        ini = "[Debugging]\r\nExtraCRC= ; user note\r\n"
        self.assertEqual(ensure_sfall_crc(ini, KOREAN_CRC),
                         "[Debugging]\r\nExtraCRC= 0xFCDC75E0 ; user note\r\n")

    def test_utf8_bom_survives_byte_for_byte(self):
        raw = b"\xef\xbb\xbf[Debugging]\r\nExtraCRC=0x12345678\r\n"
        before, encoding = decode_ini(raw)
        actual = ensure_sfall_crc(before, KOREAN_CRC).encode(encoding)
        self.assertEqual(actual, b"\xef\xbb\xbf[Debugging]\r\n"
                                 b"ExtraCRC=0x12345678,0xFCDC75E0\r\n")

    def test_ambiguous_sections_are_rejected(self):
        for ini in ("[Debugging]\nExtraCRC=0x1\nExtraCRC=0x2\n",
                    "[Debugging]\nEnable=1\n[Debugging]\nEnable=0\n"):
            with self.subTest(ini=ini), self.assertRaisesRegex(ValueError, "Ambiguous"):
                ensure_sfall_crc(ini, KOREAN_CRC)

    def test_malformed_existing_crc_and_invalid_target_refused(self):
        with self.assertRaisesRegex(ValueError, "Unrecognized"):
            ensure_sfall_crc("[Debugging]\nExtraCRC=hello\n", KOREAN_CRC)
        with self.assertRaisesRegex(ValueError, "Invalid"):
            ensure_sfall_crc("[Debugging]\n", "wrong")

    def test_no_change_if_already_registered(self):
        ini = "[Debugging]\nExtraCRC=0xE620CEBA,0xfcdc75e0\n"
        self.assertEqual(ensure_sfall_crc(ini, KOREAN_CRC), ini)


if __name__ == "__main__":
    unittest.main()
