"""Integration tests use locally supplied game files; no game fixtures are distributed."""
import argparse
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from install_engine import install, restore
from runtime import sha


class AssetTests(unittest.TestCase):
    def test_verified_payload_hashes(self):
        manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))
        for name, expected in manifest['assets'].items():
            with self.subTest(asset=name):
                self.assertEqual(sha((ROOT / name).read_bytes()), expected)
        self.assertFalse((ROOT / 'ddraw.dll').exists())
        self.assertFalse((ROOT / 'fallout2font_legacy.dll').exists())


@unittest.skipUnless(os.environ.get('KOREAN_ENGINE_TEST_INPUTS'), 'Owner-supplied game inputs not configured')
class InstallerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inputs = json.loads(Path(os.environ['KOREAN_ENGINE_TEST_INPUTS']).read_text(encoding='utf-8'))
        cls.manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))

    def seed(self, target, profile):
        spec = self.manifest['profiles'][profile]
        shutil.copy2(self.inputs['originals'][profile], target / spec['exe'])
        for name in spec.get('required_files', {}):
            shutil.copy2(Path(self.inputs['originals'][profile]).parent / name, target / name)
        shutil.copy2(self.inputs['sfall_dll'], target / 'ddraw.dll')
        (target / 'ddraw.ini').write_bytes('[Main]\r\nHiResMode=1\r\n[Misc]\r\nModSetting=keep\r\n; 한글 주석\r\n[Debugging]\r\nExtraCRC=0x12345678 ; existing mod compatibility\r\n'.encode('cp949'))
        (target / spec['cfg']).write_bytes(b'[system]\r\nlanguage=english\r\nmaster_dat=../master.dat\r\n')
        (target / 'f2_res.ini').write_bytes(b'[MAIN]\r\nSCR_WIDTH=1024\r\nSCR_HEIGHT=768\r\n')
        return {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}

    def arguments(self, profile, dry_run=False):
        return argparse.Namespace(profile=profile, cjk_exe=Path(self.inputs['cjk_exe']),
                                  legacy_font=Path(self.inputs['legacy_font']), base_exe=Path(self.inputs['stock']),
                                  keep_menu_settings=False, dry_run=dry_run)

    def test_derived_runtime_matches_game_tested_builds_and_restores(self):
        for profile, spec in self.manifest['profiles'].items():
            with self.subTest(profile=profile), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                before = self.seed(target, profile)
                result = install(self.arguments(profile, dry_run=True), target)
                self.assertTrue(result['sfall_unchanged'])
                self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)
                install(self.arguments(profile), target)
                self.assertEqual(sha((target / spec['exe']).read_bytes()), spec['patched_sha256'])
                self.assertEqual((target / 'ddraw.dll').read_bytes(), before['ddraw.dll'])
                self.assertIn(b'ModSetting=keep', (target / 'ddraw.ini').read_bytes())
                self.assertIn(b'ExtraCRC=0x12345678,', (target / 'ddraw.ini').read_bytes())
                if profile != 'stock':
                    self.assertIn(b'TranslationsINI=translations\\korean.ini', (target / 'ddraw.ini').read_bytes())
                if 'hires_mode' in spec:
                    self.assertIn(f"HiResMode={spec['hires_mode']}".encode(), (target / 'ddraw.ini').read_bytes())
                for name in spec.get('required_files', {}):
                    if name in spec.get('file_patches', {}):
                        actual = (target / name).read_bytes()
                        self.assertEqual(sha(actual), spec['file_patches'][name]['patched_sha256'])
                        self.assertEqual([i for i, (a, b) in enumerate(zip(before[name], actual)) if a != b],
                                         [0x15085, 0x150a6])
                        self.assertEqual(result['patched_dependencies'][name], sha(actual))
                    else:
                        self.assertEqual((target / name).read_bytes(), before[name])
                self.assertIn('한글 주석'.encode('cp949'), (target / 'ddraw.ini').read_bytes())
                self.assertIn(b'SCR_WIDTH=1024', (target / 'f2_res.ini').read_bytes())
                self.assertIn(b'master_dat=../master.dat', (target / spec['cfg']).read_bytes())
                self.assertIn(b'language=korean', (target / spec['cfg']).read_bytes())
                with self.assertRaisesRegex(ValueError, 'already patched|original mod file'):
                    install(self.arguments(profile), target)
                restore(target, dry_run=False)
                for name, data in before.items():
                    self.assertEqual((target / name).read_bytes(), data)
                self.assertFalse((target / 'fallout2font.dll').exists())
                self.assertFalse((target / 'fallout2font_legacy.dll').exists())

    def test_unverified_sfall_and_executable_rejected_without_writes(self):
        for changed in ['ddraw.dll', 'fallout2.exe']:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                self.seed(target, 'stock')
                path = target / changed
                path.write_bytes(path.read_bytes() + b'changed')
                before = {p.name: p.read_bytes() for p in target.iterdir()}
                with self.assertRaises(ValueError):
                    install(self.arguments('stock'), target)
                self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_modified_installation_prevents_automatic_restore(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.seed(target, 'stock')
            install(self.arguments('stock'), target)
            ini = target / 'fallout2font.ini'
            ini.write_bytes(ini.read_bytes() + b'; user change\r\n')
            with self.assertRaisesRegex(ValueError, 'Installed file changed'):
                restore(target, dry_run=False)
            self.assertTrue(ini.read_bytes().endswith(b'; user change\r\n'))

    def test_sonora_external_hrp_rejects_unknown_file_without_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory)
            self.seed(target, 'sonora-dev')
            path = target / 'f2_res.dll'
            data = bytearray(path.read_bytes())
            data[0x15085] = 0x94
            path.write_bytes(data)
            before = {p.name: p.read_bytes() for p in target.iterdir()}
            with self.assertRaisesRegex(ValueError, 'original mod file'):
                install(self.arguments('sonora-dev'), target)
            self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)

    def test_resurrection_requires_original_launcher_and_preserves_mod_settings(self):
        profile = 'resurrection'
        source = Path(self.inputs['originals'][profile]).parent
        for changed in ['fores.exe', 'f2_res.dll', None]:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory() as directory:
                target = Path(directory)
                self.seed(target, profile)
                for name in ['ddraw.ini', 'fores.cfg', 'f2_res.ini']:
                    shutil.copy2(source / name, target / name)
                if changed:
                    (target / changed).write_bytes(b'unsupported')
                    before = {p.name: p.read_bytes() for p in target.iterdir()}
                    with self.assertRaisesRegex(ValueError, 'original mod file'):
                        install(self.arguments(profile), target)
                    self.assertEqual({p.name: p.read_bytes() for p in target.iterdir()}, before)
                else:
                    original = {p.name: p.read_bytes() for p in target.iterdir()}
                    install(self.arguments(profile), target)
                    cfg = (target / 'fores.cfg').read_bytes()
                    self.assertIn(b'critter_patches=fores_critter.dat', cfg)
                    self.assertIn(b'master_dat=..\\master.dat', cfg)
                    ini = (target / 'ddraw.ini').read_bytes()
                    self.assertIn(b'StartingMap=nh_cave.map', ini)
                    self.assertIn(b'ConfigFile=fores.cfg', ini)
                    self.assertIn(b'HiResMode=0', ini)
                    restore(target, dry_run=False)
                    for name, data in original.items():
                        self.assertEqual((target / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
