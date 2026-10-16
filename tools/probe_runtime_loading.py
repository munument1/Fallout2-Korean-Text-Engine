"""Read-only investigation of possible unmodified-EXE Korean runtime loading.

This tool does NOT patch, launch, inject into or distribute any game binaries.
Use with privately held and SHA-256-verified original and CJK executables.
"""
import argparse
import hashlib
import json
from pathlib import Path

import pefile

ROOT = Path(__file__).resolve().parents[1]
MAX_PREVIEW_SPANS = 24


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def diff_spans(left, right, limit=MAX_PREVIEW_SPANS):
    """Describe byte difference locations without exposing executable bytes."""
    common = min(len(left), len(right))
    runs = []
    changed = 0
    span_count = 0
    opened = None
    for offset in range(common):
        if left[offset] != right[offset]:
            changed += 1
            if opened is None:
                opened = offset
        elif opened is not None:
            span_count += 1
            if len(runs) < limit:
                runs.append({"relative_offset": opened, "length": offset - opened})
            opened = None
    if opened is not None:
        span_count += 1
        if len(runs) < limit:
            runs.append({"relative_offset": opened, "length": common - opened})
    if len(left) != len(right):
        tail = abs(len(left) - len(right))
        changed += tail
        span_count += 1
        if len(runs) < limit:
            runs.append({"relative_offset": common, "length": tail, "unequal_size": True})
    return {"changed_bytes": changed, "span_count": span_count, "first_spans": runs}


def describe_pe(raw, label):
    """Return metadata and import names only, never byte payloads."""
    image = pefile.PE(data=raw, fast_load=True)
    try:
        image.parse_data_directories(directories=[
            pefile.DIRECTORY_ENTRY["IMAGE_DIRECTORY_ENTRY_IMPORT"],
        ])
        dlls = {}
        for entry in getattr(image, "DIRECTORY_ENTRY_IMPORT", []):
            dll_name = entry.dll.decode("ascii", errors="replace").lower()
            symbols = []
            for imported in entry.imports:
                if imported.name:
                    symbols.append(imported.name.decode("ascii", errors="replace"))
                else:
                    symbols.append("#" + str(imported.ordinal))
            dlls[dll_name] = sorted(set(symbols))
        machine = image.FILE_HEADER.Machine
        if machine != 0x14c:
            raise ValueError(label + ": requires a 32-bit x86 classic Fallout EXE")
        sections = []
        for item in image.sections:
            name = item.Name.rstrip(b"\x00").decode("ascii", errors="replace")
            sections.append({
                "name": name,
                "rva": item.VirtualAddress,
                "raw_size": item.SizeOfRawData,
                "virtual_size": item.Misc_VirtualSize,
                "raw_offset": item.PointerToRawData,
            })
        return {
            "name": label, "sha256": sha256(raw),
            "machine": "x86", "entry_rva": image.OPTIONAL_HEADER.AddressOfEntryPoint,
            "image_base": image.OPTIONAL_HEADER.ImageBase,
            "imports": dlls, "sections": sections,
        }
    finally:
        image.close()


def compare_sections(a, b, raw_a, raw_b):
    """Compare same-address sections; different layouts must not be conflated."""
    sections_a = {x["name"]: x for x in a["sections"]}
    sections_b = {x["name"]: x for x in b["sections"]}
    comparison = []
    for name in sorted(set(sections_a) | set(sections_b)):
        x, y = sections_a.get(name), sections_b.get(name)
        if x is None or y is None:
            comparison.append({"section": name, "status": "missing_from_one_executable"})
            continue
        if (x["rva"], x["raw_size"]) != (y["rva"], y["raw_size"]):
            comparison.append({"section": name, "status": "different_address_or_size",
                               "original": [x["rva"], x["raw_size"]],
                               "cjk": [y["rva"], y["raw_size"]]})
            continue
        left = raw_a[x["raw_offset"]:x["raw_offset"] + x["raw_size"]]
        right = raw_b[y["raw_offset"]:y["raw_offset"] + y["raw_size"]]
        comparison.append({"section": name, "status": "same_layout",
                           **diff_spans(left, right)})
    return comparison


def build_report(original, cjk, manifest, mod_data=None):
    expected = {"original": manifest["stock_sha256"],
                "cjk": manifest["cjk_exe_sha256"]}
    if sha256(original) != expected["original"] or sha256(cjk) != expected["cjk"]:
        raise ValueError("Input hashes do not match the known US 1.02d and CJK references.")
    base = describe_pe(original, "original")
    donor = describe_pe(cjk, "cjk")
    mod = describe_pe(mod_data, "mod") if mod_data is not None else None
    extra = {key: donor["imports"][key] for key in donor["imports"]
             if key not in base["imports"]}
    return {
        "purpose": "read-only-loader-investigation",
        "original": base,
        "cjk": donor,
        "mod": mod,
        "new_cjk_imports": extra,
        "common_import_dlls": sorted(set(base["imports"]) & set(donor["imports"])),
        "section_differences": compare_sections(base, donor, original, cjk),
        "assessment": {
            "disk_exe_unchanged": True,
            "sfall_files_unchanged": True,
            "injection_performed": False,
            "hook_implemented": False,
            "remaining": [
                "Identify verified and conflict-free entry point on original EXE",
                "Recreate Korean text renderer hooks without loading or replacing ddraw.dll",
                "Prove modified in-memory code does not collide with sfall initialization",
                "Run game startup, UI, dialogue, save/load and mod integration tests",
            ],
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original", type=Path, required=True,
                        help="Private US Fallout 2 v1.02d EXE")
    parser.add_argument("--cjk", type=Path, required=True,
                        help="Private verified FO2_UPU_CHT_v34 EXE")
    parser.add_argument("--mod", type=Path,
                        help="Optional mod executable for import comparison")
    parser.add_argument("--output", type=Path,
                        help="Optional JSON path; never provide a game directory here")
    args = parser.parse_args()
    manifest = json.loads((ROOT / "runtime-manifest.json").read_text(encoding="utf-8"))
    originals = [args.original.resolve(strict=True), args.cjk.resolve(strict=True)]
    if args.mod:
        originals.append(args.mod.resolve(strict=True))
    if args.output:
        out = args.output.resolve()
        if any(out == game or out.is_relative_to(game.parent) for game in originals):
            parser.error("Report output must be outside all source executable directories.")
    report = build_report(
        args.original.read_bytes(), args.cjk.read_bytes(), manifest,
        args.mod.read_bytes() if args.mod else None,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")
        print("Report written:", args.output)
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
