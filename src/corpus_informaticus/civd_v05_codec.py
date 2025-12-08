# civd_v05_codec.py
"""
CIVD v0.5 – Adaptive Geometry + Capsule Metadata
Compatible with v0.3/v0.4 header + file table.
"""

import os
import json
import math
from typing import Dict, Tuple, Optional

from .codec_v03 import encode_bytes_to_civd_v03, decode_civd_v03
from .filetable_v04 import (
    CivdFileTableV04,
    build_file_table_from_file_list,
)


# ---------------------------------------------------------------------
# 1. Geometry selection (v0.5 adaptive cube)
# ---------------------------------------------------------------------

def choose_geometry_v05(payload_size: int, channels: int = 4) -> Tuple[int, int, int]:
    """Choose minimal cubic geometry to fit payload."""
    voxels_needed = math.ceil(payload_size / channels)
    d = math.ceil(voxels_needed ** (1.0 / 3.0))
    return (d, d, d)


# ---------------------------------------------------------------------
# 2. Encode arbitrary payload dict → CIVD v0.5 blob
# ---------------------------------------------------------------------

def encode_payloads_to_civd_v05(
    payloads: Dict[str, bytes],
    capsule_meta: Optional[dict] = None,
    channels: int = 4,
) -> Tuple[bytes, dict]:
    """
    payloads: dict of filename → bytes
    capsule_meta: optional JSON metadata stored as meta/civd.json

    v0.5 behavior:
    - build a v0.4-style file table using (name, size) entries
    - pack table + data region into a single byte stream
    - choose adaptive cubic geometry for that byte stream
    - wrap it with the existing v0.3 encoder
    """

    # -------------------------------------------------
    # 2.1 Build an ordered list of (name, data)
    # -------------------------------------------------
    ordered_files = []

    # Add payload files
    for name, data in payloads.items():
        ordered_files.append((name, data))

    # Add metadata file if requested
    if capsule_meta is not None:
        meta_json = json.dumps(capsule_meta, indent=2).encode("utf-8")
        ordered_files.append(("meta/civd.json", meta_json))

    # -------------------------------------------------
    # 2.2 Build v0.4 file table from (name, size)
    # -------------------------------------------------
    file_specs_for_table = []
    for name, data in ordered_files:
        file_specs_for_table.append((name, len(data)))

    table_obj, table_bytes = build_file_table_from_file_list(file_specs_for_table)

    # -------------------------------------------------
    # 2.3 Concatenate all payload data (table + data)
    # -------------------------------------------------
    data_region = b"".join(data for (_name, data) in ordered_files)
    payload_bytes = table_bytes + data_region

    # -------------------------------------------------
    # 2.4 Choose geometry (v0.5 adaptive cube)
    # -------------------------------------------------
    dims = choose_geometry_v05(len(payload_bytes), channels=channels)

    # -------------------------------------------------
    # 2.5 Encode inner payload using v0.3 encoder
    # -------------------------------------------------
    blob = encode_bytes_to_civd_v03(payload_bytes, dims=dims, channels=channels)

    info = {
        "dims": dims,
        "channels": channels,
        "payload_size": len(payload_bytes),
        "file_count": len(ordered_files),
        "files": [name for (name, _data) in ordered_files],
        "has_capsule_meta": capsule_meta is not None,
    }

    return blob, info


    # -------------------------------------------------
    # 2.1 Insert metadata entry into file list
    # -------------------------------------------------
    file_specs = []

    # Add payload files
    for name, data in payloads.items():
        file_specs.append((name, data))

    # Add metadata file if requested
    if capsule_meta is not None:
        meta_json = json.dumps(capsule_meta, indent=2).encode("utf-8")
        file_specs.append(("meta/civd.json", meta_json))

    # -------------------------------------------------
    # 2.2 Build v0.4 file table
    # -------------------------------------------------
    table_obj, table_bytes = build_file_table_from_file_list(file_specs)

    # -------------------------------------------------
    # 2.3 Concatenate all payload data (table + data region)
    # -------------------------------------------------
    data_region = b""
    for name, data in file_specs:
        data_region += data

    payload_bytes = table_bytes + data_region

    # -------------------------------------------------
    # 2.4 Choose geometry (v0.5 behavior)
    # -------------------------------------------------
    dims = choose_geometry_v05(len(payload_bytes), channels=channels)

    # -------------------------------------------------
    # 2.5 Encode inner payload using v0.3 encoder
    # -------------------------------------------------
    blob = encode_bytes_to_civd_v03(payload_bytes, dims=dims, channels=channels)

    info = {
        "dims": dims,
        "channels": channels,
        "payload_size": len(payload_bytes),
        "file_count": len(file_specs),
        "files": [name for (name, _) in file_specs],
        "has_capsule_meta": capsule_meta is not None,
    }

    return blob, info


# ---------------------------------------------------------------------
# 3. Encode folder → CIVD v0.5
# ---------------------------------------------------------------------

def encode_folder_to_civd_v05(
    folder: str,
    capsule_meta: Optional[dict] = None,
    channels: int = 4,
) -> Tuple[bytes, dict]:
    """
    Load all files from a folder and encode them into a CIVD v0.5 capsule.
    """
    payloads: Dict[str, bytes] = {}
    for root, dirs, files in os.walk(folder):
        for f in files:
            path = os.path.join(root, f)
            rel = os.path.relpath(path, folder).replace("\\", "/")
            with open(path, "rb") as fp:
                payloads[rel] = fp.read()

    return encode_payloads_to_civd_v05(
        payloads, capsule_meta=capsule_meta, channels=channels
    )


# ---------------------------------------------------------------------
# 4. Decode CIVD v0.5 blob → (file_table, files, meta)
# ---------------------------------------------------------------------

def decode_civd_v05(blob: bytes):
    """Decode full v0.5 capsule into file table + file map + metadata."""
    # v0.3 decoder returns: payload_bytes, info_dict
    payload, info = decode_civd_v03(blob)

    # Split table + data region using v0.4 helper
    table_obj, consumed = CivdFileTableV04.from_bytes_with_length(payload)
    data_region = payload[consumed:]

    # Extract files from data region
    files: Dict[str, bytes] = {}
    for entry in table_obj.entries:
        offset = entry.offset
        size = entry.size
        files[entry.name] = data_region[offset:offset + size]

    # Extract capsule-level metadata (if present)
    capsule_meta = None
    if "meta/civd.json" in files:
        try:
            capsule_meta = json.loads(files["meta/civd.json"].decode("utf-8"))
        except Exception:
            capsule_meta = None

    meta_out = {
        "dims": info["dims"],
        "channels": info["channels"],
        "file_count": len(files),
        "payload_size": len(payload),
        "capsule_meta": capsule_meta,
    }

    return table_obj, files, meta_out
