from __future__ import annotations

"""
CIVD v0.4 File Table implementation.

This matches the simplified spec in `specs/civd-v0.4-file-table.md`:

Header (little-endian):
  uint32 file_count
  uint32 table_reserved   # must be 0 for now

Then `file_count` entries, each:

  uint16 name_len         # length of filename in bytes (UTF-8)
  bytes[name_len] name    # filename (not null-terminated)
  uint16 mime             # MIME/type code (advisory)
  uint32 offset           # offset into payload block (bytes)
  uint32 size             # length of file in bytes
  uint16 flags            # bitmask (compression/encryption/semantic/etc.)
  uint32 checksum         # CRC32 (or 0 if unused)

This module does not know about the 3D volume itself; it only handles
the file table buffer and a conceptual "payload block" that sits after it.
"""

import dataclasses
import struct
from typing import List, Tuple

# --- Structs -----------------------------------------------------------------

# Header: file_count (uint32), table_reserved (uint32)
HEADER_STRUCT = struct.Struct("<II")  # file_count, table_reserved

# Fixed part of each entry (name is variable-length and comes before this in our
# packed layout below).
#
# We will pack entries as:
#   [name_len (H)] [name bytes] [mime (H)] [offset (I)] [size (I)] [flags (H)] [checksum (I)]
#
# For convenience, we keep a struct just for the fixed tail:
ENTRY_TAIL_STRUCT = struct.Struct("<H I I H I")  # mime, offset, size, flags, checksum


@dataclasses.dataclass
class CivdFileEntryV04:
    """
    One logical file entry inside a CIVD v0.4 capsule.
    """

    name: str
    mime: int
    offset: int
    size: int
    flags: int = 0
    checksum: int = 0

    def to_bytes(self) -> bytes:
        """
        Serialize this entry to bytes, according to v0.4 layout.
        """
        name_bytes = self.name.encode("utf-8")
        name_len = len(name_bytes)
        # name_len (uint16) + name bytes + fixed tail
        head = struct.pack("<H", name_len)
        tail = ENTRY_TAIL_STRUCT.pack(
            self.mime,
            self.offset,
            self.size,
            self.flags,
            self.checksum,
        )
        return head + name_bytes + tail

    @staticmethod
    def from_bytes(buf: bytes, offset: int) -> Tuple["CivdFileEntryV04", int]:
        """
        Parse a single entry starting at `offset` in `buf`.

        Returns:
            (entry, new_offset)
        where new_offset is the index after this entry.
        """
        # Read name_len
        if offset + 2 > len(buf):
            raise ValueError("Buffer too small to read name_len")
        (name_len,) = struct.unpack_from("<H", buf, offset)
        offset += 2

        # Read name bytes
        end_name = offset + name_len
        if end_name > len(buf):
            raise ValueError("Buffer too small to read filename")
        name_bytes = buf[offset:end_name]
        name = name_bytes.decode("utf-8", errors="replace")
        offset = end_name

        # Read fixed tail
        if offset + ENTRY_TAIL_STRUCT.size > len(buf):
            raise ValueError("Buffer too small to read entry tail")
        mime, file_offset, size, flags, checksum = ENTRY_TAIL_STRUCT.unpack_from(buf, offset)
        offset += ENTRY_TAIL_STRUCT.size

        entry = CivdFileEntryV04(
            name=name,
            mime=mime,
            offset=file_offset,
            size=size,
            flags=flags,
            checksum=checksum,
        )
        return entry, offset


@dataclasses.dataclass
class CivdFileTableV04:
    """
    Complete file table for a CIVD v0.4 capsule.

    This describes *only* the logical files; it does not include the payload bytes.
    """

    entries: List[CivdFileEntryV04]
    table_reserved: int = 0

    def to_bytes(self) -> bytes:
        """
        Serialize the entire file table (header + entries) to bytes.
        """
        file_count = len(self.entries)
        header = HEADER_STRUCT.pack(file_count, self.table_reserved)
        body_parts = [header]
        for entry in self.entries:
            body_parts.append(entry.to_bytes())
        return b"".join(body_parts)

    @staticmethod
    def from_bytes(buf: bytes) -> "CivdFileTableV04":
        """
        Parse a file table from a buffer.

        Returns a CivdFileTableV04 instance.
        """
        if len(buf) < HEADER_STRUCT.size:
            raise ValueError("Buffer too small for file table header")

        file_count, table_reserved = HEADER_STRUCT.unpack_from(buf, 0)
        offset = HEADER_STRUCT.size

        entries: List[CivdFileEntryV04] = []
        for _ in range(file_count):
            entry, offset = CivdFileEntryV04.from_bytes(buf, offset)
            entries.append(entry)

        # We ignore any trailing bytes in buf; in real usage, the caller knows the
        # table length and uses that to split table vs payload.
        return CivdFileTableV04(entries=entries, table_reserved=table_reserved)


# --- Convenience helpers -----------------------------------------------------


def build_file_table_from_file_list(
    files: List[Tuple[str, int]],
    start_offset: int = 0,
    mime_default: int = 1,
) -> CivdFileTableV04:
    """
    Convenience helper:

    Given a list of (name, size) pairs, build a CivdFileTableV04 where each file
    is laid out sequentially in the payload block starting at `start_offset`.

    Returns a CivdFileTableV04 with computed offsets and sizes.
    """
    entries: List[CivdFileEntryV04] = []
    current_offset = start_offset

    for name, size in files:
        entry = CivdFileEntryV04(
            name=name,
            mime=mime_default,  # or per-file if you know it
            offset=current_offset,
            size=size,
            flags=0,
            checksum=0,
        )
        entries.append(entry)
        current_offset += size

    return CivdFileTableV04(entries=entries)


def demo_roundtrip() -> None:
    """
    Small sanity check to verify that encoding/decoding the file table works.
    """
    # Fake files: (name, size)
    files = [
        ("nav/map.pcd", 32768),
        ("nav/waypoints.json", 2048),
        ("vision/front.jpg", 65536),
    ]

    table = build_file_table_from_file_list(files)

    blob = table.to_bytes()
    parsed = CivdFileTableV04.from_bytes(blob)

    print("Original entries:")
    for e in table.entries:
        print("  ", e)

    print("\nParsed entries:")
    for e in parsed.entries:
        print("  ", e)

    # Basic check: names and sizes should match
    ok = all(
        (a.name == b.name and a.size == b.size and a.offset == b.offset)
        for a, b in zip(table.entries, parsed.entries)
    )
    print("\nRoundtrip OK:", ok)
