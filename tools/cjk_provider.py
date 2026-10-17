"""Experiment-only verified fetch of the third-party CJK executable.

This removes the *folder-picker* requirement, NOT the patched CJK executable
dependency. No third-party executable is included in our installer archive.
"""
import hashlib
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://raw.githubusercontent.com/NovaRain/FO2_UPU_TChinese/master/release/Fallout2.exe"
MAX_EXE_BYTES = 2 * 1024 * 1024


def download_verified_exe(destination, expected_sha256, opener=urlopen):
    """Download once into a caller-owned temporary directory, never the game folder."""
    expected = expected_sha256.lower()
    if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
        raise ValueError("Invalid pinned executable SHA-256.")
    target = Path(destination)
    if target.exists():
        raise ValueError("Refusing to overwrite an existing downloaded executable.")
    request = Request(SOURCE, headers={"User-Agent": "Fallout2-Korean-Text-Engine-Prototyping"})
    with opener(request, timeout=30) as response:
        data = response.read(MAX_EXE_BYTES + 1)
    if len(data) > MAX_EXE_BYTES:
        raise ValueError("Upstream CJK executable exceeded expected size.")
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("Upstream CJK executable hash mismatch. Installer stopped without modifying game.")
    target.write_bytes(data)
    return target
