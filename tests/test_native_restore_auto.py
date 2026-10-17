"""Regression cases for profile-free installation and safe CFG recovery."""
import json
import tempfile
import unittest
from pathlib import Path

from tools.install_engine import BACKUP, restore
from tools.runtime import put_ini, sha


class NativeRestoreTests(unittest.TestCase):
    def test_restoring_engine_preserves_gameplay_cfg_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup = root / BACKUP
            backup.mkdir()
            original = b"[system]\nlanguage=english\nvolume=20\n"
            installed = put_ini(original.decode("ascii"), "system", "language", "korean").encode("ascii")
            (backup / "fallout2.cfg").write_bytes(original)
            (root / "fallout2.cfg").write_bytes(
                b"[system]\nlanguage=korean\nvolume=83\n")
            state = {
                "before": {"fallout2.cfg": sha(original)},
                "after": {"fallout2.cfg": sha(installed)},
            }
            (backup / "manifest.json").write_text(json.dumps(state), encoding="utf-8")
            self.assertEqual(restore(root, True)["operation"], "restore")
            self.assertEqual(restore(root, False)["operation"], "restore")
            updated = (root / "fallout2.cfg").read_text("ascii")
            self.assertIn("language=english", updated)
            self.assertIn("volume=83", updated)

    def test_unsafe_restore_path_is_rejected_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup = root / BACKUP
            backup.mkdir()
            state = {
                "before": {"../unrelated.exe": None},
                "after": {"../unrelated.exe": sha(b"bad")},
            }
            (backup / "manifest.json").write_text(json.dumps(state), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Unexpected recovery path"):
                restore(root, True)


if __name__ == "__main__":
    unittest.main()
