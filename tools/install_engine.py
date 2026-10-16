"""Reversible local installation of the shared Korean adapter; official sfall is read-only."""
import argparse
import json
import os
import shutil
import sys
from pathlib import Path
import pefile
if __package__:
    from .runtime import korean_exe, sfall_crc, sha, put_ini, decode_ini
else:
    from runtime import korean_exe, sfall_crc, sha, put_ini, decode_ini

ROOT = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
STEAM = Path(r'C:\Games\Steam\steamapps\common\Fallout 2').resolve()
BACKUP = 'korean_engine_backup_v2'


def validate_target(target):
    """Reject a Steam-managed original game installation; write only to a copy."""
    target = Path(target).resolve(strict=True)
    if not target.is_dir():
        raise ValueError('Select an existing game directory.')
    parts = tuple(part.casefold() for part in target.parts)
    managed = any(parts[index:index + 3] == ('steamapps', 'common', 'fallout 2')
                  for index in range(len(parts) - 2))
    if managed or target == STEAM or STEAM in target.parents:
        raise ValueError('Use an independent game copy; the original Steam installation is protected.')
    return target


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + '.korean-tmp')
    with temporary.open('xb') as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def checked_destination(target, name):
    path = target / name
    if not path.resolve().is_relative_to(target):
        raise ValueError(f'Redirected destination: {name}')
    if path.exists() and path.is_symlink():
        raise ValueError(f'Symlink destination: {name}')
    return path


def restore(target, dry_run):
    backup = target / BACKUP
    state = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if set(state['before']) != set(state['after']):
        raise ValueError('Invalid recovery manifest.')
    allowed = {'fallout2.exe', 'Fallout2.exe', 'FSonoraDLC.exe', 'Nevada.exe', 'olympus.exe', 'FALLOUT2',
               'fallout2.cfg', 'Fallout2.cfg', 'Nevada.cfg', 'olympus.cfg', 'fores.cfg', 'ddraw.ini', 'f2_res.ini',
               'f2_res.dll', 'fallout2font.dll', 'fallout2font_legacy.dll', 'fallout2font.ini',
               'fonts/Galmuri9.ttf', 'fonts/Galmuri11.ttf', 'fonts/Galmuri-LICENSE.txt'}
    if not set(state['before']) <= allowed:
        raise ValueError('Unexpected recovery path.')
    for name, expected in state['after'].items():
        path = checked_destination(target, name)
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise ValueError(f'Installed file changed; manual recovery needed: {name}')
        previous = state['before'][name]
        if previous is not None and sha((backup / name).read_bytes()) != previous:
            raise ValueError('Recovery file hash mismatch.')
    archived = target / (BACKUP + '_restored')
    if archived.exists():
        raise ValueError('Prior restored backup exists.')
    if not dry_run:
        for name, expected in state['before'].items():
            path = checked_destination(target, name)
            if expected is None:
                path.unlink()
            else:
                atomic(path, (backup / name).read_bytes())
        backup.rename(archived)
    return {'operation': 'restore', 'dry_run': dry_run}


