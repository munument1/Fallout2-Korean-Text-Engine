"""Reversible local installation of the shared Korean adapter; official sfall is read-only."""
import argparse
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
import pefile
if __package__:
    from .runtime import korean_exe, sfall_crc, sha, put_ini, decode_ini
    from .native_pe import native_exe
else:
    from runtime import korean_exe, sfall_crc, sha, put_ini, decode_ini
    from native_pe import native_exe

ROOT = Path(sys._MEIPASS) if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1]
STEAM = Path(r'C:\Games\Steam\steamapps\common\Fallout 2').resolve()
BACKUP = 'korean_engine_backup_v2'


def detect_native_executables(target):
    """Find compatible Watcom PE game images, even when they have no extension.

    Only .exe and extensionless PE candidates with the classic Watcom BEGTEXT
    section enter the native
    validator. A changed engine ABI is an error, not permission to patch just
    the other launcher and leave a partly translated installation.
    """
    try:
        from .native_pe import inspect_native_exe
    except ImportError:
        from native_pe import inspect_native_exe
    candidates = {}
    for path in sorted(Path(target).iterdir(), key=lambda item: item.name.casefold()):
        if path.suffix.casefold() not in ('.exe', '') or not path.is_file():
            continue
        if path.is_symlink():
            raise ValueError('Symlinked executable is unsupported: ' + path.name)
        if not 100_000 <= path.stat().st_size <= 20_000_000:
            continue
        raw = path.read_bytes()
        try:
            pe = pefile.PE(data=raw, fast_load=True)
        except pefile.PEFormatError:
            continue
        if not pe.sections or pe.sections[0].Name.rstrip(b'\0') != b'BEGTEXT':
            continue
        try:
            inspect_native_exe(raw)
        except ValueError as exc:
            raise ValueError(f'Incompatible game executable {path.name}: {exc}') from exc
        candidates[path.name] = raw
    if not candidates:
        raise ValueError('No compatible Fallout 2 Watcom EXE found. New engine ABIs need separate analysis.')
    return candidates


def detect_native_config(target, executable_names):
    """Determine the INI used by the game from existing files, not a mod name."""
    configs = {path.name.casefold(): path.name
               for path in Path(target).iterdir()
               if path.is_file() and path.suffix.casefold() == '.cfg' and not path.is_symlink()}
    choices = []
    for name in executable_names:
        stem = Path(name).stem
        if stem.casefold().endswith(('hr', 'hd')):
            stem = stem[:-2]
        candidate = configs.get((stem + '.cfg').casefold())
        if candidate and candidate not in choices:
            choices.append(candidate)
    if len(choices) > 1:
        # Extended sfall mods can bundle a vanilla fallout2.exe/.cfg alongside
        # their own launcher/CFG. Respect the *active* sfall ConfigFile instead
        # of guessing from a folder or game name. Reject missing/unsafe hints.
        ini = Path(target) / 'ddraw.ini'
        if ini.is_file() and not ini.is_symlink():
            text, _ = decode_ini(ini.read_bytes())
            hints = []
            active = False
            for line in text.splitlines():
                clean = line.strip()
                if not clean or clean.startswith((';', '#')):
                    continue
                if clean.startswith('['):
                    active = clean.casefold() == '[misc]'
                elif active and '=' in clean:
                    key, value = clean.split('=', 1)
                    if key.strip().casefold() == 'configfile':
                        hints.append(value.split(';', 1)[0].strip())
            if len(hints) == 1:
                import re
                hint = hints[0]
                if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\.cfg', hint, re.I):
                    match = configs.get(hint.casefold())
                    if match in choices:
                        return match
        raise ValueError('Multiple game configurations found without one verified sfall ConfigFile.')
    if choices:
        return choices[0]
    # Some Fallout 2 total conversions use an extensionless game PE and an
    # independent launcher. The game CFG then has the launcher's stem, not
    # the PE's name. One existing CFG is unambiguous without a game profile.
    if len(configs) == 1:
        return next(iter(configs.values()))
    if 'fallout2.cfg' in configs:
        return configs['fallout2.cfg']
    raise ValueError('Unable to locate the game text configuration for compatible EXE(s).')


