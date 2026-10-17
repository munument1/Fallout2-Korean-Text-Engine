"""Validate that the release DLL is the independent x86 Korean renderer."""
import argparse
from pathlib import Path

import pefile

EXPECTED = {
    "InitKoreanEngine", "InitFont", "ClearFont", "SelectFont",
    "GetTextWidth", "GetTextHeight", "TextOutput", "TextOutputL",
    "TextOutputX", "SplitText",
}


def verify_native_dll(path):
    path = Path(path)
    data = path.read_bytes()
    image = pefile.PE(data=data)
    if image.FILE_HEADER.Machine != 0x14c:
        raise ValueError("Native renderer must target x86.")
    if not image.FILE_HEADER.Characteristics & 0x2000:
        raise ValueError("Renderer must be a DLL.")
    exported = {
        entry.name.decode("ascii")
        for entry in image.DIRECTORY_ENTRY_EXPORT.symbols if entry.name
    }
    missing = EXPECTED - exported
    if missing:
        raise ValueError("Missing native renderer exports: " +
                         ", ".join(sorted(missing)))
    if b"fallout2font_legacy.dll" in data:
        raise ValueError("Unexpected legacy CJK renderer dependency.")
    print(f"Verified native x86 Korean font DLL: {path} ({len(data)} bytes)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dll", type=Path)
    args = parser.parse_args()
    verify_native_dll(args.dll)
