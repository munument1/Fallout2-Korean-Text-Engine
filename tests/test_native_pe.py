"""Original native EXE patch code; no copyrighted game or CJK binary in CI."""
import hashlib
from pathlib import Path
import os
import struct
import unittest

import pefile
from tools.native_pe import (
    _startup_stub, native_exe, HOOK_VA, BOOT_VA,
    IAT_GETPROCADDRESS, IAT_LOADLIBRARYA, STOCK_SHA256, RPU_HRP_SHA256,
)
from tools.runtime import sfall_crc


class NativePEUnitTests(unittest.TestCase):
    def test_own_loader_points_to_our_native_dll(self):
        code = _startup_stub()
        self.assertEqual(len(code), 0x1000)
        self.assertEqual(code[0x480:0x482], b"\x9c\x60")
        self.assertIn(struct.pack("<I", IAT_LOADLIBRARYA), code)
        self.assertIn(struct.pack("<I", IAT_GETPROCADDRESS), code)
        self.assertIn(b"fallout2font.dll\x00", code)
        self.assertIn(b"InitKoreanEngine\x00", code)
        self.assertNotIn(b"fallout2font_legacy.dll", code)
        self.assertNotIn(b"FO2_UPU_CHT", code)

    def test_non_stock_input_rejected(self):
        for raw in (b"", b"MZ" + b"\0" * 4096, b"not executable"):
            with self.subTest(size=len(raw)), self.assertRaisesRegex(ValueError, "only verified stock"):
                native_exe(raw)


@unittest.skipUnless(os.environ.get("KOREAN_ENGINE_STOCK_EXE"), "Owner stock EXE not available")
class NativePEOwnerInputTests(unittest.TestCase):
    def test_exact_stock_native_patch_deterministic(self):
        src = Path(os.environ["KOREAN_ENGINE_STOCK_EXE"]).read_bytes()
        self.assertEqual(hashlib.sha256(src).hexdigest(), STOCK_SHA256)
        patch1 = native_exe(src)
        self.assertEqual(patch1, native_exe(src))
        pe = pefile.PE(data=patch1)
        self.assertEqual(pe.FILE_HEADER.NumberOfSections, 7)
        self.assertEqual(pe.sections[-1].Name.rstrip(b"\x00"), b".krinit")
        self.assertEqual(pe.OPTIONAL_HEADER.SizeOfImage, 0x300000)
        self.assertEqual(pe.OPTIONAL_HEADER.AddressOfEntryPoint, 0xe4480)
        self.assertEqual(patch1[pe.get_offset_from_rva(HOOK_VA - 0x400000):][:5],
                         b"\xe9" + struct.pack("<i", BOOT_VA - (HOOK_VA + 5)))
        self.assertNotEqual(src, patch1)
        with self.assertRaisesRegex(ValueError, "only verified stock"):
            native_exe(patch1)


@unittest.skipUnless(os.environ.get("KOREAN_ENGINE_RPU_EXE"), "Owner HRP-patched EXE unavailable")
class NativePERpuOwnerInputTests(unittest.TestCase):
    def test_rpu_bootstrap_remains_identical_when_adding_korean_section(self):
        src = Path(os.environ["KOREAN_ENGINE_RPU_EXE"]).read_bytes()
        self.assertEqual(hashlib.sha256(src).hexdigest(), RPU_HRP_SHA256)
        dst = native_exe(src)
        self.assertEqual(dst, native_exe(src))
        self.assertEqual(dst[0xD4880:0xD488A], src[0xD4880:0xD488A])
        self.assertEqual(dst[0xEE5C0:0xEE5E7], src[0xEE5C0:0xEE5E7])
        pe = pefile.PE(data=dst)
        self.assertEqual(pe.sections[-1].Name.rstrip(b"\0"), b".krinit")
        self.assertEqual(pe.FILE_HEADER.NumberOfSections, 7)
        self.assertIn(b"f2_res.dll", dst[:len(src)])
        self.assertIn(b"fallout2font.dll", dst)
        with self.assertRaisesRegex(ValueError, "only verified"):
            native_exe(dst)


if __name__ == "__main__":
    unittest.main()
