"""Regression tests for safe installer selection and bundled runtime data."""
import tempfile
import unittest
from pathlib import Path

from tools.gui_installer import detect_profiles, self_test
from tools.install_engine import validate_target
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
