"""Build a Korean runtime from owner-supplied game/CJK files. Never ships game code."""
import hashlib
import json
import struct
from pathlib import Path
import pefile


def sha(data):
    return hashlib.sha256(data).hexdigest()


def korean_exe(original, stock, donor, manifest):
    if sha(stock) != manifest['stock_sha256']:
        raise ValueError('Exact US 1.02d stock EXE required for comparison.')
    if sha(donor) != manifest['cjk_exe_sha256']:
        raise ValueError('Unsupported CJK EXE supplied.')
    result = bytearray(donor)
    for patch in manifest['korean_patches']:
        offset = int(patch['offset'], 16)
        before, after = bytes.fromhex(patch['before']), bytes.fromhex(patch['after'])
        if result[offset:offset + len(before)] != before or len(before) != len(after):
            raise ValueError('CJK Korean-patch signature mismatch.')
        result[offset:offset + len(after)] = after
    if sha(result) != manifest['korean_stock_sha256']:
        raise ValueError('Korean stock EXE hash mismatch.')
    bp, mp, cp = [pefile.PE(data=b) for b in (stock, original, result)]
    if mp.FILE_HEADER.Machine != 0x14c or mp.OPTIONAL_HEADER.ImageBase != 0x400000:
        raise ValueError('Only supported classic x86 executables can be patched.')
    if mp.OPTIONAL_HEADER.AddressOfEntryPoint != bp.OPTIONAL_HEADER.AddressOfEntryPoint:
        raise ValueError('Unexpected game entry point.')
    if len(mp.sections) != len(bp.sections):
        raise ValueError('Unexpected original section layout.')
    changed = 0
    for bs, ms in zip(bp.sections, mp.sections):
        if bs.Name != ms.Name or bs.VirtualAddress != ms.VirtualAddress:
            raise ValueError('Unsupported original section mapping.')
        name = bs.Name.rstrip(b'\0')
        if name in (b'BEGTEXT', b'DGROUP'):
            if (bs.SizeOfRawData, bs.PointerToRawData) != (ms.SizeOfRawData, ms.PointerToRawData):
                raise ValueError('Original game code/data section size changed.')
            for offset in range(bs.PointerToRawData, bs.PointerToRawData + bs.SizeOfRawData):
                if stock[offset] != original[offset]:
                    if result[offset] != stock[offset]:
                        raise ValueError(f'CJK/mod patch conflict at {offset:#x}.')
                    result[offset] = original[offset]
                    changed += 1
        elif name == b'.rsrc' and bs.get_data() != ms.get_data():
            new_rva = 0x300000
            alignment = cp.OPTIONAL_HEADER.FileAlignment
            new_raw = (len(result) + alignment - 1) // alignment * alignment
            resource = bytearray(ms.get_data())

            def adjust(entries):
                for entry in entries:
                    if hasattr(entry, 'directory'):
                        adjust(entry.directory.entries)
                    else:
                        data = entry.data.struct
                        index = data.get_file_offset() - ms.PointerToRawData
                        if not 0 <= index <= len(resource) - 16:
                            raise ValueError('Invalid original resource node.')
                        if not ms.VirtualAddress <= data.OffsetToData < ms.VirtualAddress + ms.SizeOfRawData:
                            raise ValueError('Resource points outside original section.')
                        struct.pack_into('<I', resource, index, data.OffsetToData - ms.VirtualAddress + new_rva)

            adjust(mp.DIRECTORY_ENTRY_RESOURCE.entries)
            result.extend(b'\0' * (new_raw - len(result)))
            result.extend(resource)
            header = cp.sections[0].get_file_offset() + len(cp.sections) * 40
            if header + 40 > cp.OPTIONAL_HEADER.SizeOfHeaders:
                raise ValueError('No room for resource section header.')
            # Keep old Watcom PE section ranges contiguous; append after .topo0.
            new_header = bytearray(40)
            new_header[:8] = b'.modrsrc'
            struct.pack_into('<IIII', new_header, 8, len(resource), new_rva, len(resource), new_raw)
            struct.pack_into('<I', new_header, 36, 0x40000040)
            result[header:header + 40] = new_header
            struct.pack_into('<H', result, cp.FILE_HEADER.get_field_absolute_offset('NumberOfSections'), len(cp.sections) + 1)
            directory = cp.OPTIONAL_HEADER.DATA_DIRECTORY[2]
            struct.pack_into('<II', result, directory.get_file_offset(), new_rva, mp.OPTIONAL_HEADER.DATA_DIRECTORY[2].Size)
            alignment = cp.OPTIONAL_HEADER.SectionAlignment
            end = new_rva + len(resource)
            struct.pack_into('<I', result, cp.OPTIONAL_HEADER.get_field_absolute_offset('SizeOfImage'), (end + alignment - 1) // alignment * alignment)
        elif name == b'.bss':
            if bs.PointerToRawData or ms.PointerToRawData or bs.Misc_VirtualSize != ms.Misc_VirtualSize:
                raise ValueError('Unexpected uninitialized-data section.')
        elif name != b'.rsrc' and bs.get_data() != ms.get_data():
            raise ValueError(f'Unhandled mod section change: {name!r}.')
    for index, (bd, md) in enumerate(zip(bp.OPTIONAL_HEADER.DATA_DIRECTORY, mp.OPTIONAL_HEADER.DATA_DIRECTORY)):
        if index != 2 and (bd.VirtualAddress, bd.Size) != (md.VirtualAddress, md.Size):
            raise ValueError('Unexpected original data directory.')

    def leaves(pe, entries, prefix=()):
        values = {}
        for entry in entries:
            key = prefix + (str(entry.name) if entry.name else entry.id,)
            if hasattr(entry, 'directory'):
                values.update(leaves(pe, entry.directory.entries, key))
            else:
                values[key] = pe.get_data(entry.data.struct.OffsetToData, entry.data.struct.Size)
        return values

    final = pefile.PE(data=result)
    if leaves(mp, mp.DIRECTORY_ENTRY_RESOURCE.entries) != leaves(final, final.DIRECTORY_ENTRY_RESOURCE.entries):
        raise ValueError('Original resource preservation failed.')
    if final.get_data(0xcaf23, 4) != bytes.fromhex('59552200'):
        raise ValueError('CJK compatibility signature lost.')
    return bytes(result), changed


def sfall_crc(data, table):
    value = 0xffffffff
    for byte in data:
        value = table[(value & 255) ^ byte] ^ (value >> 8)
    return value ^ 0xffffffff


def put_ini(text, section, key, value):
    import re
    lines, active, done, out = text.splitlines(), False, False, []
    for line in lines:
        if line.startswith('['):
            if active and not done:
                out.append(f'{key}={value}')
                done = True
            active = line.lower() == f'[{section}]'.lower()
        if active and re.match(rf'\s*{re.escape(key)}\s*=', line, re.I):
            if not done:
                out.append(f'{key}={value}')
                done = True
        else:
            out.append(line)
    if active and not done:
        out.append(f'{key}={value}')
        done = True
    if not done:
        out.extend([f'[{section}]', f'{key}={value}'])
    return '\r\n'.join(out) + '\r\n'


def decode_ini(raw):
    for encoding in ('utf-8-sig', 'cp949'):
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            pass
    raise ValueError('INI must be UTF-8 or CP949.')
