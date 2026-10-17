"""Original native EXE patch code; no copyrighted game or CJK binary in CI."""
import hashlib
from pathlib import Path
import os
import struct
import unittest

import pefile
from tools.native_pe import (
    _startup_stub, native_exe, inspect_native_exe, HOOK_VA, BOOT_VA,
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
            with self.subTest(size=len(raw)), self.assertRaises(ValueError):
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
        with self.assertRaises(ValueError):
            native_exe(patch1)

    def test_future_non_abi_update_is_accepted_without_registering_sha(self):
        original = Path(os.environ["KOREAN_ENGINE_STOCK_EXE"]).read_bytes()
        candidate = bytearray(original)
        candidate[0x51994] ^= 1  # unrelated gameplay code, no ABI hook touched
        self.assertNotEqual(hashlib.sha256(candidate).hexdigest(), STOCK_SHA256)
        compiled = native_exe(bytes(candidate))
        self.assertEqual(compiled[0x51994], candidate[0x51994])
        self.assertEqual(inspect_native_exe(bytes(candidate))["boot_va"], BOOT_VA)

    def test_future_changed_font_abi_is_rejected(self):
        original = bytearray(Path(os.environ["KOREAN_ENGINE_STOCK_EXE"]).read_bytes())
        original[0x32580] ^= 1
        with self.assertRaisesRegex(ValueError, "engine ABI differs"):
            native_exe(bytes(original))


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
        with self.assertRaises(ValueError):
            native_exe(dst)


@unittest.skipUnless(os.environ.get("KOREAN_ENGINE_NEVADA_EXE"), "Owner Nevada EXE unavailable")
class NativePENevadaInputTests(unittest.TestCase):
    def test_larger_resources_move_native_loader_without_overwriting_mod(self):
        raw = Path(os.environ["KOREAN_ENGINE_NEVADA_EXE"]).read_bytes()
        layout = inspect_native_exe(raw)
        self.assertGreater(layout["boot_va"], BOOT_VA)
        result = native_exe(raw)
        pe = pefile.PE(data=result)
        self.assertEqual(pe.sections[-1].VirtualAddress, layout["virt"])
        self.assertEqual(pe.OPTIONAL_HEADER.SizeOfImage, layout["virt"] + 0x10000)
        self.assertEqual(result[0x11FE00:len(raw)], raw[0x11FE00:])
        self.assertEqual(result[0xACAF0:0xACBB0], raw[0xACAF0:0xACBB0])


if __name__ == "__main__":
    unittest.main()
