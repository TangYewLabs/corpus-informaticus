"""
CIVD v0.4 File Table
--------------------

This module defines the file table format for CIVD v0.4.

The table sits at the front of the payload region:

| FILECOUNT (4 bytes LE) |
| ENTRY 0                |
| ENTRY 1                |
| ...                    |
| ENTRY N-1              |
| FILEDATA (raw bytes)   |

Each entry is:

    name_len   (1 byte)
    name       (UTF-8)
    mime       (1 byte)
    flags      (1 byte)
    offset     (4 bytes LE)
    size       (4 bytes LE)
    checksum   (4 bytes LE)

"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import List, Tuple


# -------------------------
# Dataclass for file entries
# -------------------------
@dataclass
class CivdFileEntryV04:
    name: str
    mime: int
    offset: int
    size: int
    flags: int = 0
    checksum: int = 0

    def to_bytes(self) -> bytes:
        name_bytes = self.name.encode("utf-8")
        if len(name_bytes) > 255:
            raise ValueError(f"Filename too long: {self.name}")

        return (
            struct.pack("<B", len(name_bytes)) +
            name_bytes +
            struct.pack(
                "<BBIII",
                self.mime,
                self.flags,
                self.offset,
                self.size,
                self.checksum
            )
        )

    @staticmethod
    def from_bytes(buf: bytes, pos: int) -> Tuple["CivdFileEntryV04", int]:
        """Parse an entry from buffer starting at index pos."""
        name_len = buf[pos]
        pos += 1

        name = buf[pos:pos + name_len].decode("utf-8")
        pos += name_len

        mime, flags, offset, size, checksum = struct.unpack_from("<BBIII", buf, pos)
        pos += struct.calcsize("<BBIII")

        return CivdFileEntryV04(
            name=name,
            mime=mime,
            offset=offset,
            size=size,
            flags=flags,
            checksum=checksum,
        ), pos


# -------------------------
# File Table container
# -------------------------
class CivdFileTableV04:
    def __init__(self, entries: List[CivdFileEntryV04]):
        self.entries = entries

    # ---- serialization ----
    def to_bytes(self) -> bytes:
        out = struct.pack("<I", len(self.entries))
        for e in self.entries:
            out += e.to_bytes()
        return out

    # ---- parsing ----
    @staticmethod
    def from_bytes(buf: bytes) -> "CivdFileTableV04":
        count = struct.unpack_from("<I", buf, 0)[0]
        pos = 4
        entries: List[CivdFileEntryV04] = []

        for _ in range(count):
            entry, pos = CivdFileEntryV04.from_bytes(buf, pos)
            entries.append(entry)

        return CivdFileTableV04(entries), pos

    @staticmethod
    def from_bytes_with_length(buf: bytes) -> Tuple["CivdFileTableV04", int]:
        """Return (table, length_consumed_in_bytes)."""
        table, consumed = CivdFileTableV04.from_bytes(buf)
        return table, consumed


# -------------------------
# Small demo for validation
# -------------------------
def demo_roundtrip():
    entries = [
        CivdFileEntryV04("nav/map.pcd", 1, 0, 32768),
        CivdFileEntryV04("nav/waypoints.json", 1, 32768, 2048),
        CivdFileEntryV04("vision/front.jpg", 1, 34816, 65536),
    ]

    tbl = CivdFileTableV04(entries)
    blob = tbl.to_bytes()
    parsed_tbl, consumed = CivdFileTableV04.from_bytes_with_length(blob)

    print("Original entries:")
    for e in entries:
        print("  ", e)
    print("\nParsed entries:")
    for e in parsed_tbl.entries:
        print("  ", e)

    print("\nRoundtrip OK:", parsed_tbl.entries == entries)
