"""Failure-path regression tests for the profile-free native installer.

These use synthetic bytes and mocks, never a redistributed Fallout 2 EXE.
"""
import argparse
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from tools import install_engine as engine
from tools import native_pe


_EXPORTS = (
    'InitKoreanEngine', 'InitFont', 'ClearFont', 'SelectFont',
    'GetTextWidth', 'GetTextHeight', 'TextOutput', 'TextOutputL',
    'TextOutputX', 'SplitText',
)


class NativeInstallRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.game = self.root / 'game'
        self.game.mkdir()
        self.original_exe = b'original-watcom-game'
        self.patched_exe = b'patched-korean-game'
        (self.game / 'fallout2.exe').write_bytes(self.original_exe)
        (self.game / 'fallout2.cfg').write_bytes(
            b'[system]\r\nlanguage=english\r\n')
        self.font = self.root / 'standalone.dll'
        self.font.write_bytes(b'fake-dll')
        self.args = argparse.Namespace(
            native_exe=True, standalone_font=self.font,
            cjk_exe=None, legacy_font=None, dry_run=False,
        )
        symbols = [SimpleNamespace(name=item.encode('ascii')) for item in _EXPORTS]
        self.fake_pe = SimpleNamespace(
            FILE_HEADER=SimpleNamespace(Machine=0x14c, Characteristics=0x2000),
            DIRECTORY_ENTRY_EXPORT=SimpleNamespace(symbols=symbols),
        )

    def install(self):
        with (mock.patch.object(engine.pefile, 'PE', return_value=self.fake_pe),
              mock.patch.object(engine, 'detect_native_executables',
                                return_value={'fallout2.exe': self.original_exe}),
              mock.patch.object(engine, 'detect_native_config', return_value='fallout2.cfg'),
              mock.patch.object(engine, 'inspect_sfall',
                                return_value={'enabled': False, 'status': 'absent', 'hash': None}),
              mock.patch.object(native_pe, 'native_exe', return_value=self.patched_exe)):
            return engine.install_native(self.args, self.game, {'assets': {}})

    def assert_clean_original(self):
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), self.original_exe)
        self.assertFalse((self.game / 'fallout2font.dll').exists())
        self.assertFalse((self.game / engine.BACKUP).exists())
        self.assertEqual(list(self.game.glob(engine.BACKUP + '-staging-*')), [])

    def test_install_and_restore_in_existing_steam_directory(self):
        steam = self.root / 'steamapps' / 'common' / 'Fallout 2'
        steam.parent.mkdir(parents=True)
        self.game.rename(steam)
        self.game = engine.validate_target(steam)
        saved_game = self.game / 'data' / 'SAVEGAME' / 'SLOT01' / 'SAVE.DAT'
        saved_game.parent.mkdir(parents=True)
        saved_game.write_bytes(b'existing-save-must-survive')
        before = {p.relative_to(self.game): p.read_bytes()
                  for p in self.game.rglob('*') if p.is_file()}
        self.install()
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), self.patched_exe)
        self.assertEqual((self.game / engine.BACKUP / 'fallout2.exe').read_bytes(),
                         self.original_exe)
        self.assertEqual(saved_game.read_bytes(), before[saved_game.relative_to(self.game)])
        engine.restore(engine.validate_target(steam), dry_run=False)
        for name, original in before.items():
            self.assertEqual((self.game / name).read_bytes(), original)
        self.assertFalse((self.game / 'fallout2font.dll').exists())

    def test_backup_copy_failure_leaves_no_incomplete_backup(self):
        with mock.patch.object(engine.shutil, 'copy2', side_effect=OSError('backup I/O error')):
            with self.assertRaisesRegex(OSError, 'backup I/O error'):
                self.install()
        self.assert_clean_original()
        self.install()
        engine.restore(self.game, dry_run=False)
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), self.original_exe)

    def test_second_file_failure_rolls_back_and_allows_retry(self):
        real_atomic = engine.atomic

        def failing_atomic(path, data):
            if path.name == 'fallout2font.dll':
                raise OSError('out of disk space')
            return real_atomic(path, data)

        with mock.patch.object(engine, 'atomic', side_effect=failing_atomic):
            with self.assertRaisesRegex(OSError, 'out of disk space'):
                self.install()
        self.assert_clean_original()
        self.install()
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), self.patched_exe)
        engine.restore(self.game, dry_run=False)
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), self.original_exe)

    def test_rejects_changed_executable_before_backup(self):
        changed = b'updated-during-scan'

        def changed_source(_):
            (self.game / 'fallout2.exe').write_bytes(changed)
            return self.patched_exe

        with mock.patch.object(native_pe, 'native_exe', side_effect=changed_source):
            # The generic fixture patches native_exe, so exercise this case by
            # letting that patch return the changed source through side_effect.
            with mock.patch.object(engine.pefile, 'PE', return_value=self.fake_pe):
                with mock.patch.object(engine, 'detect_native_executables',
                                       return_value={'fallout2.exe': self.original_exe}):
                    with mock.patch.object(engine, 'detect_native_config',
                                           return_value='fallout2.cfg'):
                        with mock.patch.object(engine, 'inspect_sfall', return_value={
                                'enabled': False, 'status': 'absent', 'hash': None}):
                            with self.assertRaisesRegex(ValueError,
                                                        'changed during compatibility inspection'):
                                engine.install_native(self.args, self.game, {'assets': {}})
        self.assertEqual((self.game / 'fallout2.exe').read_bytes(), changed)
        self.assertFalse((self.game / engine.BACKUP).exists())

    def test_atomic_cleans_new_temp_file_if_replace_fails(self):
        path = self.game / 'fallout2.cfg'
        original = path.read_bytes()
        with mock.patch.object(engine.os, 'replace', side_effect=OSError('rename failed')):
            with self.assertRaisesRegex(OSError, 'rename failed'):
                engine.atomic(path, b'new config')
        self.assertEqual(path.read_bytes(), original)
        self.assertFalse((self.game / 'fallout2.cfg.korean-tmp').exists())

    def test_dry_run_does_not_create_backup(self):
        self.args.dry_run = True
        report = self.install()
        self.assertEqual(report['operation'], 'install')
        self.assert_clean_original()


if __name__ == '__main__':
    unittest.main()
