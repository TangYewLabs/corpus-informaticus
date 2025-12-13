"""
snapshot_v08.py — CIVD v0.8 snapshot container with explicit schema versioning.

Design:
- Self-identifying header (magic + version)
- Variable header length with length-prefixed strings (schema_version, meta_json)
- Payload is dense volume buffer compatible with VolumeSpecV06 ROI access.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import struct
from typing import Any, Dict, Optional, Tuple

import numpy as np

from .roi_v06 import VolumeSpecV06, read_region_from_bytes

MAGIC_SNAP_V08 = b"CIVDSNAP"  # 8 bytes

# Fixed prefix: magic(8) + ver(u16) + header_len(u16) = 12 bytes
_SNAP_PREFIX = struct.Struct("<8s H H")

# Fixed core fields after prefix:
# dims (3u32), channels (u32), dtype_code(u16), sig_code(u16), order_code(u8), reserved(7 bytes)
_SNAP_CORE = struct.Struct("<3I I H H B 7x")

DTYPE_CODE = {"uint8": 1, "uint16": 2, "float32": 3}
DTYPE_NAME = {v: k for k, v in DTYPE_CODE.items()}

SIG_CODE = {"C_CONTIG": 1, "F_CONTIG": 2}
SIG_NAME = {v: k for k, v in SIG_CODE.items()}

ORDER_CODE = {"C": 1, "F": 2}
ORDER_NAME = {v: k for k, v in ORDER_CODE.items()}


def _pack_lp_string(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack("<I", len(b)) + b


def _unpack_lp_string(blob: bytes, offset: int) -> Tuple[str, int]:
    (n,) = struct.unpack_from("<I", blob, offset)
    offset += 4
    s = blob[offset : offset + n].decode("utf-8")
    offset += n
    return s, offset


@dataclass(frozen=True)
class SnapshotHeaderV08:
    version: str                 # "0.8"
    schema_id: str               # e.g. "CIVD_SNAPSHOT"
    schema_version: str          # e.g. "0.8"
    dims: Tuple[int, int, int]   # (x,y,z)
    channels: int
    dtype: str
    signature: str
    order: str
    meta: Dict[str, Any]


def write_snapshot_v08(
    path: str,
    volume_buf: bytes,
    spec: VolumeSpecV06,
    meta: Optional[Dict[str, Any]] = None,
    schema_id: str = "CIVD_SNAPSHOT",
    schema_version: str = "0.8",
) -> SnapshotHeaderV08:
    meta = meta or {}
    dtype_code = DTYPE_CODE.get(spec.dtype)
    sig_code = SIG_CODE.get(spec.signature)
    order_code = ORDER_CODE.get(spec.order)
    if dtype_code is None:
        raise ValueError(f"Unsupported dtype: {spec.dtype!r}")
    if sig_code is None:
        raise ValueError(f"Unsupported signature: {spec.signature!r}")
    if order_code is None:
        raise ValueError(f"Unsupported order: {spec.order!r}")

    # Encode meta JSON
    meta_json = json.dumps(meta, separators=(",", ":"), ensure_ascii=False)

    core = _SNAP_CORE.pack(
        spec.dims[0], spec.dims[1], spec.dims[2],
        spec.channels,
        dtype_code,
        sig_code,
        order_code,
    )

    tail = (
        _pack_lp_string(schema_id) +
        _pack_lp_string(schema_version) +
        _pack_lp_string(meta_json)
    )

    header_len = _SNAP_PREFIX.size + len(core) + len(tail)
    prefix = _SNAP_PREFIX.pack(MAGIC_SNAP_V08, 8, header_len)
    header_bytes = prefix + core + tail

    expected = spec.expected_nbytes()
    if len(volume_buf) != expected:
        raise ValueError(f"volume_buf size {len(volume_buf)} != expected {expected}")

    with open(path, "wb") as f:
        f.write(header_bytes)
        f.write(volume_buf)

    return SnapshotHeaderV08(
        version="0.8",
        schema_id=schema_id,
        schema_version=schema_version,
        dims=spec.dims,
        channels=spec.channels,
        dtype=spec.dtype,
        signature=spec.signature,
        order=spec.order,
        meta=meta,
    )


def read_snapshot_v08(path: str) -> Tuple[SnapshotHeaderV08, VolumeSpecV06, bytes]:
    with open(path, "rb") as f:
        blob = f.read()

    magic, ver, header_len = _SNAP_PREFIX.unpack_from(blob, 0)
    if magic != MAGIC_SNAP_V08 or ver != 8:
        raise ValueError("Not a CIVD v0.8 snapshot")

    off = _SNAP_PREFIX.size

    x, y, z, channels, dtype_code, sig_code, order_code = _SNAP_CORE.unpack_from(blob, off)
    off += _SNAP_CORE.size

    dtype = DTYPE_NAME.get(dtype_code)
    signature = SIG_NAME.get(sig_code)
    order = ORDER_NAME.get(order_code)
    if dtype is None or signature is None or order is None:
        raise ValueError("Unknown dtype/signature/order in header")

    schema_id, off = _unpack_lp_string(blob, off)
    schema_version, off = _unpack_lp_string(blob, off)
    meta_json, off = _unpack_lp_string(blob, off)

    if off != header_len:
        raise ValueError("Header length mismatch")

    meta = json.loads(meta_json) if meta_json else {}

    spec = VolumeSpecV06(dims=(x, y, z), channels=channels, dtype=dtype, order=order, signature=signature)

    payload = blob[header_len:]
    if len(payload) != spec.expected_nbytes():
        raise ValueError("Snapshot payload size mismatch vs spec")

    header = SnapshotHeaderV08(
        version="0.8",
        schema_id=schema_id,
        schema_version=schema_version,
        dims=(x, y, z),
        channels=channels,
        dtype=dtype,
        signature=signature,
        order=order,
        meta=meta,
    )

    return header, spec, payload


def read_roi_from_snapshot_v08(
    path: str,
    x: int, y: int, z: int,
    w: int, h: int, d: int,
    channels: Optional[list[int]] = None,
) -> "np.ndarray":
    header, spec, payload = read_snapshot_v08(path)
    return read_region_from_bytes(payload, spec, x=x, y=y, z=z, w=w, h=h, d=d, channels=channels, copy=True)
