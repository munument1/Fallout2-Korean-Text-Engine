"""Regression: never inject a UTF-8 BOM into a previously BOM-free sfall INI."""
import unittest
from tools.runtime import decode_ini
from tools.install_engine import ensure_sfall_crc


class IniRoundtripTests(unittest.TestCase):
    def test_ascii_sfall_ini_is_not_rewritten_when_crc_registered(self):
        raw = b"[Main]\r\nHiResMode=0\r\n[Debugging]\r\nExtraCRC=0xFCDC75E0\r\n"
        value, encoding = decode_ini(raw)
        self.assertEqual(encoding, 'utf-8')
        self.assertEqual(ensure_sfall_crc(value, '0xFCDC75E0').encode(encoding), raw)

    def test_utf8_bom_retained_when_present(self):
        raw = b"\xef\xbb\xbf[Debugging]\r\nExtraCRC=0xFCDC75E0\r\n"
        value, encoding = decode_ini(raw)
        self.assertEqual(encoding, 'utf-8-sig')
        self.assertEqual(ensure_sfall_crc(value, '0xFCDC75E0').encode(encoding), raw)

    def test_cp949_legacy_comments_round_trip(self):
        raw = "[Debugging]\r\n; 한글\r\nExtraCRC=0xFCDC75E0\r\n".encode("cp949")
        value, encoding = decode_ini(raw)
        self.assertEqual(encoding, 'cp949')
        self.assertEqual(ensure_sfall_crc(value, '0xFCDC75E0').encode(encoding), raw)


if __name__ == '__main__':
    unittest.main()
