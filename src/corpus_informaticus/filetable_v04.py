"""
CIVD v0.4 file table

This module defines a simple file table structure used by CIVD v0.4 and
extended by v0.5. It supports:

- CivdFileEntryV04: one virtual file inside the capsule
- CivdFileTableV04: a list of entries with (de)serialization helpers
- build_file_table_from_file_list: helper used by v0.4/v0.5 codecs
- demo_roundtrip(): quick self-test
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple
import struct


# ---------------------------------------------------------------------------
# Binary layout
#
# We keep this intentionally simple and self-contained.
#
# filetable_body:
#   u32 entry_count
#   repeat entry_count times:
#       u16 name_len
#       bytes[name_len] utf-8 name
#       u16 mime
#       u16 flags
#       u32 offset
#       u32 size
#       u32 checksum
#
# filetable_with_length:
#   u32 table_body_length
#   bytes[table_body_length] filetable_body
# ---------------------------------------------------------------------------

_TABLE_COUNT_STRUCT = struct.Struct("<I")   # entry_count
_TABLE_LENGTH_STRUCT = struct.Struct("<I")  # table_body_length
_ENTRY_META_STRUCT = struct.Struct("<H H I I I")
# fields: mime (u16), flags (u16), offset (u32), size (u32), checksum (u32)


@dataclass
class CivdFileEntryV04:
    """
    One file entry inside a CIVD v0.4 file table.
    """
    name: str
    mime: int          # 1 = generic / application/octet-stream
    offset: int        # byte offset inside the logical data region
    size: int          # size in bytes
    flags: int = 0     # reserved
    checksum: int = 0  # reserved (CRC32 or similar in future)


@dataclass
class CivdFileTableV04:
    """
    File table: a collection of CivdFileEntryV04 entries.
    """
    entries: List[CivdFileEntryV04]

    # ---------------------- serialization ----------------------

    def to_bytes(self) -> bytes:
        """
        Serialize table to raw bytes (WITHOUT the outer length prefix).
        """
        parts: List[bytes] = []
        # number of entries
        parts.append(_TABLE_COUNT_STRUCT.pack(len(self.entries)))

        for entry in self.entries:
            name_bytes = entry.name.encode("utf-8")
            if len(name_bytes) > 0xFFFF:
                raise ValueError(f"File name too long for v0.4 table: {entry.name}")

            # name length + name bytes
            parts.append(struct.pack("<H", len(name_bytes)))
            parts.append(name_bytes)

            # fixed metadata: mime, flags, offset, size, checksum
            parts.append(
                _ENTRY_META_STRUCT.pack(
                    int(entry.mime),
                    int(entry.flags),
                    int(entry.offset),
                    int(entry.size),
                    int(entry.checksum),
                )
            )

        return b"".join(parts)

    def to_bytes_with_length(self) -> bytes:
        """
        Serialize table with a leading u32 length so parsers can skip it.
        Layout: [u32 body_length][body_bytes...]
        """
        body = self.to_bytes()
        return _TABLE_LENGTH_STRUCT.pack(len(body)) + body

    # ---------------------- deserialization ----------------------

    @classmethod
    def from_bytes(cls, buf: bytes, offset: int = 0) -> Tuple["CivdFileTableV04", int]:
        """
        Parse a file table body from `buf[offset:]`, WITHOUT length prefix.

        Returns:
            (table, bytes_consumed)
        """
        pos = offset

        if len(buf) - pos < _TABLE_COUNT_STRUCT.size:
            raise ValueError("Buffer too short for file table header")

        (entry_count,) = _TABLE_COUNT_STRUCT.unpack_from(buf, pos)
        pos += _TABLE_COUNT_STRUCT.size

        entries: List[CivdFileEntryV04] = []

        for _ in range(entry_count):
            # name length
            if len(buf) - pos < 2:
                raise ValueError("Buffer too short for name length")
            (name_len,) = struct.unpack_from("<H", buf, pos)
            pos += 2

            if len(buf) - pos < name_len:
                raise ValueError("Buffer too short for name bytes")
            name_bytes = buf[pos : pos + name_len]
            pos += name_len
            name = name_bytes.decode("utf-8")

            # fixed metadata
            if len(buf) - pos < _ENTRY_META_STRUCT.size:
                raise ValueError("Buffer too short for entry metadata")
            mime, flags, f_offset, size, checksum = _ENTRY_META_STRUCT.unpack_from(buf, pos)
            pos += _ENTRY_META_STRUCT.size

            entries.append(
                CivdFileEntryV04(
                    name=name,
                    mime=mime,
                    offset=f_offset,
                    size=size,
                    flags=flags,
                    checksum=checksum,
                )
            )

        consumed = pos - offset
        return cls(entries=entries), consumed

    @classmethod
    def from_bytes_with_length(
        cls, buf: bytes, offset: int = 0
    ) -> Tuple["CivdFileTableV04", int]:
        """
        Parse a file table with a leading u32 length prefix.

        Returns:
            (table, total_bytes_consumed)
        """
        pos = offset

        if len(buf) - pos < _TABLE_LENGTH_STRUCT.size:
            raise ValueError("Buffer too short for table length prefix")

        (length,) = _TABLE_LENGTH_STRUCT.unpack_from(buf, pos)
        pos += _TABLE_LENGTH_STRUCT.size

        if len(buf) - pos < length:
            raise ValueError("Buffer too short for declared table body length")

        body = buf[pos : pos + length]
        table, inner_consumed = cls.from_bytes(body, 0)

        # inner_consumed should equal `length`, but we do not strictly enforce it here.
        pos += length
        total_consumed = pos - offset
        return table, total_consumed


# ---------------------------------------------------------------------------
# Helper used by CIVD v0.4/v0.5 codecs
# ---------------------------------------------------------------------------

def build_file_table_from_file_list(
    file_specs: List[Tuple[str, int]]
) -> Tuple[CivdFileTableV04, bytes]:
    """
    Build a CivdFileTableV04 plus its serialized [len][body] bytes
    from a list of (name, size) pairs.

    Offsets are assigned sequentially starting at 0 in the order given.
    """
    entries: List[CivdFileEntryV04] = []
    offset = 0

    for name, size in file_specs:
        entry = CivdFileEntryV04(
            name=name,
            mime=1,        # 1 = generic binary / application/octet-stream
            offset=offset,
            size=size,
            flags=0,
            checksum=0,
        )
        entries.append(entry)
        offset += size

    table = CivdFileTableV04(entries=entries)
    table_bytes = table.to_bytes_with_length()
    return table, table_bytes


# ---------------------------------------------------------------------------
# Demo / self-test
# ---------------------------------------------------------------------------

def demo_roundtrip() -> None:
    """
    Simple self-test: build a fake table, serialize, parse back, compare.
    """
    original_entries = [
        CivdFileEntryV04(
            name="nav/map.pcd",
            mime=1,
            offset=0,
            size=32768,
            flags=0,
            checksum=0,
        ),
        CivdFileEntryV04(
            name="nav/waypoints.json",
            mime=1,
            offset=32768,
            size=2048,
            flags=0,
            checksum=0,
        ),
        CivdFileEntryV04(
            name="vision/front.jpg",
            mime=1,
            offset=34816,
            size=65536,
            flags=0,
            checksum=0,
        ),
    ]

    table = CivdFileTableV04(entries=original_entries)
    buf = table.to_bytes_with_length()
    parsed_table, consumed = CivdFileTableV04.from_bytes_with_length(buf)

    print("Original entries:")
    for e in original_entries:
        print("  ", e)

    print("\nParsed entries:")
    for e in parsed_table.entries:
        print("  ", e)

    print(f"\nBytes consumed: {consumed} (total buffer len = {len(buf)})")
    print("Roundtrip OK:", parsed_table.entries == original_entries)


if __name__ == "__main__":
    demo_roundtrip()
