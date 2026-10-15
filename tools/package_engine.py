"""Package owned adapter assets, source and installer without game/CJK binaries."""
import argparse
import json
from pathlib import Path
import zipfile
from runtime import sha

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('dist/korean-text-engine.zip'))
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'runtime-manifest.json').read_text(encoding='utf-8'))
    for name, expected in manifest['assets'].items():
        if sha((ROOT / name).read_bytes()) != expected:
            raise ValueError(f'Asset checksum mismatch: {name}')
    names = set(manifest['assets']) | {'runtime-manifest.json', 'README.md', 'LICENSE', 'requirements.txt', 'build.cmd'}
    for directory in ['src', 'tools', 'docs', 'tests']:
        names.update(p.relative_to(ROOT).as_posix() for p in (ROOT / directory).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    if any(Path(n).name.lower() in {'ddraw.dll', 'fallout2.exe', 'fallout2font_legacy.dll'} for n in names):
        raise ValueError('Third-party engine/game payload must not be distributed.')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(args.output, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            entry = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            entry.compress_type = zipfile.ZIP_DEFLATED
            entry.external_attr = 0o644 << 16
            archive.writestr(entry, (ROOT / name).read_bytes())
    print(json.dumps({'artifact': str(args.output), 'files': len(names), 'third_party_binaries': False}))


if __name__ == '__main__':
    main()
