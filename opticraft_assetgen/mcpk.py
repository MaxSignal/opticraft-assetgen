"""MCPK, the asset pack format OptiCraft reads (assets.pak / assets.pak.tns).

Layout, all integers big-endian:

    header   32 bytes   "MCPK", version, entry count, table offset,
                        names offset, names size, data alignment, reserved
    table    16 bytes per entry, sorted by (hash, name):
                        FNV-1a 32 of the lower-cased name, name offset,
                        data offset, data size
    names    NUL-terminated UTF-8 paths ("assets/terrain.png")
    data     each file, starting on a DATA_ALIGN boundary

The game looks a file up by the hash of its lower-cased path, so two paths that
differ only in case cannot both be stored.
"""
import struct

MAGIC = b"MCPK"
VERSION = 1
HEADER = struct.Struct(">4sIIIIIII")
ENTRY = struct.Struct(">IIII")
DATA_ALIGN = 64


def fnv1a32(text):
    value = 0x811C9DC5
    for byte in text.encode("utf-8"):
        value ^= byte
        value = (value * 0x01000193) & 0xFFFFFFFF
    return value


def _align(value, alignment):
    return (value + alignment - 1) // alignment * alignment


def write_pak(path, files):
    """Write `files`, a mapping of pak path -> bytes. Returns the file size."""
    seen = {}
    for name in files:
        lowered = name.lower()
        if lowered in seen:
            raise ValueError(f"paths differ only in case: {seen[lowered]} and {name}")
        seen[lowered] = name

    names = bytearray()
    records = []
    for name in files:
        records.append([fnv1a32(name.lower()), len(names), 0, len(files[name]), name])
        names += name.encode("utf-8") + b"\0"
    records.sort(key=lambda r: (r[0], r[4]))

    table_offset = HEADER.size
    names_offset = table_offset + len(records) * ENTRY.size
    cursor = _align(names_offset + len(names), DATA_ALIGN)
    for record in records:
        record[2] = cursor
        cursor = _align(cursor + record[3], DATA_ALIGN)

    with open(path, "wb") as out:
        out.write(HEADER.pack(MAGIC, VERSION, len(records), table_offset,
                              names_offset, len(names), DATA_ALIGN, 0))
        for hash_value, name_offset, offset, size, _ in records:
            out.write(ENTRY.pack(hash_value, name_offset, offset, size))
        out.write(bytes(names))
        for _, _, offset, _, name in records:
            out.write(b"\0" * (offset - out.tell()))
            out.write(files[name])
        out.write(b"\0" * (_align(out.tell(), DATA_ALIGN) - out.tell()))
        return out.tell()


def read_pak(path):
    """Return {pak path: bytes}; used to verify a written pak."""
    with open(path, "rb") as f:
        blob = f.read()
    magic, version, count, table_offset, names_offset, names_size, _, _ = HEADER.unpack_from(blob, 0)
    if magic != MAGIC or version != VERSION:
        raise ValueError(f"{path}: not an MCPK version {VERSION} pak")
    names = blob[names_offset:names_offset + names_size]
    files = {}
    for index in range(count):
        hash_value, name_offset, offset, size = ENTRY.unpack_from(blob, table_offset + index * ENTRY.size)
        name = names[name_offset:names.index(b"\0", name_offset)].decode("utf-8")
        if fnv1a32(name.lower()) != hash_value:
            raise ValueError(f"{path}: bad hash for {name}")
        files[name] = blob[offset:offset + size]
    return files
