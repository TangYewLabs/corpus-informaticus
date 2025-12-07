"""
civd_api_v04.py — High-level API for CIVD v0.4 capsules.

This module provides a simple, stable interface:

- save_folder_as_capsule(folder_path, capsule_path, dims=(64,64,32), channels=4)
- load_capsule(capsule_path)

Under the hood it uses:
- codec_v03 for volumetric encoding/decoding
- civd_v04_codec for file table + file packing
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Tuple, Any

import numpy as np

from .codec_v03 import encode_bytes_to_civd_v03, decode_civd_v03
from .civd_v04_codec import (
    encode_folder_to_civd_v04,
    decode_civd_v04,
)


# ---------- Core helpers ----------


def _build_tensor_from_payload(
    payload: bytes,
    dims: Tuple[int, int, int],
    channels: int,
) -> np.ndarray:
    """
    Convert linear payload into (Z, Y, X, C) tensor.
    """
    dim_x, dim_y, dim_z = dims
    capacity = dim_x * dim_y * dim_z * channels

    if len(payload) > capacity:
        raise ValueError(
            f"Payload length {len(payload)} exceeds capacity {capacity}"
        )

    flat = np.zeros(capacity, dtype=np.uint8)
    flat[: len(payload)] = np.frombuffer(payload, dtype=np.uint8)
    tensor = flat.reshape(dim_z, dim_y, dim_x, channels)
    return tensor


# ---------- Public API ----------


def save_folder_as_capsule(
    folder_path: str | Path,
    capsule_path: str | Path,
    dims: Tuple[int, int, int] = (64, 64, 32),
    channels: int = 4,
) -> dict:
    """
    Pack all files in `folder_path` into a CIVD v0.4 volumetric capsule
    and write it to `capsule_path`.

    Returns a dict with metadata about the capsule.
    """
    folder = Path(folder_path)
    capsule = Path(capsule_path)

    if not folder.is_dir():
        raise ValueError(f"Not a folder: {folder}")

    blob, info = encode_folder_to_civd_v04(
        folder,
        dims=dims,
        channels=channels,
    )

    capsule.write_bytes(blob)
    return info


def load_capsule(
    capsule_path: str | Path,
) -> Tuple[np.ndarray, Dict[str, bytes], dict]:
    """
    Load a .civd capsule and return:

    - tensor: np.ndarray of shape (Z, Y, X, C)
    - files: dict[name -> bytes]
    - meta:  dict with dims, channels, file_count, etc.
    """
    p = Path(capsule_path)
    if not p.exists():
        raise FileNotFoundError(p)

    blob = p.read_bytes()

    # v0.3 volumetric decode
    payload, v03_info = decode_civd_v03(blob)
    dims = v03_info["dims"]
    channels = v03_info["channels"]

    tensor = _build_tensor_from_payload(payload, dims, channels)

    # v0.4 file table + embedded files
    table, files, v04_meta = decode_civd_v04(blob)

    meta: dict[str, Any] = {
        "dims": dims,
        "channels": channels,
        "payload_size": v04_meta.get("payload_size"),
        "file_count": v04_meta.get("file_count"),
        "table_size": v04_meta.get("table_size"),
        "data_region_size": v04_meta.get("data_region_size"),
        "v03_info": v03_info,
        "v04_meta": v04_meta,
    }

    return tensor, files, meta
