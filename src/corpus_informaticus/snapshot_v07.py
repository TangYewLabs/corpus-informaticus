"""
snapshot_v07.py — CIVD v0.7 snapshot helpers.

This is a *lightweight* snapshot container for dense volume snapshots.

File layout (on disk):

    [ magic         ]  b"CIVD-SNAP7\n"        (11 bytes)
    [ header_len    ]  uint32 LE              (4 bytes)
    [ header_json   ]  UTF-8 JSON (header_len bytes)
    [ volume_bytes  ]  raw dense volume buffer

The volume buffer is interpreted according to VolumeSpecV06:

    shape = (z, y, x, C) in C-contiguous order

This module does NOT depend on the older CIVD v0.3/v0.5 container
layouts; it is a thin, self-contained snapshot format used by v0.7
examples and ROI flows.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import json
import struct

import numpy as np

from .roi_v06 import (
    VolumeSpecV06,
    full_volume_from_bytes,
    read_region_from_bytes,
)
from .roi_v06 import RoiV06  # type: ignore  # defined in same module
from .roi_v06 import clamp_roi  # type: ignore


# ---------------------------------------------------------------------------
# Header model
# ---------------------------------------------------------------------------


@dataclass
class SnapshotHeaderV07:
    """
    Logical header for a v0.7 snapshot.

    version:
        CIVD feature version for this snapshot (e.g. "0.7").
    layout:
        String describing the on-disk layout. For this module:
        "SNAPSHOT_V07".
    dims:
        (x, y, z) voxel dimensions.
    channels:
        Number of channels per voxel.
    dtype:
        NumPy dtype name (e.g. "uint8", "float32").
    signature:
        Logical volume signature, e.g. "C_CONTIG".
    meta:
        Optional capsule-level metadata dictionary (JSON-compatible).
    """

    version: str
    layout: str
    dims: Tuple[int, int, int]
    channels: int
    dtype: str
    signature: str
    meta: Optional[Dict[str, Any]] = None


MAGIC = b"CIVD-SNAP7\n"
MAGIC_LEN = len(MAGIC)
_HEADER_LEN_STRUCT = struct.Struct("<I")  # uint32 little-endian


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _spec_from_header(hdr: SnapshotHeaderV07) -> VolumeSpecV06:
    return VolumeSpecV06(
        dims=hdr.dims,
        channels=hdr.channels,
        dtype=hdr.dtype,
        order="C",
        signature=hdr.signature,
    )


def _build_header_dict(
    spec: VolumeSpecV06,
    meta: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    return {
        "version": "0.7",
        "layout": "SNAPSHOT_V07",
        "dims": list(spec.dims),
        "channels": int(spec.channels),
        "dtype": str(spec.dtype),
        "signature": str(spec.signature),
        "meta": meta if meta is not None else None,
    }


def _header_from_dict(d: Dict[str, Any]) -> SnapshotHeaderV07:
    return SnapshotHeaderV07(
        version=str(d.get("version", "")),
        layout=str(d.get("layout", "")),
        dims=tuple(d.get("dims", [0, 0, 0])),  # type: ignore[arg-type]
        channels=int(d.get("channels", 0)),
        dtype=str(d.get("dtype", "uint8")),
        signature=str(d.get("signature", "C_CONTIG")),
        meta=d.get("meta"),
    )


def _normalize_path_or_bytes(
    path_or_bytes: Union[str, Path, bytes, bytearray]
) -> bytes:
    if isinstance(path_or_bytes, (bytes, bytearray)):
        return bytes(path_or_bytes)
    p = Path(path_or_bytes)
    return p.read_bytes()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def write_snapshot_v07(
    volume_bytes: bytes,
    spec: VolumeSpecV06,
    meta: Optional[Dict[str, Any]] = None,
    path: Optional[Union[str, Path]] = None,
) -> Tuple[bytes, SnapshotHeaderV07]:
    """
    Write a v0.7 snapshot to disk (optionally) and return the blob + header.

    Parameters
    ----------
    volume_bytes:
        Raw dense volume buffer in (z, y, x, C) C-contiguous layout.
    spec:
        VolumeSpecV06 describing dims, channels, dtype, signature.
    meta:
        Optional capsule-level metadata dictionary.
    path:
        Optional filesystem path to write the snapshot to. If None, the
        blob is constructed in memory and only returned.

    Returns
    -------
    blob : bytes
        The complete on-disk representation of the snapshot.
    header : SnapshotHeaderV07
        Parsed header model for convenience.
    """
    expected = spec.expected_nbytes()
    if len(volume_bytes) != expected:
        raise ValueError(
            f"volume_bytes length {len(volume_bytes)} does not match "
            f"expected {expected} for dims={spec.dims}, "
            f"channels={spec.channels}, dtype={spec.dtype}"
        )

    header_dict = _build_header_dict(spec, meta)
    header_json = json.dumps(header_dict, separators=(",", ":"), sort_keys=True).encode(
        "utf-8"
    )
    header_len = len(header_json)

    blob = bytearray()
    blob += MAGIC
    blob += _HEADER_LEN_STRUCT.pack(header_len)
    blob += header_json
    blob += volume_bytes

    out_blob = bytes(blob)
    hdr = _header_from_dict(header_dict)

    if path is not None:
        p = Path(path)
        p.write_bytes(out_blob)

    return out_blob, hdr


def read_snapshot_v07(
    path_or_bytes: Union[str, Path, bytes, bytearray]
) -> Tuple[SnapshotHeaderV07, VolumeSpecV06, bytes]:
    """
    Read a v0.7 snapshot from disk or from an in-memory blob.

    Parameters
    ----------
    path_or_bytes:
        Filesystem path or bytes-like object containing a v0.7 snapshot.

    Returns
    -------
    header : SnapshotHeaderV07
    spec   : VolumeSpecV06
    volume_bytes : bytes
    """
    data = _normalize_path_or_bytes(path_or_bytes)

    if len(data) < MAGIC_LEN + _HEADER_LEN_STRUCT.size:
        raise ValueError("Snapshot data too short to contain header.")

    if data[:MAGIC_LEN] != MAGIC:
        raise ValueError("Snapshot magic header mismatch; not a v0.7 snapshot.")

    offset = MAGIC_LEN
    (header_len,) = _HEADER_LEN_STRUCT.unpack_from(data, offset)
    offset += _HEADER_LEN_STRUCT.size

    if len(data) < offset + header_len:
        raise ValueError("Snapshot data truncated before header JSON.")

    header_json = data[offset : offset + header_len]
    offset += header_len

    header_dict = json.loads(header_json.decode("utf-8"))
    hdr = _header_from_dict(header_dict)

    if hdr.layout != "SNAPSHOT_V07":
        raise ValueError(f"Unexpected snapshot layout: {hdr.layout!r}")

    spec = _spec_from_header(hdr)

    volume_bytes = data[offset:]
    expected = spec.expected_nbytes()
    if len(volume_bytes) != expected:
        raise ValueError(
            f"Snapshot volume length {len(volume_bytes)} does not match "
            f"expected {expected} for dims={spec.dims}, "
            f"channels={spec.channels}, dtype={spec.dtype}"
        )

    return hdr, spec, volume_bytes


def full_volume_from_snapshot_v07(
    path_or_bytes: Union[str, Path, bytes, bytearray],
    copy: bool = False,
):
    """
    Convenience: load the entire snapshot into a 4D tensor (z, y, x, C).

    Returns
    -------
    header : SnapshotHeaderV07
    spec   : VolumeSpecV06
    volume : np.ndarray, shape = (z, y, x, C)
    """
    hdr, spec, vol_bytes = read_snapshot_v07(path_or_bytes)
    vol = full_volume_from_bytes(vol_bytes, spec, copy=copy)
    return hdr, spec, vol


def read_roi_from_snapshot_v07(
    path_or_bytes: Union[str, Path, bytes, bytearray],
    roi: RoiV06,
    channels: Optional[list[int]] = None,
    copy: bool = True,
) -> np.ndarray:
    """
    Extract a 3D region-of-interest (ROI) from a v0.7 snapshot.

    Parameters
    ----------
    path_or_bytes:
        Path or blob of a snapshot created by write_snapshot_v07().
    roi:
        RoiV06 specifying (x, y, z) origin and (w, h, d) size.
    channels:
        Optional subset of channel indices to extract.
    copy:
        If True, returns a copy of the data (default). If False, returns
        a NumPy view over the underlying array.

    Returns
    -------
    np.ndarray
        ROI tensor of shape (d, h, w, C_sel).
    """
    hdr, spec, vol_bytes = read_snapshot_v07(path_or_bytes)

    # Clamp ROI defensively to dims.
    clamped = clamp_roi(roi, spec.dims)

    return read_region_from_bytes(
        buf=vol_bytes,
        spec=spec,
        x=clamped.x,
        y=clamped.y,
        z=clamped.z,
        w=clamped.w,
        h=clamped.h,
        d=clamped.d,
        channels=channels,
        copy=copy,
    )