def has_native_korean_text(target):
    """An engine hook does not imply Korean MSG files are installed.

    Forcing language=korean without the required game MSG tree can prevent
    some modded games from launching. Preserve their selected language until
    users separately install actual translated text files.
    """
    directory = checked_destination(target, 'data/text/korean')
    if not directory.is_dir():
        return False
    return any(directory.glob('game/*.msg')) or any(directory.glob('dialog/*.msg'))


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
    # Compare canonical paths: Windows temporary/short-name paths may differ
    # from their resolved spelling. Never allow symlinks, even dangling ones.
    root = Path(target).resolve(strict=True)
    path = root / name
    if path.is_symlink():
        raise ValueError(f'Symlink destination: {name}')
    if not path.resolve().is_relative_to(root):
        raise ValueError(f'Redirected destination: {name}')
    return path


def restore(target, dry_run):
    import re
    backup = target / BACKUP
    if backup.is_symlink() or not backup.is_dir():
        raise ValueError('No valid Korean engine backup directory found.')
    state = json.loads((backup / 'manifest.json').read_text(encoding='utf-8'))
    if set(state['before']) != set(state['after']):
        raise ValueError('Invalid recovery manifest.')
    allowed = {'fallout2.exe', 'Fallout2.exe', 'fallout2HR.exe', 'FSonoraDLC.exe', 'FSonora.exe', 'Nevada.exe', 'NevadaHD.exe', 'olympus.exe', 'FALLOUT2',
               'fallout2.cfg', 'Fallout2.cfg', 'Nevada.cfg', 'olympus.cfg', 'fores.cfg', 'ddraw.ini', 'f2_res.ini',
               'f2_res.dll', 'fallout2font.dll', 'fallout2font_legacy.dll', 'fallout2font.ini',
               'fonts/Galmuri9.ttf', 'fonts/Galmuri11.ttf', 'fonts/Galmuri-LICENSE.txt'}
    # Native auto-detection also supports future mod EXE/CFG filenames.
    # Keep path characters tightly constrained, disallow nested directories
    # and verify the backed-up original against the genuine Watcom ABI below.
    dynamic = {name for name in state['before'] if name not in allowed}
    for name in dynamic:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\.(?:exe|cfg)', name, flags=re.I):
            raise ValueError('Unexpected recovery path: ' + name)
    cfg_merges = {}
    for name, expected in state['after'].items():
        path = checked_destination(target, name)
        if not path.is_file():
            raise ValueError(f'Installed file changed; manual recovery needed: {name}')
        previous = state['before'][name]
        if previous is not None and sha((backup / name).read_bytes()) != previous:
            raise ValueError('Recovery file hash mismatch.')
        if name in dynamic and name.lower().endswith('.exe'):
            try:
                from .native_pe import inspect_native_exe
            except ImportError:
                from native_pe import inspect_native_exe
            inspect_native_exe((backup / name).read_bytes())
        if sha(path.read_bytes()) != expected:
            # Fallout itself updates its CFG during normal gameplay. If the
            # installer only changed language=en -> ko, undo only that setting
            # while preserving the user's intervening gameplay settings.
            if name.lower().endswith('.cfg') and previous is not None:
                old_text, old_encoding = decode_ini((backup / name).read_bytes())
                original_lang = read_ini_option(old_text, 'system', 'language')
                installed_cfg = put_ini(old_text, 'system', 'language', 'korean').encode(old_encoding)
                if original_lang is not None and sha(installed_cfg) == expected:
                    current_text, current_encoding = decode_ini(path.read_bytes())
                    if read_ini_option(current_text, 'system', 'language') == 'korean':
                        current_text = put_ini(current_text, 'system', 'language', original_lang)
                    cfg_merges[name] = current_text.encode(current_encoding)
                    continue
            raise ValueError(f'Installed file changed; manual recovery needed: {name}')
    # Preserve every prior recovery record. A user may install, restore, and
    # install again; the previous archive must never block a later restore or
    # be overwritten. Treat dangling symlinks as occupied names as well.
    archived = target / (BACKUP + '_restored')
    suffix = 2
    while archived.exists() or archived.is_symlink():
        archived = target / f'{BACKUP}_restored_{suffix}'
        suffix += 1
    if not dry_run:
        for name, expected in state['before'].items():
            path = checked_destination(target, name)
            if expected is None:
                path.unlink()
            else:
                atomic(path, cfg_merges.get(name, (backup / name).read_bytes()))
        backup.rename(archived)
    return {'operation': 'restore', 'dry_run': dry_run, 'archived_backup': archived.name}


