"""Original, donor-free Fallout 2 US 1.02d Korean bootstrap.

This writes a *new* PE section with our own startup code. No CJK EXE or
third-party font DLL is read, copied, or downloaded. The stub loads our native
fallout2font.dll and invokes the InitKoreanEngine export after game startup
reaches a verified, existing Windows API boundary.

The original 1.02d Watcom font-manager ABI is verified using multiple
independent code/data signatures, not entire-file SHA-256. Compatible mod
updates can change unrelated scripts/resources without requiring this tool
to know the new full EXE hash. Unfamiliar engine builds are refused.
"""
import hashlib
import struct

import pefile

STOCK_SHA256 = "581c09c20fee70edc09ec412ee034e62e89cdefa13092e534ddd17d23f8163cb"
RPU_HRP_SHA256 = "048684f802b05859e2b160fa358be1b99075bf31b49a312a536645581aa16b5f"
SUPPORTED_NATIVE_SHA256 = frozenset({STOCK_SHA256, RPU_HRP_SHA256})
HOOK_VA = 0x4CAF22
ORIGINAL_INSTRUCTION = bytes.fromhex("a334e45100")  # mov [0x51e434],eax
BOOT_VA = 0x6F0480
IAT_LOADLIBRARYA = 0x6C020C
IAT_GETPROCADDRESS = 0x6C01FC

# SHA-256 of small, NON-CONTIGUOUS ABI-critical windows in owner-supplied
# Fallout 2 US 1.02d. These are hashes only; no copyrighted game code shipped.
# All inspected installed variants (stock, RPU, Et Tu, Resurrection, Sonora,
# Nevada) share these windows. Changing any Watcom ABI hook fails closed.
ABI_WINDOWS = (
    ("set-current", 0x32520, 0x325A0, "0a61818d63f14ac10942453e4a05446b1e390be80f3f60eb14b08d65c5edefdd"),
    ("word-wrap", 0xACAF0, 0xACBB0, "64877f0e82bd827ea8a01eea1b254ab31884d202a3cfffb7afe2c87a4cf94d8f"),
    ("startup", 0xBB310, 0xBB350, "e998c8f1c3321060ae41d74bdcdcbe9f0c29581619384ca93421c7aa6ab32bd8"),
    ("font-manager", 0x106C88, 0x106CB4, "91aaef7f6e90f79f11726a58ae4d41e06883407e21f03fd7b2a91541d3637898"),
    ("font-functions", 0x32600, 0x32700, "9f041a6f00b0dfc305b92053d905b34a534e129e6dc596914e82b8fe513c1e71"),
    ("draw-function", 0x326E0, 0x32760, "6031b463e3c785213bd56c482d33ab778f2e385cb29fa8a584b305795e469654"),
)


def _align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def _startup_stub(boot_va=BOOT_VA, hook_va=HOOK_VA):
    section = bytearray(0x1000)
    dll_va = boot_va + 0x180
    func_va = boot_va + 0x1A0
    code = bytearray()

    def emit(b):
        code.extend(b)

    emit(b"\x9c\x60")               # pushfd; pushad
    emit(b"\x68" + struct.pack("<I", dll_va))
    emit(b"\xff\x15" + struct.pack("<I", IAT_LOADLIBRARYA))
    emit(b"\x85\xc0")               # test eax,eax
    fail1 = len(code)
    emit(b"\x74\x00")               # jz restore
    emit(b"\x68" + struct.pack("<I", func_va))
    emit(b"\x50")
    emit(b"\xff\x15" + struct.pack("<I", IAT_GETPROCADDRESS))
    emit(b"\x85\xc0")
    fail2 = len(code)
    emit(b"\x74\x00")               # jz restore
    emit(b"\xff\xd0")               # call eax (cdecl, no params)
    restore = len(code)
    emit(b"\x61\x9d")               # popad; popfd
    emit(ORIGINAL_INSTRUCTION)
    jumpback = boot_va + len(code)
    emit(b"\xe9" + struct.pack("<i", hook_va + 5 - (jumpback + 5)))
    for branch in (fail1, fail2):
        displacement = restore - (branch + 2)
        if not -128 <= displacement <= 127:
            raise AssertionError("Out of range native bootstrap branch")
        code[branch + 1] = displacement & 255
    if len(code) > 0x180:
        raise AssertionError("Bootstrap exceeds reserved section range")
    section[0x480:0x480 + len(code)] = code
    section[0x600:0x600 + 17] = b"fallout2font.dll\x00"
    section[0x620:0x620 + 17] = b"InitKoreanEngine\x00"
    return bytes(section)


