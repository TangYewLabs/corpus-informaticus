"""
tile_pack_v07.py — CIVD v0.7 tiling helpers.

This module implements:
- A small tiling spec (TilingSpecV07)
- Stable tile naming (tile_txX_tyY_tzZ.bin)
- Conversion of a dense v0.6 volume buffer into per-tile binaries
- Writing a "tile pack" folder with a JSON manifest
- Loading the manifest back as a TilingSpecV07
- Querying which tiles intersect a given RoiV06

It is intentionally independent from the on-disk CIVD layout:
it works over a decoded dense buffer + VolumeSpecV06.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
import math
import os
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .roi_v06 import VolumeSpecV06, RoiV06
from .tile_manifest_v07 import TileIndexV07

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_MANIFEST_FILENAME = "tiling_manifest.json"
TILE_MANIFEST_VERSION = "civd.tilepack.v0.7"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TilingSpecV07:
    """
    Logical description of how a dense volume was tiled.

    volume_dims:
        (x, y, z) voxel dimensions of the original dense volume.
    tile_size:
        (tile_x, tile_y, tile_z) tile side lengths in voxels.
    tiles_per_axis:
        (tiles_x, tiles_y, tiles_z) counts along each axis.
    """

    volume_dims: Tuple[int, int, int]
    tile_size: Tuple[int, int, int]
    tiles_per_axis: Tuple[int, int, int]


# ---------------------------------------------------------------------------
# Tile naming helpers
# ---------------------------------------------------------------------------


def tile_index_to_name(idx: TileIndexV07) -> str:
    """
    Convert a TileIndexV07 to a stable filename.

    Example:
        TileIndexV07(tx=1, ty=2, tz=3)
        -> "tile_tx1_ty2_tz3.bin"
    """
    return f"tile_tx{idx.tx}_ty{idx.ty}_tz{idx.tz}.bin"


def name_to_tile_index(name: str) -> TileIndexV07:
    """
    Parse a tile filename back into a TileIndexV07.

    Accepts names of the form:
        "tile_txX_tyY_tzZ.bin"
    """
    base = os.path.basename(name)
    if not base.startswith("tile_tx") or not base.endswith(".bin"):
        raise ValueError(f"Not a valid tile filename: {name!r}")

    core = base[:-4]  # drop ".bin"
    parts = core.split("_")
    # Expect ["tile", "txX", "tyY", "tzZ"]
    if len(parts) != 4:
        raise ValueError(f"Unexpected tile name structure: {name!r}")

    try:
        tx = int(parts[1][2:])
        ty = int(parts[2][2:])
        tz = int(parts[3][2:])
    except Exception as exc:
        raise ValueError(f"Failed to parse tile indices from: {name!r}") from exc

    return TileIndexV07(tx=tx, ty=ty, tz=tz)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _compute_tiles_per_axis(
    volume_dims: Tuple[int, int, int],
    tile_size: Tuple[int, int, int],
) -> Tuple[int, int, int]:
    """
    Given volume dims (X, Y, Z) and tile_size (Tx, Ty, Tz),
    compute how many tiles we need along each axis, using ceil division.
    """
    x, y, z = volume_dims
    tx, ty, tz = tile_size

    if tx <= 0 or ty <= 0 or tz <= 0:
        raise ValueError(f"Tile size must be > 0, got {tile_size}")

    tiles_x = math.ceil(x / tx)
    tiles_y = math.ceil(y / ty)
    tiles_z = math.ceil(z / tz)

    return tiles_x, tiles_y, tiles_z


def _full_volume_view(
    buf: bytes,
    spec: VolumeSpecV06,
) -> np.ndarray:
    """
    Return a NumPy view over the full volume with shape (z, y, x, C).

    We re-implement the same logic as roi_v06._volume_view_from_bytes
    so tile_pack_v07 stays decoupled from any private helpers.
    """
    expected = spec.expected_nbytes()
    if len(buf) != expected:
        raise ValueError(
            f"Buffer size {len(buf)} does not match expected {expected} "
            f"for dims={spec.dims}, channels={spec.channels}, dtype={spec.dtype}"
        )

    dtype = np.dtype(spec.dtype)
    x, y, z = spec.dims
    total_voxels = x * y * z

    arr = np.frombuffer(buf, dtype=dtype)
    if arr.size != total_voxels * spec.channels:
        raise ValueError(
            f"Buffer length {arr.size} elements does not match "
            f"voxels*channels = {total_voxels * spec.channels}"
        )

    if spec.order not in ("C", "F"):
        raise ValueError(f"Unsupported order: {spec.order!r}. Use 'C' or 'F'.")

    vol = arr.reshape((z, y, x, spec.channels), order=spec.order)
    return vol


# ---------------------------------------------------------------------------
# Tiling core
# ---------------------------------------------------------------------------


def tile_volume_buffer(
    buf: bytes,
    spec: VolumeSpecV06,
    tile_size: Tuple[int, int, int],
) -> Tuple[TilingSpecV07, Dict[TileIndexV07, bytes]]:
    """
    Slice a dense volume buffer into per-tile binary blobs.

    Parameters
    ----------
    buf:
        Raw bytes containing a dense volume in the layout described by 'spec'.
    spec:
        VolumeSpecV06 describing dims, channels, dtype, order, signature.
        For v0.7 we assume a standard dense tensor with signature
        'C_CONTIG' or 'F_CONTIG' (checked by roi_v06).
    tile_size:
        (tile_x, tile_y, tile_z) tile dimensions in voxels.

    Returns
    -------
    (tiling_spec, tiles)
        tiling_spec:  TilingSpecV07 describing the tiling layout.
        tiles:        dict[TileIndexV07, bytes] of per-tile buffers.
    """
    x_max, y_max, z_max = spec.dims
    tx, ty, tz = tile_size

    tiles_per_axis = _compute_tiles_per_axis(spec.dims, tile_size)
    tiles_x, tiles_y, tiles_z = tiles_per_axis

    tiling_spec = TilingSpecV07(
        volume_dims=spec.dims,
        tile_size=tile_size,
        tiles_per_axis=tiles_per_axis,
    )

    vol = _full_volume_view(buf, spec)  # (z, y, x, C)

    tiles: Dict[TileIndexV07, bytes] = {}

    for tz_idx in range(tiles_z):
        z0 = tz_idx * tz
        z1 = min(z0 + tz, z_max)
        if z0 >= z1:
            continue

        for ty_idx in range(tiles_y):
            y0 = ty_idx * ty
            y1 = min(y0 + ty, y_max)
            if y0 >= y1:
                continue

            for tx_idx in range(tiles_x):
                x0 = tx_idx * tx
                x1 = min(x0 + tx, x_max)
                if x0 >= x1:
                    continue

                tile_arr = vol[z0:z1, y0:y1, x0:x1, :]
                tile_buf = tile_arr.tobytes()

                idx = TileIndexV07(tx=tx_idx, ty=ty_idx, tz=tz_idx)
                tiles[idx] = tile_buf

    return tiling_spec, tiles


# ---------------------------------------------------------------------------
# Pack / manifest helpers
# ---------------------------------------------------------------------------


def write_tile_pack(
    out_dir: str,
    tiling_spec: TilingSpecV07,
    tiles: Dict[TileIndexV07, bytes],
) -> None:
    """
    Write a "tile pack" directory:

        out_dir/
          ├── tiling_manifest.json
          ├── tile_tx0_ty0_tz0.bin
          ├── tile_tx0_ty0_tz1.bin
          └── ...

    The manifest contains a machine-readable description of the tiling.
    """
    os.makedirs(out_dir, exist_ok=True)

    manifest_tiles = []

    for idx, buf in tiles.items():
        filename = tile_index_to_name(idx)
        path = os.path.join(out_dir, filename)
        with open(path, "wb") as f:
            f.write(buf)

        manifest_tiles.append(
            {
                "tx": idx.tx,
                "ty": idx.ty,
                "tz": idx.tz,
                "filename": filename,
                "nbytes": len(buf),
            }
        )

    manifest = {
        "version": TILE_MANIFEST_VERSION,
        "volume_dims": list(tiling_spec.volume_dims),
        "tile_size": list(tiling_spec.tile_size),
        "tiles_per_axis": list(tiling_spec.tiles_per_axis),
        "tiles": manifest_tiles,
    }

    manifest_path = os.path.join(out_dir, TILE_MANIFEST_FILENAME)
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)


def load_tile_manifest(out_dir: str) -> TilingSpecV07:
    """
    Load a TilingSpecV07 from a tile pack directory.

    This reads only the global tiling parameters. Per-tile entries are
    available in the JSON if a consumer wants to inspect them.
    """
    manifest_path = os.path.join(out_dir, TILE_MANIFEST_FILENAME)
    with open(manifest_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    volume_dims = tuple(data["volume_dims"])
    tile_size = tuple(data["tile_size"])
    tiles_per_axis = tuple(data["tiles_per_axis"])

    return TilingSpecV07(
        volume_dims=volume_dims,  # type: ignore[arg-type]
        tile_size=tile_size,      # type: ignore[arg-type]
        tiles_per_axis=tiles_per_axis,  # type: ignore[arg-type]
    )


# ---------------------------------------------------------------------------
# ROI → tile selection
# ---------------------------------------------------------------------------


def query_tiles_for_roi(
    tiling_spec: TilingSpecV07,
    roi: RoiV06,
) -> List[TileIndexV07]:
    """
    Given a tiling spec and an ROI in voxel space, return the list of
    TileIndexV07 that intersect that ROI.

    This is used for:
    - Robotics: "Which tiles do I need for this field-of-view?"
    - Cloud / streaming: "Which tiles should I fetch for this request?"
    """
    x_max, y_max, z_max = tiling_spec.volume_dims
    tx_size, ty_size, tz_size = tiling_spec.tile_size
    tiles_x, tiles_y, tiles_z = tiling_spec.tiles_per_axis

    # ROI bounds in voxel coords
    x0_roi = roi.x
    y0_roi = roi.y
    z0_roi = roi.z
    x1_roi = roi.x + roi.w
    y1_roi = roi.y + roi.h
    z1_roi = roi.z + roi.d

    selected: List[TileIndexV07] = []

    for tz_idx in range(tiles_z):
        z0 = tz_idx * tz_size
        z1 = min(z0 + tz_size, z_max)
        if z1 <= z0:
            continue

        # Z overlap?
        if not (z0 < z1_roi and z1 > z0_roi):
            continue

        for ty_idx in range(tiles_y):
            y0 = ty_idx * ty_size
            y1 = min(y0 + ty_size, y_max)
            if y1 <= y0:
                continue

            # Y overlap?
            if not (y0 < y1_roi and y1 > y0_roi):
                continue

            for tx_idx in range(tiles_x):
                x0 = tx_idx * tx_size
                x1 = min(x0 + tx_size, x_max)
                if x1 <= x0:
                    continue

                # X overlap?
                if not (x0 < x1_roi and x1 > x0_roi):
                    continue

                selected.append(TileIndexV07(tx=tx_idx, ty=ty_idx, tz=tz_idx))

    return selected
