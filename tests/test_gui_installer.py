"""Regression tests for safe installer selection and bundled runtime data."""
import tempfile
import unittest
from pathlib import Path

from tools.gui_installer import (detect_profiles, find_cjk_files,
                                 guess_profile, self_test, suggest_stock_exe)
from tools.install_engine import inspect_sfall, validate_target
from tools.runtime import sha


class GuiInstallerTests(unittest.TestCase):
    def test_bundled_assets_match_manifest(self):
        self.assertEqual(self_test(), 0)

    def test_ambiguous_identical_executables_are_not_guessed(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "fallout2.exe").write_bytes(b"verified example")
            digest = sha(b"verified example")
            manifest = {"profiles": {
                "stock": {"exe": "fallout2.exe", "original_sha256": digest},
                "rpu": {"exe": "fallout2.exe", "original_sha256": digest},
            }}
            self.assertEqual(detect_profiles(directory, manifest), ["stock", "rpu"])

    def test_cjk_folder_matches_exact_two_files(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "Fallout2.exe").write_bytes(b"known-cjk-exe")
            (directory / "fallout2font.dll").write_bytes(b"known-cjk-font")
            manifest = {
                "cjk_exe_sha256": sha(b"known-cjk-exe"),
                "legacy_font_sha256": sha(b"known-cjk-font"),
            }
            exe, font = find_cjk_files(directory, manifest)
            self.assertEqual(exe, directory / "Fallout2.exe")
            self.assertEqual(font, directory / "fallout2font.dll")
            (directory / "fallout2font.dll").write_bytes(b"unknown-font")
            self.assertEqual(find_cjk_files(directory, manifest), (None, None))

    def test_et_tu_directory_detected_without_ambiguous_guess(self):
        choices = ["stock", "rpu", "ettu"]
        self.assertEqual(guess_profile(Path("C:/Games/Fallout1in2"), choices), "ettu")
        self.assertIsNone(guess_profile(Path("C:/Games/FO2-copy"), choices))

    def test_original_exe_found_only_if_hash_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            game = base / "Sonora"
            game.mkdir()
            original = base / "fallout2.exe"
            original.write_bytes(b"verified-stock")
            manifest = {"stock_sha256": sha(b"verified-stock")}
            self.assertEqual(suggest_stock_exe(game, manifest), original)
            original.write_bytes(b"mismatched-stock")
            self.assertIsNone(suggest_stock_exe(game, manifest))

    def test_wrong_hash_returns_no_matches(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "fallout2.exe").write_bytes(b"unexpected exe")
            manifest = {"profiles": {"stock": {
                "exe": "fallout2.exe", "original_sha256": sha(b"expected exe")
            }}}
            self.assertEqual(detect_profiles(directory, manifest), [])

    def test_missing_profile_dependency_is_not_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "olympus.exe").write_bytes(b"sample")
            manifest = {"profiles": {"olympus": {
                "exe": "olympus.exe",
                "original_sha256": sha(b"sample"),
                "required_files": {"launcher.exe": sha(b"required")},
            }}}
            self.assertEqual(detect_profiles(directory, manifest), [])

    def test_stock_without_sfall_is_a_valid_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            result = inspect_sfall(target, {"official_sfall_sha256": "unused"})
            self.assertEqual(result["status"], "absent")
            self.assertIsNone(result["hash"])
            self.assertFalse(result["enabled"])
            self.assertFalse((target / "ddraw.ini").exists())

    def test_missing_sfall_dll_leaves_unrelated_ini_untouched(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            ini = target / "ddraw.ini"
            ini.write_text("old configuration", encoding="ascii")
            self.assertFalse(inspect_sfall(target, {"official_sfall_sha256": "unused"})["enabled"])
            self.assertEqual(ini.read_text(encoding="ascii"), "old configuration")

    def test_unrelated_ddraw_dll_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "ddraw.dll").write_bytes(b"not a DirectDraw DLL")
            (target / "ddraw.ini").write_text("[Main]\\n[Debugging]\\n")
            with self.assertRaisesRegex(ValueError, "Unrecognized ddraw.dll"):
                inspect_sfall(target, {"official_sfall_sha256": "unused"})

    def test_existing_ddraw_requires_matching_configuration(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp)
            (target / "ddraw.dll").write_bytes(b"not a DirectDraw DLL")
            with self.assertRaisesRegex(ValueError, "ddraw.ini"):
                inspect_sfall(target, {"official_sfall_sha256": "unused"})

    def test_original_steam_directory_is_protected(self):
        with tempfile.TemporaryDirectory() as temp:
            steam = Path(temp) / "steamapps" / "common" / "Fallout 2"
            steam.mkdir(parents=True)
            with self.assertRaisesRegex(ValueError, "Steam"):
                validate_target(steam)
            copy = Path(temp) / "FO2-copy"
            copy.mkdir()
            self.assertEqual(validate_target(copy), copy.resolve())


if __name__ == "__main__":
    unittest.main()