def read_ini_option(text, section, key):
    """Read only active INI assignments (ignoring commented-out defaults)."""
    active = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith((';', '#')):
            continue
        if stripped.startswith('['):
            active = stripped.casefold() == f'[{section}]'.casefold()
        elif active and '=' in stripped:
            name, value = stripped.split('=', 1)
            if name.strip().casefold() == key.casefold():
                return value.split(';', 1)[0].strip()
    return None



def ensure_sfall_crc(text, crc, allowed_size_tokens=()):
    """Register a single CJK-compatible EXE CRC without rewriting other INI data.

    Preserve whitespace, line endings, existing entries, comments and BOM.
    Refuse ambiguous duplicate [Debugging] / ExtraCRC entries. Some extended
    sfall mods also list the *original* EXE byte lengths as decimal tokens;
    preserve only lengths verified against detected compatible EXEs when the
    existing INI explicitly enables SkipSizeCheck.
    """
    import re

    if not re.fullmatch(r'0[xX][0-9a-fA-F]{8}', crc):
        raise ValueError('Invalid Korean executable CRC.')
    lines = text.splitlines(keepends=True)
    newline = '\r\n' if '\r\n' in text else ('\n' if '\n' in text else '\r' if '\r' in text else '\r\n')
    active = False
    section_count = 0
    section_end = None
    crc_lines = []
    for index, line in enumerate(lines):
        body = line.rstrip('\r\n')
        clean = body.lstrip(' \t\ufeff')
        if not clean or clean.startswith((';', '#')):
            continue
        header = re.match(r'^\[([^\]]+)\]\s*(?:[;#].*)?$', clean)
        if header:
            if active and section_end is None:
                section_end = index
            active = header.group(1).strip().casefold() == 'debugging'
            if active:
                section_count += 1
            continue
        if active and re.match(r'^ExtraCRC\s*=', clean, re.I):
            crc_lines.append(index)
    if section_count > 1 or len(crc_lines) > 1:
        raise ValueError('Ambiguous duplicate sfall Debugging/ExtraCRC entries; refusing to edit.')
    if crc_lines:
        index = crc_lines[0]
        line = lines[index]
        body = line.rstrip('\r\n')
        eol = line[len(body):]
        match = re.match(r'^(\s*ExtraCRC\s*=\s*)([^;#]*)([;#].*)?$', body, re.I)
        if not match:
            raise ValueError('Malformed sfall ExtraCRC entry.')
        current = match.group(2)
        tokens = [item.strip() for item in current.split(',') if item.strip()]
        sizes = {str(size) for size in allowed_size_tokens}
        allow_sizes = (read_ini_option(text, 'Debugging', 'SkipSizeCheck') == '1')
        if any(not re.fullmatch(r'0[xX][0-9a-fA-F]{1,8}', item) and
               not (allow_sizes and item in sizes) for item in tokens):
            raise ValueError('Unrecognized existing sfall ExtraCRC entry; refusing to edit.')
        if any(item.lower().startswith('0x') and int(item, 16) == int(crc, 16)
               for item in tokens):
            return text
        value = current.rstrip()
        trailing = current[len(value):]
        if not value and match.group(3) and not trailing:
            # Keep an inline comment separated when the original value was empty.
            trailing = ' '
        updated = (value + ',' if value else '') + crc + trailing
        lines[index] = body[:match.start(2)] + updated + body[match.end(2):] + eol
        return ''.join(lines)
    if section_count:
        insert_at = section_end if section_end is not None else len(lines)
        if insert_at > 0 and not lines[insert_at - 1].endswith(('\r', '\n')):
            lines[insert_at - 1] += newline
        lines.insert(insert_at, 'ExtraCRC=' + crc + newline)
        return ''.join(lines)
    if text and not text.endswith(('\n', '\r')):
        text += newline
    return text + '[Debugging]' + newline + 'ExtraCRC=' + crc + newline


