"""Regression tests for safe installer selection and bundled runtime data."""
import tempfile
import unittest
from pathlib import Path

from tools.gui_installer import (detect_profiles, detect_native_profile, find_cjk_files,
                                 guess_profile, self_test, suggest_stock_exe)
from tools.install_engine import (inspect_sfall, validate_target,
                                  detect_native_executables, detect_native_config)
from tools.native_pe import STOCK_SHA256, RPU_HRP_SHA256
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

    def test_native_detect_rejects_unknown_exe_with_rpu_marker(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "fallout2.exe").write_bytes(b"pretend HRP patched")
            (directory / "mods").mkdir()
            (directory / "mods" / "rpu.dat").write_bytes(b"rpu")
            self.assertIsNone(detect_native_profile(directory))

    def test_native_detect_refuses_fallout_et_tu_marker_even_with_valid_exe(self):
        with tempfile.TemporaryDirectory() as temp:
            game = Path(temp)
            (game / "mods").mkdir()
            (game / "mods" / "fallout1in2.dat").write_bytes(b"mod marker")
            self.assertIsNone(detect_native_profile(game))

    @unittest.skipUnless(__import__("os").environ.get("KOREAN_ENGINE_RPU_EXE"),
                         "Owner RPU game EXE unavailable")
    def test_real_rpu_detects_without_game_type_selection(self):
        from os import environ
        game = Path(environ["KOREAN_ENGINE_RPU_EXE"]).parent
        self.assertEqual(detect_native_profile(game), "rpu")
        with tempfile.TemporaryDirectory() as temp:
            staged = Path(temp)
            (staged / "mods").mkdir()
            (staged / "mods" / "rpu.dat").write_bytes(b"stub test marker")
            (staged / "fallout2.exe").write_bytes(Path(environ["KOREAN_ENGINE_RPU_EXE"]).read_bytes())
            (staged / "fallout2HR.exe").write_bytes(b"unexpected hrp exe")
            self.assertIsNone(detect_native_profile(staged))

    @unittest.skipUnless(__import__("os").environ.get("KOREAN_ENGINE_STOCK_EXE"),
                         "Owner stock game EXE unavailable")
    def test_real_stock_is_autodetected(self):
        from os import environ
        stock = Path(environ["KOREAN_ENGINE_STOCK_EXE"])
        self.assertEqual(sha(stock.read_bytes()), STOCK_SHA256)
        self.assertEqual(detect_native_profile(stock.parent), "stock")

    @unittest.skipUnless(__import__("os").environ.get("KOREAN_ENGINE_STOCK_EXE"),
                         "Owner original EXE unavailable")
    def test_future_mod_name_and_new_sha_still_detect_without_registration(self):
        from os import environ
        original = Path(environ["KOREAN_ENGINE_STOCK_EXE"]).read_bytes()
        updated = bytearray(original)
        updated[0x51994] ^= 1  # unmodified Watcom ABI, different EXE hash
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / "MyFutureMod_2.7.exe").write_bytes(updated)
            (folder / "MyFutureMod_2.7.cfg").write_text(
                "[system]\nlanguage=english\n", encoding="ascii")
            self.assertEqual(list(detect_native_executables(folder)), ["MyFutureMod_2.7.exe"])
            self.assertEqual(detect_native_config(folder, ["MyFutureMod_2.7.exe"]),
                             "MyFutureMod_2.7.cfg")
            # A changed core font-related function fails the *whole* folder.
            other = bytearray(original)
            other[0x32570] ^= 1
            (folder / "OtherUpdatedGame.exe").write_bytes(other)
            with self.assertRaisesRegex(ValueError, "OtherUpdatedGame.exe"):
                detect_native_executables(folder)

    @unittest.skipUnless(__import__('os').environ.get('KOREAN_ENGINE_STOCK_EXE'),
                         'Original PE fixture unavailable')
    def test_extensionless_watcom_game_and_external_launcher(self):
        from os import environ
        original = Path(environ['KOREAN_ENGINE_STOCK_EXE']).read_bytes()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'FALLOUT2').write_bytes(original)
            (folder / 'fores.exe').write_bytes(b'unrelated launcher')
            (folder / 'fores.cfg').write_text('[system]\nlanguage=english\n')
            self.assertEqual(set(detect_native_executables(folder)), {'FALLOUT2'})
            self.assertEqual(detect_native_config(folder, ['FALLOUT2']), 'fores.cfg')

    @unittest.skipUnless(__import__('os').environ.get('KOREAN_ENGINE_RESURRECTION_DIR'),
                         'Original Resurrection total conversion unavailable')
    def test_real_resurrection_launcher_not_mistaken_for_game(self):
        from os import environ
        game = Path(environ['KOREAN_ENGINE_RESURRECTION_DIR'])
        self.assertEqual(set(detect_native_executables(game)), {'FALLOUT2'})
        self.assertEqual(detect_native_config(game, ['FALLOUT2']), 'fores.cfg')

    @unittest.skipUnless(__import__("os").environ.get("KOREAN_ENGINE_RPU_EXE"),
                         "Owner RPU EXE unavailable")
    def test_native_detects_all_valid_rpu_executables_without_profile(self):
        from os import environ
        game = Path(environ["KOREAN_ENGINE_RPU_EXE"]).parent
        self.assertEqual(set(detect_native_executables(game)), {"fallout2.exe", "fallout2HR.exe"})
        self.assertEqual(detect_native_config(game, detect_native_executables(game)), "fallout2.cfg")

    @unittest.skipUnless(__import__("os").environ.get("KOREAN_ENGINE_NEVADA_EXE"),
                         "Owner Nevada EXE unavailable")
    def test_native_detects_mod_exe_and_config_without_registry(self):
        from os import environ
        game = Path(environ["KOREAN_ENGINE_NEVADA_EXE"]).parent
        self.assertEqual(set(detect_native_executables(game)), {"Nevada.exe", "NevadaHD.exe"})
        self.assertEqual(detect_native_config(game, detect_native_executables(game)), "Nevada.cfg")

    def test_multiple_config_files_choose_safe_sfall_hint(self):
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp)
            (folder / 'fallout2.cfg').write_text('[system]\nlanguage=english\n')
            (folder / 'olympus.cfg').write_text('[system]\nlanguage=english\n')
            ini = folder / 'ddraw.ini'
            ini.write_text('[Misc]\nConfigFile=olympus.cfg\n')
            names = ['fallout2.exe', 'fallout2HR.exe', 'olympus.exe']
            self.assertEqual(detect_native_config(folder, names), 'olympus.cfg')
            ini.write_text('[Misc]\nConfigFile=../evil.cfg\n')
            with self.assertRaisesRegex(ValueError, 'Multiple game configurations'):
                detect_native_config(folder, names)
            ini.write_text('[Misc]\nConfigFile=olympus.cfg\nConfigFile=fallout2.cfg\n')
            with self.assertRaisesRegex(ValueError, 'Multiple game configurations'):
                detect_native_config(folder, names)

    @unittest.skipUnless(__import__('os').environ.get('KOREAN_ENGINE_OLYMPUS_DIR'),
                         'Owner Olympus 2207 files unavailable')
    def test_olympus_real_extended_ini_and_three_exes_detect_without_profile(self):
        from os import environ
        from tools.install_engine import ensure_sfall_crc
        from tools.runtime import decode_ini
        game = Path(environ['KOREAN_ENGINE_OLYMPUS_DIR'])
        executables = detect_native_executables(game)
        self.assertEqual(set(executables), {'fallout2.exe', 'fallout2HR.exe', 'olympus.exe'})
        # The input points to the owner's read-only pre-install snapshot;
        # validate the exact original executable/INI combination.
        self.assertEqual(detect_native_config(game, executables), 'olympus.cfg')
        original = (game / 'ddraw.ini').read_bytes()
        text, _ = decode_ini(original)
        changed = ensure_sfall_crc(text, '0xA1B2C3D4',
                                   allowed_size_tokens=(1189888, 1483776))
        self.assertIn('0xA1B2C3D4', changed)
        self.assertIn('1189888,1483776', changed)

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

    @unittest.skipUnless(__import__('os').environ.get('KOREAN_ENGINE_RESURRECTION_LEGACY_DIR'),
                         'Owner Resurrection sfall 3.2a files unavailable')
    def test_resurrection_legacy_sfall_rejected_before_size_check_failure(self):
        from os import environ
        target = Path(environ['KOREAN_ENGINE_RESURRECTION_LEGACY_DIR'])
        with self.assertRaisesRegex(ValueError, 'unverified ddraw.dll'):
            inspect_sfall(target, {'official_sfall_sha256': 'unused'})

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
