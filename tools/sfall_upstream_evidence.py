"""Read-only evidence generator for requesting Korean EXE recognition in sfall.

No game EXE, CJK executable or proprietary DLL is bundled or modified.
The JSON output contains only SHA-256, CRC32C, PE metadata and profile labels.
"""
import argparse
import json
from pathlib import Path

import pefile

if __package__:
    from .runtime import sha, sfall_crc
else:
    from runtime import sha, sfall_crc


ROOT = Path(__file__).resolve().parents[1]
CJK_RVA = 0xCAF23
CJK_MARKER = bytes.fromhex("59552200")


def summarize_profiles(manifest):
    """Group exact supported game builds by their recorded sfall CRC."""
    result = {}
    for profile, spec in sorted(manifest["profiles"].items()):
        crc = spec["sfall_crc"].upper().replace("0X", "0x")
        result.setdefault(crc, []).append({
            "profile": profile,
            "sha256": spec["patched_sha256"],
        })
    return result


def verify_executable(data, profile, manifest):
    """Verify owned game EXE without disclosing its contents."""
    if profile not in manifest["profiles"]:
        raise ValueError("Unsupported profile")
    spec = manifest["profiles"][profile]
    digest = sha(data)
    if digest != spec["patched_sha256"]:
        raise ValueError("EXE SHA-256 does not match the verified profile build")
    crc = "0x%08X" % sfall_crc(data, manifest["crc_table"])
    if crc.lower() != spec["sfall_crc"].lower():
        raise ValueError("Calculated CRC32C does not match sfall compatibility reference")
    pe = pefile.PE(data=data)
    try:
        if pe.FILE_HEADER.Machine != 0x14c or pe.OPTIONAL_HEADER.ImageBase != 0x400000:
            raise ValueError("Expected a classic 32-bit x86 Fallout 2 executable")
        marker_matches = pe.get_data(CJK_RVA, len(CJK_MARKER)) == CJK_MARKER
        if not marker_matches:
            raise ValueError("CJK signature expected by sfall was not preserved")
        return {
            "profile": profile,
            "sha256": digest,
            "sfall_crc32c": crc,
            "file_size": len(data),
            "sfall_existing_cjk_signature": "0x00225559",
            "sfall_versionCHI_signature_matches": marker_matches,
            "description": "Hash verified; gameplay compatibility must be tested separately.",
        }
    finally:
        pe.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="Show known profile CRCs without reading game files")
    parser.add_argument("--exe", type=Path, help="Owner-supplied Korean-patched game executable")
    parser.add_argument("--profile", help="Exact matching profile key")
    parser.add_argument("--output", type=Path, help="Write metadata-only JSON to this location")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))
    if args.list:
        result = {"verified_crc_profiles": summarize_profiles(manifest)}
    else:
        if args.exe is None or args.profile is None:
            parser.error("Provide --exe and --profile, or use --list")
        result = verify_executable(args.exe.read_bytes(), args.profile, manifest)
    document = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        outfile = args.output.resolve()
        if args.exe and outfile == args.exe.resolve():
            parser.error("Output must not overwrite the source executable")
        outfile.write_text(document, encoding="utf-8")
    print(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
