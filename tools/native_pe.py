"""Original, donor-free Fallout 2 US 1.02d Korean bootstrap.

This writes a *new* PE section with our own startup code. No CJK EXE or
third-party font DLL is read, copied, or downloaded. The stub loads our native
fallout2font.dll and invokes the InitKoreanEngine export after game startup
reaches a verified, existing Windows API boundary.

Only exact hash-verified stock Fallout 2 US 1.02d is supported initially.
"""
import hashlib
import struct

import pefile

STOCK_SHA256 = "581c09c20fee70edc09ec412ee034e62e89cdefa13092e534ddd17d23f8163cb"
HOOK_VA = 0x4CAF22
ORIGINAL_INSTRUCTION = bytes.fromhex("a334e45100")  # mov [0x51e434],eax
BOOT_VA = 0x6F0480
IAT_LOADLIBRARYA = 0x6C020C
IAT_GETPROCADDRESS = 0x6C01FC


def _align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def _startup_stub():
    section = bytearray(0x1000)
    dll_va = 0x6F0600
    func_va = 0x6F0620
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
    jumpback = BOOT_VA + len(code)
    emit(b"\xe9" + struct.pack("<i", HOOK_VA + 5 - (jumpback + 5)))
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


def native_exe(stock):
    """Return a new executable from exact stock bytes, refusing all other input."""
    if hashlib.sha256(stock).hexdigest() != STOCK_SHA256:
        raise ValueError("Native Korean bootstrap supports only verified stock US 1.02d.")
    pe = pefile.PE(data=stock)
    if pe.FILE_HEADER.Machine != pefile.MACHINE_TYPE["IMAGE_FILE_MACHINE_I386"]:
        raise ValueError("Only Win32 x86 executable is supported.")
    if pe.OPTIONAL_HEADER.ImageBase != 0x400000 or pe.OPTIONAL_HEADER.AddressOfEntryPoint != 0xE4480:
        raise ValueError("Unexpected Fallout 2 executable layout.")
    iat = {entry.name.decode("ascii"): entry.address
           for module in pe.DIRECTORY_ENTRY_IMPORT
           if module.dll == b"KERNEL32.dll"
           for entry in module.imports if entry.name}
    if iat.get("LoadLibraryA") != IAT_LOADLIBRARYA or iat.get("GetProcAddress") != IAT_GETPROCADDRESS:
        raise ValueError("Original Win32 imports do not match bootstrap assumptions.")
    offset = pe.get_offset_from_rva(HOOK_VA - pe.OPTIONAL_HEADER.ImageBase)
    if stock[offset:offset + 5] != ORIGINAL_INSTRUCTION:
        raise ValueError("Original game startup instructions differ.")

    if pe.FILE_HEADER.NumberOfSections != 6:
        raise ValueError("Unexpected game section count.")
    sec = pe.sections[-1]
    virt = _align(sec.VirtualAddress + max(sec.Misc_VirtualSize, sec.SizeOfRawData),
                  pe.OPTIONAL_HEADER.SectionAlignment)
    physical = _align(len(stock), pe.OPTIONAL_HEADER.FileAlignment)
    if virt != 0x2F0000 or physical != 0x122800:
        raise ValueError("Not the supported PE section layout.")
    new_header_offset = pe.sections[0].get_file_offset() + len(pe.sections) * 40
    if new_header_offset + 40 > pe.OPTIONAL_HEADER.SizeOfHeaders:
        raise ValueError("No safe room for native section header.")

    result = bytearray(stock)
    result.extend(b"\0" * (physical - len(result)))
    result.extend(_startup_stub())
    header = bytearray(40)
    header[:8] = b".krinit\0"
    struct.pack_into("<IIII", header, 8, 0x1000, virt, 0x1000, physical)
    struct.pack_into("<I", header, 36, 0x60000020)  # CODE, READ, EXECUTE
    result[new_header_offset:new_header_offset + 40] = header
    struct.pack_into("<H", result, pe.FILE_HEADER.get_field_absolute_offset("NumberOfSections"), 7)
    struct.pack_into("<I", result, pe.OPTIONAL_HEADER.get_field_absolute_offset("SizeOfImage"), 0x300000)
    # Jump into our independently authored loader. The displacement doubles
    # as the versionCHI CJK-compatibility marker recognized by official sfall.
    result[offset:offset + 5] = b"\xE9" + struct.pack("<i", BOOT_VA - (HOOK_VA + 5))
    if result[offset + 1:offset + 5] != bytes.fromhex("59552200"):
        raise AssertionError("Expected sfall CJK-compatible marker not produced")
    checked = pefile.PE(data=result)
    if checked.sections[-1].Name.rstrip(b"\0") != b".krinit":
        raise ValueError("Native section missing after patch.")
    checksum_offset = checked.OPTIONAL_HEADER.get_field_absolute_offset("CheckSum")
    struct.pack_into("<I", result, checksum_offset, checked.generate_checksum())
    return bytes(result)