def inspect_sfall(target, manifest):
    """Detect an existing sfall installation, without requiring or replacing it.

    Korean rasterization uses the patched game EXE + font DLL and works as a
    separate subsystem. Existing sfall installations still need the patched
    game's CRC registered in their own INI.
    """
    dll = checked_destination(target, 'ddraw.dll')
    ini = checked_destination(target, 'ddraw.ini')
    if not dll.exists():
        return {'enabled': False, 'status': 'absent', 'hash': None}
    if not dll.is_file() or dll.is_symlink():
        raise ValueError('An unsupported ddraw.dll entry was found.')
    if not ini.is_file() or ini.is_symlink():
        raise ValueError('ddraw.dll exists, but its ddraw.ini is missing or invalid. '
                         'Keep the mod original configuration file.')
    data = dll.read_bytes()
    digest = sha(data)
    if digest == manifest['official_sfall_sha256']:
        return {'enabled': True, 'status': 'verified-4.5.1', 'hash': digest}
    # Older and mod-bundled sfall builds are not identical to our reference
    # binary. Check that the DLL is an x86 PE and the paired configuration is
    # recognizably sfall, rather than editing an unrelated DirectDraw wrapper.
    try:
        pe = pefile.PE(data=data, fast_load=True)
        if pe.FILE_HEADER.Machine != 0x14c or not (pe.FILE_HEADER.Characteristics & 0x2000):
            raise ValueError('Not an x86 sfall-style DLL.')
    except pefile.PEFormatError as exc:
        raise ValueError('Unrecognized ddraw.dll. The Korean renderer does not '
                         'require sfall; remove this file only if your mod does not '
                         'need it.') from exc
    config, _ = decode_ini(ini.read_bytes())
    sections = {line.strip().casefold() for line in config.splitlines() if line.strip().startswith('[')}
    if not {'[main]', '[debugging]'} <= sections:
        raise ValueError('An unverified ddraw.dll was found without sfall-style '
                         'configuration. Refusing to change its ddraw.ini.')
    return {'enabled': True, 'status': 'existing-unverified', 'hash': digest}


