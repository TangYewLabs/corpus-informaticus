"""
CIVD v0.4 codec
---------------

High-level helpers for packing/unpacking a folder of files into a
single CIVD volumetric capsule, using:

- CIVD v0.3 volumetric codec (codec_v03)
- CIVD v0.4 file table (filetable_v04)

Layout inside the volumetric payload (channel 0):

    [ FILE TABLE BYTES ] [ CONCATENATED FILE BYTES ]

The file table describes:
- how many files
- their names
- their offsets and sizes inside the concatenated data region
"""

from __future__ import annotations

import os
from typing import Dict, Tuple, List, Any

from .codec_v03 import encode_bytes_to_civd_v03, decode_civd_v03
from .filetable_v04 import CivdFileEntryV04, CivdFileTableV04


# --------------------------------------------------------------------
# Internal helper: build table + concatenated file bytes from a folder
# --------------------------------------------------------------------
def _build_table_and_blob_from_folder(root: str) -> Tuple[CivdFileTableV04, bytes]:
    """
    Walk `root` and build:

    - a CivdFileTableV04 (entries with name, mime, flags, offset, size)
    - a single bytes blob with all file contents concatenated

    Filenames are stored as POSIX-style paths relative to `root`,
    for example: "nav/map.pcd", "vision/front.jpg".
    """
    root = os.path.abspath(root)
    entries: List[CivdFileEntryV04] = []
    data_chunks: List[bytes] = []
    offset = 0

    for dirpath, _, filenames in os.walk(root):
        for fname in sorted(filenames):
            full_path = os.path.join(dirpath, fname)
            rel_path = os.path.relpath(full_path, root).replace("\\", "/")

            with open(full_path, "rb") as f:
                buf = f.read()

            size = len(buf)

            # For now, we just use mime=1 (generic binary) and flags=0.
            entry = CivdFileEntryV04(
                name=rel_path,
                mime=1,
                offset=offset,
                size=size,
                flags=0,
                checksum=0,  # future: CRC32 per file
            )
            entries.append(entry)
            data_chunks.append(buf)

            offset += size

    table = CivdFileTableV04(entries)
    data_blob = b"".join(data_chunks)
    return table, data_blob


# --------------------------------------------------------------------
# Helper: robustly handle different v0.3 return signatures
# --------------------------------------------------------------------
def _call_v03_encode(payload: bytes,
                     dims: Tuple[int, int, int],
                     channels: int) -> Tuple[bytes, Dict[str, Any]]:
    """
    Wrap encode_bytes_to_civd_v03 to handle different return shapes:

    - blob
    - (blob, info)
    - (blob, info, ...)

    Always returns (blob, info_dict).
    """
    result = encode_bytes_to_civd_v03(payload, dims=dims, channels=channels)

    # Case 1: v0.3 returns just bytes
    if isinstance(result, (bytes, bytearray)):
        blob = bytes(result)
        info: Dict[str, Any] = {}
    # Case 2: v0.3 returns a tuple of 2+ items
    elif isinstance(result, tuple):
        if not result:
            raise ValueError("encode_bytes_to_civd_v03 returned empty tuple")
        blob = result[0]
        # second element is info dict if present
        if len(result) > 1 and isinstance(result[1], dict):
            info = dict(result[1])
        else:
            info = {}
    else:
        raise TypeError(
            f"Unexpected return type from encode_bytes_to_civd_v03: {type(result)}"
        )

    # Ensure we have some minimal info fields, even if v0.3 did not provide them
    info.setdefault("dims", dims)
    info.setdefault("channels", channels)
    info.setdefault("orig_length", len(payload))

    return blob, info


# --------------------------------------------------------------------
# Public API: encode a folder into a CIVD v0.4 volumetric capsule
# --------------------------------------------------------------------
def encode_folder_to_civd_v04(
    root: str,
    dims: Tuple[int, int, int] = (64, 64, 32),
    channels: int = 4,
) -> Tuple[bytes, Dict]:
    """
    Encode all files in `root` into a single CIVD v0.4 capsule.

    Steps:
    - Build file table + concatenated data region.
    - Prepend file-table bytes to data region.
    - Feed that 1D payload into CIVD v0.3 volumetric codec.
    - Return (volumetric_blob, info_dict).
    """
    table, data_blob = _build_table_and_blob_from_folder(root)
    table_bytes = table.to_bytes()

    payload = table_bytes + data_blob

    # Use CIVD v0.3 volumetric codec under the hood, with robust handling
    # of its return signature.
    blob, v03_info = _call_v03_encode(payload, dims=dims, channels=channels)

    info = {
        "dims": v03_info.get("dims", dims),
        "channels": v03_info.get("channels", channels),
        "orig_length": v03_info.get("orig_length", len(payload)),
        "file_count": len(table.entries),
        "files": [e.name for e in table.entries],
        "table_size": len(table_bytes),
        "data_region_size": len(data_blob),
        "payload_size": len(payload),
    }
    return blob, info


# --------------------------------------------------------------------
# Public API: decode a CIVD v0.4 capsule back into files
# --------------------------------------------------------------------
def decode_civd_v04(blob: bytes) -> Tuple[CivdFileTableV04, Dict[str, bytes], Dict]:
    """
    Decode a CIVD v0.4 volumetric capsule into:

    - CivdFileTableV04 (metadata about files)
    - dict mapping filename -> bytes
    - meta dict with dims/channels/count/etc.
    """
    # Step 1: decode volumetric container via v0.3 codec
    payload, v03_info = decode_civd_v03(blob)

    # Step 2: parse file table from the front of the payload
    table, consumed = CivdFileTableV04.from_bytes(payload)
    data_region = payload[consumed:]

    files: Dict[str, bytes] = {}
    for entry in table.entries:
        start = entry.offset
        end = start + entry.size
        files[entry.name] = data_region[start:end]

    meta = {
        "file_count": len(table.entries),
        "dims": v03_info.get("dims"),
        "channels": v03_info.get("channels"),
        "orig_length": v03_info.get("orig_length"),
        "table_size": consumed,
        "data_region_size": len(data_region),
        "payload_size": len(payload),
    }

    return table, files, meta


# --------------------------------------------------------------------
# Small self-test
# --------------------------------------------------------------------
def _demo_roundtrip_folder(root: str = "tmp_v04_test") -> None:
    """
    Simple internal demo: pack `root` into a CIVD capsule,
    then decode it back and print basic info.
    """
    blob, info = encode_folder_to_civd_v04(root)
    print("ENC:", info)

    table, files, meta = decode_civd_v04(blob)
    print("DEC meta:", meta)
    print("Files decoded:")
    for name, data in files.items():
        print("  ", name, "->", repr(data[:40]))