def install(args, target):
    manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))
    if args.profile not in manifest['profiles']:
        raise ValueError('No verified executable profile for this mod.')
    profile = manifest['profiles'][args.profile]
    required_hashes = {}
    for name, expected in profile.get('required_files', {}).items():
        path = checked_destination(target, name)
        if not path.is_file() or sha(path.read_bytes()) != expected:
            raise ValueError(f'Required original mod file is missing or unsupported: {name}')
        required_hashes[name] = expected
    original_path = checked_destination(target, profile['exe'])
    original = original_path.read_bytes()
    if sha(original) != profile['original_sha256']:
        raise ValueError('Original EXE is unsupported or already patched. Restore first.')
    sfall_path = checked_destination(target, 'ddraw.dll')
    sfall_hash = sha(sfall_path.read_bytes())
    if sfall_hash != manifest['official_sfall_sha256']:
        raise ValueError('Install unmodified official sfall 4.5.1 before using this verified build.')
    donor = args.cjk_exe.read_bytes()
    legacy = args.legacy_font.read_bytes()
    if sha(legacy) != manifest['legacy_font_sha256']:
        raise ValueError('Unsupported user-supplied legacy font DLL.')
    stock = original if sha(original) == manifest['stock_sha256'] else args.base_exe.read_bytes() if args.base_exe else None
    if stock is None:
        raise ValueError('--base-exe pointing to stock US 1.02d is required for a custom mod EXE.')
    patched, preserved = korean_exe(original, stock, donor, manifest)
    if sha(patched) != profile['patched_sha256']:
        raise ValueError('Derived EXE does not match the game-tested build.')
    crc = f'0x{sfall_crc(patched, manifest["crc_table"]):08X}'
    if crc != profile['sfall_crc']:
        raise ValueError('Derived EXE CRC mismatch.')
    payload = {profile['exe']: patched, 'fallout2font_legacy.dll': legacy}
    # External HRP generates its own monitor bullet, bypassing the EXE constants.
    # Patch only a hash-verified profile dependency, with exact instruction checks.
    for name, spec in profile.get('file_patches', {}).items():
        if name not in required_hashes or name != 'f2_res.dll':
            raise ValueError('Unsupported profile dependency patch.')
        data = bytearray(checked_destination(target, name).read_bytes())
        for entry in spec['patches']:
            offset = int(entry['offset'], 16)
            before, after = bytes.fromhex(entry['before']), bytes.fromhex(entry['after'])
            if len(before) != len(after) or data[offset:offset + len(before)] != before:
                raise ValueError('External HRP bullet instruction mismatch.')
            data[offset:offset + len(after)] = after
        if sha(data) != spec['patched_sha256']:
            raise ValueError('Derived external HRP hash mismatch.')
        payload[name] = bytes(data)
    for name, expected in manifest['assets'].items():
        data = (ROOT / name).read_bytes()
        if sha(data) != expected:
            raise ValueError(f'Runtime asset hash mismatch: {name}; use the verified build.')
        payload[name] = data
    ini_path = checked_destination(target, 'ddraw.ini')
    text, encoding = decode_ini(ini_path.read_bytes())
    active, existing = False, []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith('['):
            active = stripped.lower() == '[debugging]'
        elif active and '=' in stripped and stripped.split('=', 1)[0].strip().lower() == 'extracrc':
            existing = [value.strip() for value in stripped.split('=', 1)[1].split(';', 1)[0].split(',') if value.strip()]
            break
    if crc.lower() not in [value.lower() for value in existing]:
        existing.append(crc)
    text = put_ini(text, 'Debugging', 'ExtraCRC', ','.join(existing))
    if args.profile != 'stock':
        # All new translation-only mod packages provide this file separately.
        text = put_ini(text, 'Main', 'TranslationsINI', r'translations\korean.ini')
    if 'hires_mode' in profile:
        # Profiles using an external HRP keep the integrated mode disabled.
        text = put_ini(text, 'Main', 'HiResMode', str(profile['hires_mode']))
    payload['ddraw.ini'] = text.encode(encoding)
    cfg_path = checked_destination(target, profile['cfg'])
    text, encoding = decode_ini(cfg_path.read_bytes())
    payload[profile['cfg']] = put_ini(text, 'system', 'language', 'korean').encode(encoding)
    if not args.keep_menu_settings:
        hr_path = checked_destination(target, 'f2_res.ini')
        text, encoding = decode_ini(hr_path.read_bytes()) if hr_path.exists() else ('', 'ascii')
        values = profile['menu']
        for key, value in values.items():
            text = put_ini(text, 'MAINMENU', key, str(value))
        payload['f2_res.ini'] = text.encode(encoding)
    backup = target / BACKUP
    if backup.exists():
        raise ValueError('Existing Korean engine backup found; restore before reinstalling.')
    for name in payload:
        path = checked_destination(target, name)
        if path.with_name(path.name + '.korean-tmp').exists():
            raise ValueError('Unfinished temporary installation file found.')
    report = {'operation': 'install', 'profile': args.profile, 'dry_run': args.dry_run,
              'sfall_unchanged': True, 'preserved_mod_bytes': preserved, 'exe_crc': crc,
              'preserved_original_files': {name: value for name, value in required_hashes.items() if name not in payload},
              'patched_dependencies': {name: spec['patched_sha256'] for name, spec in profile.get('file_patches', {}).items()},
              'files': sorted(payload)}
    if args.dry_run:
        return report
    backup.mkdir()
    state = {'before': {}, 'after': {name: sha(data) for name, data in payload.items()}}
    for name in payload:
        path = checked_destination(target, name)
        state['before'][name] = sha(path.read_bytes()) if path.exists() else None
        if path.exists():
            destination = backup / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, destination)
    (backup / 'manifest.json').write_text(json.dumps(state, indent=2), encoding='utf-8')
    touched = []
    try:
        for name, data in payload.items():
            atomic(target / name, data)
            touched.append(name)
        if sha(sfall_path.read_bytes()) != sfall_hash:
            raise ValueError('Official sfall changed during installation.')
        for name, expected in required_hashes.items():
            if sha((target / name).read_bytes()) != state['after'].get(name, expected):
                raise ValueError(f'Original mod file changed during installation: {name}')
    except Exception:
        for name in reversed(touched):
            if state['before'][name] is None:
                (target / name).unlink()
            else:
                atomic(target / name, (backup / name).read_bytes())
        raise
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('target', type=Path)
    parser.add_argument('--profile', choices=['stock', 'rpu', 'ettu', 'sonora', 'sonora-dev', 'nevada', 'olympus', 'resurrection'])
    parser.add_argument('--cjk-exe', type=Path)
    parser.add_argument('--legacy-font', type=Path)
    parser.add_argument('--base-exe', type=Path)
    parser.add_argument('--keep-menu-settings', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    try:
        target = validate_target(args.target)
        if args.restore:
            result = restore(target, args.dry_run)
        else:
            if not all([args.profile, args.cjk_exe, args.legacy_font]):
                parser.error('--profile, --cjk-exe and --legacy-font are required for installation')
            result = install(args, target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, pefile.PEFormatError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