def install_native(args, target, manifest):
    """Profile-free, reversible installation for structurally compatible 1.02d engines."""
    try:
        from .native_pe import native_exe
    except ImportError:
        from native_pe import native_exe
    if getattr(args, 'cjk_exe', None) or getattr(args, 'legacy_font', None):
        raise ValueError('Independent native mode cannot accept third-party CJK files.')
    standalone = getattr(args, 'standalone_font', None)
    if not standalone:
        raise ValueError('Independent native mode requires the native font DLL.')
    font = Path(standalone).read_bytes()
    pe = pefile.PE(data=font)
    if pe.FILE_HEADER.Machine != 0x14c or not (pe.FILE_HEADER.Characteristics & 0x2000):
        raise ValueError('Expected 32-bit native Korean DLL.')
    exports = {symbol.name.decode('ascii') for symbol in pe.DIRECTORY_ENTRY_EXPORT.symbols if symbol.name}
    required = {'InitKoreanEngine', 'InitFont', 'ClearFont', 'SelectFont',
                'GetTextWidth', 'GetTextHeight', 'TextOutput', 'TextOutputL',
                'TextOutputX', 'SplitText'}
    if not required <= exports or b'fallout2font_legacy.dll' in font:
        raise ValueError('Invalid independent Korean font DLL exports.')
    original_exes = detect_native_executables(target)
    config_name = detect_native_config(target, original_exes.keys())
    payload = {name: native_exe(content) for name, content in original_exes.items()}
    for name, expected in manifest['assets'].items():
        data = (ROOT / name).read_bytes()
        if sha(data) != expected:
            raise ValueError('Bundled runtime asset hash mismatch: ' + name)
        payload[name] = data
    payload['fallout2font.dll'] = font
    sfall = inspect_sfall(target, manifest)
    sfall_path = checked_destination(target, 'ddraw.dll')
    sfall_hash = sfall['hash']
    crcs = []
    if sfall['enabled']:
        ini_path = checked_destination(target, 'ddraw.ini')
        current_ini = ini_path.read_bytes()
        text, encoding = decode_ini(current_ini)
        updated = text
        for name in original_exes:
            crc = f'0x{sfall_crc(payload[name], manifest["crc_table"]):08X}'
            if crc not in crcs:
                crcs.append(crc)
                updated = ensure_sfall_crc(updated, crc,
                                           allowed_size_tokens=(len(data) for data in original_exes.values()))
        if updated.encode(encoding) != current_ini:
            payload['ddraw.ini'] = updated.encode(encoding)
    cfg_path = checked_destination(target, config_name)
    text, encoding = decode_ini(cfg_path.read_bytes())
    has_translation = has_native_korean_text(target)
    if has_translation:
        updated_cfg = put_ini(text, 'system', 'language', 'korean').encode(encoding)
        if updated_cfg != cfg_path.read_bytes():
            payload[config_name] = updated_cfg
    backup = Path(target) / BACKUP
    if backup.exists():
        raise ValueError('Existing Korean engine backup found; restore before reinstalling.')
    for name in payload:
        path = checked_destination(target, name)
        if path.with_name(path.name + '.korean-tmp').exists():
            raise ValueError('Unfinished temporary installation found: ' + name)
    report = {
        'operation': 'install', 'profile': 'automatic-structural', 'renderer': 'native-no-cjk',
        'dry_run': args.dry_run, 'executables': sorted(original_exes),
        'config': config_name, 'sfall_status': sfall['status'], 'sfall_unchanged': True,
        'korean_translation_detected': has_translation,
        'sfall_ini_modified': 'ddraw.ini' in payload, 'sfall_crc_added': bool(crcs),
        'exe_crcs': crcs, 'files': sorted(payload),
    }
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
            atomic(checked_destination(target, name), data)
            touched.append(name)
        if sfall['enabled'] and sha(sfall_path.read_bytes()) != sfall_hash:
            raise ValueError('Existing sfall DLL changed during installation.')
    except Exception:
        for name in reversed(touched):
            path = checked_destination(target, name)
            if state['before'][name] is None:
                path.unlink()
            else:
                atomic(path, (backup / name).read_bytes())
        raise
    return report