def inspect_native_exe(original):
    """Return a safe patch layout after checking independent 1.02d ABI anchors.

    Re-validate at install time; folder names and version labels are not trust
    signals. Hashes of the full EXE are intentionally not required.
    """
    try:
        pe = pefile.PE(data=original)
    except (pefile.PEFormatError, TypeError) as exc:
        raise ValueError("Not a compatible Fallout 2 PE executable.") from exc
    if pe.FILE_HEADER.Machine != pefile.MACHINE_TYPE["IMAGE_FILE_MACHINE_I386"]:
        raise ValueError("Only Win32 x86 executable is supported.")
    if pe.OPTIONAL_HEADER.ImageBase != 0x400000 or pe.OPTIONAL_HEADER.AddressOfEntryPoint != 0xE4480:
        raise ValueError("Unexpected Fallout 2 executable layout.")
    expected_sections = (
        (b"BEGTEXT", 0x10000, 0x400, 0xEE200),
        (b"DGROUP", 0x100000, 0xEE600, 0x20E00),
        (b".bss", 0x130000, 0, 0x184200),
        (b".idata", 0x2C0000, 0x10F400, 0xC00),
        (b".reloc", 0x2D0000, 0x110000, 0xFE00),
    )
    if len(pe.sections) != 6:
        raise ValueError("Expected 6-section Fallout 2 Watcom image; refusing unfamiliar game engine.")
    for index, (name, va, pointer, raw_size) in enumerate(expected_sections):
        s = pe.sections[index]
        if ((s.Name.rstrip(b"\0"), s.VirtualAddress, s.PointerToRawData,
             s.SizeOfRawData) != (name, va, pointer, raw_size)):
            raise ValueError("Core engine section layout differs; refusing an unsafe hook.")
    resources = pe.sections[-1]
    if (resources.Name.rstrip(b"\0") != b".rsrc" or
            resources.VirtualAddress != 0x2E0000 or
            resources.PointerToRawData != 0x11FE00 or
            resources.SizeOfRawData < 0x2A00 or
            resources.PointerToRawData + resources.SizeOfRawData > len(original)):
        raise ValueError("Unrecognized Fallout 2 resources section.")
    if (pe.OPTIONAL_HEADER.FileAlignment != 0x200 or
            pe.OPTIONAL_HEADER.SectionAlignment != 0x10000 or
            pe.OPTIONAL_HEADER.SizeOfHeaders != 0x400):
        raise ValueError("Unrecognized Watcom executable alignment.")
    if pe.get_overlay_data_start_offset() is not None:
        raise ValueError("Executable has extra overlay data; cannot safely append native engine.")
    for name, start, end, digest in ABI_WINDOWS:
        if len(original) < end or hashlib.sha256(original[start:end]).hexdigest() != digest:
            raise ValueError(f"Unsupported game update: {name} engine ABI differs.")
    iat = {entry.name.decode("ascii"): entry.address
           for module in pe.DIRECTORY_ENTRY_IMPORT
           if module.dll == b"KERNEL32.dll"
           for entry in module.imports if entry.name}
    if iat.get("LoadLibraryA") != IAT_LOADLIBRARYA or iat.get("GetProcAddress") != IAT_GETPROCADDRESS:
        raise ValueError("Original Win32 imports do not match bootstrap assumptions.")
    offset = pe.get_offset_from_rva(HOOK_VA - pe.OPTIONAL_HEADER.ImageBase)
    if original[offset:offset + 5] != ORIGINAL_INSTRUCTION:
        raise ValueError("Original game startup instructions differ.")

    sec = pe.sections[-1]
    virt = _align(sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData),
                  pe.OPTIONAL_HEADER.SectionAlignment)
    physical = _align(len(original), pe.OPTIONAL_HEADER.FileAlignment)
    if virt < 0x2F0000 or virt > 0xD00000:
        raise ValueError("Native PE section location is unsafe.")
    new_header_offset = pe.sections[0].get_file_offset() + len(pe.sections) * 40
    if new_header_offset + 40 > pe.OPTIONAL_HEADER.SizeOfHeaders:
        raise ValueError("No safe room for native section header.")

    boot_va = pe.OPTIONAL_HEADER.ImageBase + virt + 0x480
    return {"virt": virt, "physical": physical, "boot_va": boot_va}


def native_exe(original):
    """Patch structurally verified 1.02d-family game with an isolated loader."""
    plan = inspect_native_exe(original)
    pe = pefile.PE(data=original)
    offset = pe.get_offset_from_rva(HOOK_VA - pe.OPTIONAL_HEADER.ImageBase)
    new_header_offset = pe.sections[0].get_file_offset() + len(pe.sections) * 40
    result = bytearray(original)
    result.extend(b"\0" * (plan["physical"] - len(result)))
    result.extend(_startup_stub(boot_va=plan["boot_va"]))
    header = bytearray(40)
    header[:8] = b".krinit\0"
    struct.pack_into("<IIII", header, 8, 0x1000, plan["virt"], 0x1000, plan["physical"])
    struct.pack_into("<I", header, 36, 0x60000020)  # CODE, READ, EXECUTE
    result[new_header_offset:new_header_offset + 40] = header
    struct.pack_into("<H", result, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"), 7)
    struct.pack_into("<I", result, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"), plan["virt"] + 0x10000)
    # Jump into our independently authored loader. Classic 1.02d has the
    # familiar versionCHI-compatible displacement; enlarged resource sections
    # require a different displacement and are verified by the DLL dynamically.
    result[offset:offset + 5] = b"\xE9" + struct.pack("<i", plan["boot_va"] - (HOOK_VA + 5))
    checked = pefile.PE(data=result)
    if checked.sections[-1].Name.rstrip(b"\0") != b".krinit":
        raise ValueError("Native section missing after patch.")
    checksum_offset = checked.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum")
    struct.pack_into("<I", result, checksum_offset, checked.generate_checksum())
    return bytes(result)
