"""
tile_pack_v08.py — CIVD v0.8 tiling packer with optional per-tile header.

- Writes per-tile binaries with CIVDTILE header (v0.8) + payload.
- Backward compatible readers can treat the tile payload as v0.7 raw.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from typing import Dict, List, Optional, Tuple

import numpy as np

from .roi_v06 import VolumeSpecV06
from .tile_manifest_v07 import TileIndexV07
from .tile_pack_v07 import (
    TILE_MANIFEST_FILENAME,
    tile_index_to_name,
    name_to_tile_index,
    query_tiles_for_roi,
)
from .tile_header_v08 import TileHeaderV08, try_parse_tile_header_v08, TILE_HEADER_LEN_V08


@dataclass(frozen=True)
class TilingSpecV08:
    volume_dims: Tuple[int, int, int]     # (x,y,z)
    tile_size: Tuple[int, int, int]       # (sx,sy,sz)
    tiles_per_axis: Tuple[int, int, int]  # (nx,ny,nz)


def compute_tiling_spec_v08(volume_dims: Tuple[int, int, int], tile_size: Tuple[int, int, int]) -> TilingSpecV08:
    x, y, z = volume_dims
    sx, sy, sz = tile_size
    if sx <= 0 or sy <= 0 or sz <= 0:
        raise ValueError("tile_size must be positive")

    nx = (x + sx - 1) // sx
    ny = (y + sy - 1) // sy
    nz = (z + sz - 1) // sz
    return TilingSpecV08(volume_dims=volume_dims, tile_size=tile_size, tiles_per_axis=(nx, ny, nz))


def tile_volume_buffer_v08(
    buf: bytes,
    spec: VolumeSpecV06,
    tile_size: Tuple[int, int, int],
) -> Tuple[TilingSpecV08, Dict[TileIndexV07, bytes]]:
    """
    Produce raw payload tiles (no headers yet). Payload layout matches v0.6 volume layout:
      view shape: (z,y,x,C)
    """
    vol = np.frombuffer(buf, dtype=np.dtype(spec.dtype)).reshape(
        (spec.dims[2], spec.dims[1], spec.dims[0], spec.channels), order=spec.order
    )

    tiling = compute_tiling_spec_v08(spec.dims, tile_size)
    sx, sy, sz = tiling.tile_size
    nx, ny, nz = tiling.tiles_per_axis

    tiles: Dict[TileIndexV07, bytes] = {}
    for tz in range(nz):
        for ty in range(ny):
            for tx in range(nx):
                x0 = tx * sx
                y0 = ty * sy
                z0 = tz * sz

                x1 = min(x0 + sx, spec.dims[0])
                y1 = min(y0 + sy, spec.dims[1])
                z1 = min(z0 + sz, spec.dims[2])

                sub = vol[z0:z1, y0:y1, x0:x1, :]

                # If tile hits edges, pad to full tile_size for stable addressing.
                pad_z = sz - (z1 - z0)
                pad_y = sy - (y1 - y0)
                pad_x = sx - (x1 - x0)
                if pad_z or pad_y or pad_x:
                    sub = np.pad(
                        sub,
                        pad_width=((0, pad_z), (0, pad_y), (0, pad_x), (0, 0)),
                        mode="constant",
                    )

                tiles[TileIndexV07(tx=tx, ty=ty, tz=tz)] = sub.tobytes(order=spec.order)

    return tiling, tiles


def write_tile_pack_v08(
    out_dir: str,
    tiling: TilingSpecV08,
    tiles: Dict[TileIndexV07, bytes],
    volume_spec: VolumeSpecV06,
    add_tile_headers: bool = True,
) -> str:
    """
    Write a tile pack folder with:
      - per tile .bin files
      - tiling_manifest.json

    If add_tile_headers=True, each tile file is CIVDTILE(v0.8)+payload.
    """
    os.makedirs(out_dir, exist_ok=True)

    # Write tiles
    for idx, payload in tiles.items():
        fname = tile_index_to_name(idx)
        fpath = os.path.join(out_dir, fname)

        if add_tile_headers:
            hdr = TileHeaderV08(
                tile_format_ver=8,
                header_len=64,
                flags=0,
                tx=idx.tx,
                ty=idx.ty,
                tz=idx.tz,
                tile_size=tiling.tile_size,
                channels=volume_spec.channels,
                dtype=volume_spec.dtype,
                signature=volume_spec.signature,
                order=volume_spec.order,
                payload_nbytes=len(payload),
            )
            blob = hdr.to_bytes() + payload
        else:
            blob = payload

        with open(fpath, "wb") as f:
            f.write(blob)

    # Write manifest (keep v0.7 filename for continuity)
    manifest = {
        "schema": "civd.tiling.manifest.v1",
        "tiling_version": "0.8",
        "volume_dims": list(tiling.volume_dims),
        "tile_size": list(tiling.tile_size),
        "tiles_per_axis": list(tiling.tiles_per_axis),
        "tile_files": [tile_index_to_name(idx) for idx in sorted(tiles.keys(), key=lambda t: (t.tz, t.ty, t.tx))],
        "volume_spec": {
            "dims": list(volume_spec.dims),
            "channels": volume_spec.channels,
            "dtype": volume_spec.dtype,
            "order": volume_spec.order,
            "signature": volume_spec.signature,
        },
        "tile_file_format": "CIVDTILE_V08" if add_tile_headers else "RAW_V07",
    }

    mpath = os.path.join(out_dir, TILE_MANIFEST_FILENAME)
    with open(mpath, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    return mpath


def read_tile_file_payload_auto(path: str) -> Tuple[Optional[TileHeaderV08], bytes]:
    """
    Read a tile file and return (header_or_None, payload_bytes).
    - If header present: parse header, strip header_len, return payload
    - Else: return raw bytes as payload (v0.7)
    """
    with open(path, "rb") as f:
        blob = f.read()

    hdr = try_parse_tile_header_v08(blob)
    if hdr is None:
        return None, blob

    payload = blob[hdr.header_len:]
    if len(payload) != hdr.payload_nbytes:
        raise ValueError("Tile payload size mismatch vs header")
    return hdr, payload