def install(args, target):
    manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))
    if bool(getattr(args, 'native_exe', False)):
        return install_native(args, target, manifest)
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
    native_mode = bool(getattr(args, 'native_exe', False))
    if native_mode:
        if args.profile not in ('stock', 'rpu'):
            raise ValueError('Native Korean engine supports only verified stock US 1.02d and RPU.')
        if args.profile == 'rpu':
            rpu_data = checked_destination(target, 'mods/rpu.dat')
            if not rpu_data.is_file() or rpu_data.is_symlink():
                raise ValueError('RPU mod data (mods/rpu.dat) is missing.')
        # Allow exactly the verified native-compatible EXEs. A familiar name
        # or the presence of RPU mod files must never bypass the hash check.
        try:
            from .native_pe import SUPPORTED_NATIVE_SHA256
        except ImportError:
            from native_pe import SUPPORTED_NATIVE_SHA256
        if sha(original) not in SUPPORTED_NATIVE_SHA256:
            raise ValueError('Unsupported Fallout 2 EXE. Native Korean requires a verified stock US 1.02d or tested HRP-patched EXE.')
    elif sha(original) != profile['original_sha256']:
        raise ValueError('Original EXE is unsupported or already patched. Restore first.')
    sfall = inspect_sfall(target, manifest)
    sfall_path = checked_destination(target, 'ddraw.dll')
    sfall_hash = sfall['hash']
    if native_mode and not getattr(args, 'standalone_font', None):
        raise ValueError('Independent EXE patch requires the native font DLL.')
    if native_mode and (getattr(args, 'cjk_exe', None) or getattr(args, 'legacy_font', None)):
        raise ValueError('Independent EXE mode must not receive Chinese CJK binaries.')
    standalone_path = getattr(args, 'standalone_font', None)
    if standalone_path:
        standalone_data = Path(standalone_path).read_bytes()
        # The experimental adapter is independently compiled. Its interface
        # must match all CJK font exports without linking to the legacy DLL.
        binary = pefile.PE(data=standalone_data)
        if binary.FILE_HEADER.Machine != 0x14c or not (binary.FILE_HEADER.Characteristics & 0x2000):
            raise ValueError('Experimental standalone font must be an x86 DLL.')
        symbols = {entry.name.decode('ascii') for entry in binary.DIRECTORY_ENTRY_EXPORT.symbols if entry.name}
        required = {'InitFont', 'ClearFont', 'SelectFont', 'GetTextWidth', 'GetTextHeight',
                    'TextOutput', 'TextOutputL', 'TextOutputX', 'SplitText'}
        if not required <= symbols or b'fallout2font_legacy.dll' in standalone_data:
            raise ValueError('Standalone font ABI validation failed.')
        if native_mode and 'InitKoreanEngine' not in symbols:
            raise ValueError('Native game executable needs InitKoreanEngine DLL export.')
        legacy = None
    else:
        legacy = args.legacy_font.read_bytes()
        if sha(legacy) != manifest['legacy_font_sha256']:
            raise ValueError('Unsupported user-supplied legacy font DLL.')
    if native_mode:
        patched, preserved = native_exe(original), 0
    else:
        donor = args.cjk_exe.read_bytes()
        stock = original if sha(original) == manifest['stock_sha256'] else args.base_exe.read_bytes() if args.base_exe else None
        if stock is None:
            raise ValueError('--base-exe pointing to stock US 1.02d is required for a custom mod EXE.')
        patched, preserved = korean_exe(original, stock, donor, manifest)
        if sha(patched) != profile['patched_sha256']:
            raise ValueError('Derived CJK EXE does not match the verified profile.')
    # CRC is a compatibility setting for sfall; the Korean renderer does not
    # need the DLL. We still verify the derived EXE independently above.
    crc = None
    if sfall['enabled']:
        crc = f'0x{sfall_crc(patched, manifest["crc_table"]):08X}'
        if not native_mode and crc != profile['sfall_crc']:
            raise ValueError('Derived EXE CRC mismatch.')
    payload = {profile['exe']: patched}
    if native_mode and args.profile == 'rpu':
        # Standard RPU/HRP installations often launch fallout2HR.exe rather
        # than fallout2.exe. Patch both only if the two originals are identical
        # and hash verified, so game launchers cannot bypass the Korean engine.
        hires_path = checked_destination(target, 'fallout2HR.exe')
        if hires_path.exists():
            if not hires_path.is_file() or hires_path.is_symlink() or hires_path.read_bytes() != original:
                raise ValueError('RPU fallout2HR.exe differs from the verified main EXE. Refusing to change either executable.')
            payload['fallout2HR.exe'] = patched
    if legacy is not None:
        payload['fallout2font_legacy.dll'] = legacy
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
    if standalone_path:
        payload['fallout2font.dll'] = standalone_data
    sfall_crc_added = False
    if sfall['enabled']:
        # The GUI confirms which settings will change before writing.
        # CJK-modified executables are expected to use ExtraCRC in official sfall.
        ini_path = checked_destination(target, 'ddraw.ini')
        original_ini = ini_path.read_bytes()
        text, encoding = decode_ini(original_ini)
        updated = ensure_sfall_crc(text, crc)
        sfall_crc_added = updated != text
        needs_hires = ('hires_mode' in profile and
                       read_ini_option(text, 'Main', 'HiResMode') != str(profile['hires_mode']))
        if needs_hires and not getattr(args, 'configure_sfall', False):
            raise ValueError('This profile needs an additional HiResMode compatibility change. '
                             'The automatic setting only adds ExtraCRC. '
                             'Choose advanced sfall compatibility settings explicitly.')
        if needs_hires:
            updated = put_ini(updated, 'Main', 'HiResMode', str(profile['hires_mode']))
        # Never override a mod-provided TranslationsINI.
        if updated.encode(encoding) != original_ini:
            payload['ddraw.ini'] = updated.encode(encoding)
    cfg_path = checked_destination(target, profile['cfg'])
    text, encoding = decode_ini(cfg_path.read_bytes())
    payload[profile['cfg']] = put_ini(text, 'system', 'language', 'korean').encode(encoding)
    # Never overwrite RPU's menu layout just because a user left the stock
    # installer's "keep existing settings" checkbox at its default value.
    if not args.keep_menu_settings and not (native_mode and args.profile == 'rpu'):
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
              'renderer': 'native-no-cjk' if native_mode else
                          'experimental-standalone' if standalone_path else 'legacy-cjk-bridge',
              'sfall_unchanged': True, 'sfall_status': sfall['status'],
              'sfall_ini_modified': 'ddraw.ini' in payload,
              'sfall_crc_added': sfall_crc_added,
              'preserved_mod_bytes': preserved, 'exe_crc': crc,
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
        if sfall['enabled'] and sha(sfall_path.read_bytes()) != sfall_hash:
            raise ValueError('Existing sfall changed during installation.')
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
    parser.add_argument('--standalone-font', type=Path,
                        help='Experiment only: independently compiled font DLL; no Chinese legacy font DLL')
    parser.add_argument('--native-exe', action='store_true',
                        help='EXPERIMENT: structurally detect compatible Fallout 2 Watcom EXEs, no CJK binaries')
    parser.add_argument('--auto-cjk-exe', action='store_true',
                        help='Explicit opt-in: temporarily download a hash-pinned upstream CJK EXE')
    parser.add_argument('--base-exe', type=Path)
    parser.add_argument('--keep-menu-settings', action='store_true')
    parser.add_argument('--configure-sfall', action='store_true',
                        help='Explicitly configure existing sfall compatibility INI for patched EXE')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args()
    try:
        target = validate_target(args.target)
        if args.restore:
            result = restore(target, args.dry_run)
        else:
            if (not args.profile and not args.native_exe) or (not args.legacy_font and not args.standalone_font):
                parser.error('Choose exactly one font DLL mode; legacy installs also need a profile')
            if args.legacy_font and args.standalone_font:
                parser.error('Choose --legacy-font OR --standalone-font, not both')
            if args.native_exe and (args.cjk_exe or args.auto_cjk_exe or args.legacy_font or
                                    not args.standalone_font):
                parser.error('--native-exe needs --standalone-font; no profile or CJK inputs required')
            if args.auto_cjk_exe and args.cjk_exe:
                parser.error('Use --auto-cjk-exe OR --cjk-exe, not both')
            if args.native_exe:
                result = install(args, target)
            elif args.auto_cjk_exe:
                if not args.standalone_font:
                    parser.error('Experimental automatic source is allowed only with --standalone-font')
                if __package__:
                    from .cjk_provider import download_verified_exe
                else:
                    from cjk_provider import download_verified_exe
                with tempfile.TemporaryDirectory(prefix='fallout2-korean-source-') as directory:
                    manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))
                    args.cjk_exe = download_verified_exe(
                        Path(directory) / 'Fallout2.exe', manifest['cjk_exe_sha256'])
                    result = install(args, target)
            else:
                if not args.cjk_exe:
                    parser.error('Select a CJK executable or opt in to verified automatic download')
                result = install(args, target)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (OSError, ValueError, UnicodeError, pefile.PEFormatError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
