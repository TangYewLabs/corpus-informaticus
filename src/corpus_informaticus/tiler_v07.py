"""
tiler_v07.py — CIVD v0.7 tiling and ROI helpers.

This module implements:
- Tiling a dense 4D volume (z, y, x, C) into smaller 3D tiles.
- Reassembling a volume from tiles.
- Determining which tiles a given ROI touches.

It is generic: it does not know about on-disk CIVD layout, only
about logical volumes and TileManifestV07.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Tuple, Set

import numpy as np

from .tile_manifest_v07 import (
    TileManifestV07,
    TileGridSpecV07,
    TileIndexV07,
)
from .roi_v06 import RoiV06


# ---------------------------------------------------------------------------
# Tiling
# ---------------------------------------------------------------------------


TilesDict = Dict[TileIndexV07, np.ndarray]


def tile_volume(
    vol: np.ndarray,
    manifest: TileManifestV07,
) -> TilesDict:
    """
    Split a dense volume into tiles.

    Parameters
    ----------
    vol:
        NumPy array with shape (z, y, x, C).
    manifest:
        TileManifestV07 describing dims, tile sizes, and channels.

    Returns
    -------
    dict[TileIndexV07, np.ndarray]
        Mapping tile indices to tile arrays with shape
        (tile_z_eff, tile_y_eff, tile_x_eff, C).
    """
    if vol.ndim != 4:
        raise ValueError(f"Expected 4D array (z, y, x, C), got shape {vol.shape}")

    z, y, x, c = vol.shape
    gx, gy, gz = manifest.grid.grid_dims()
    dx, dy, dz = manifest.grid.dims
    if (x, y, z) != (dx, dy, dz):
        raise ValueError(
            f"Volume shape spatial dims (x={x}, y={y}, z={z}) do not match "
            f"manifest dims {manifest.grid.dims}"
        )
    if c != manifest.channels:
        raise ValueError(
            f"Volume channels {c} do not match manifest.channels={manifest.channels}"
        )

    tiles: TilesDict = {}
    for tz in range(gz):
        for ty in range(gy):
            for tx in range(gx):
                idx = TileIndexV07(tx=tx, ty=ty, tz=tz)
                x0, x1, y0, y1, z0, z1 = manifest.grid.tile_bounds(idx)
                tile = vol[z0:z1, y0:y1, x0:x1, :]
                tiles[idx] = tile.copy()
    return tiles


def assemble_volume_from_tiles(
    manifest: TileManifestV07,
    tiles: TilesDict,
    fill_value: float = 0.0,
) -> np.ndarray:
    """
    Reconstruct a dense volume from tiles.

    Any missing tiles are filled with 'fill_value'.
    """
    dx, dy, dz = manifest.grid.dims
    x, y, z = dx, dy, dz
    c = manifest.channels

    vol = np.full((z, y, x, c), fill_value, dtype=np.dtype(manifest.dtype))

    gx, gy, gz = manifest.grid.grid_dims()

    for tz in range(gz):
        for ty in range(gy):
            for tx in range(gx):
                idx = TileIndexV07(tx=tx, ty=ty, tz=tz)
                x0, x1, y0, y1, z0, z1 = manifest.grid.tile_bounds(idx)

                tile = tiles.get(idx, None)
                if tile is None:
                    continue  # leave fill_value

                tz_size, ty_size, tx_size, tc = tile.shape
                if tc != c:
                    raise ValueError(
                        f"Tile {idx} channels {tc} != manifest.channels {c}"
                    )

                # Sanity check: tile must fit inside the target region
                if (z1 - z0, y1 - y0, x1 - x0) != (tz_size, ty_size, tx_size):
                    raise ValueError(
                        f"Tile {idx} shape {tile.shape} does not match "
                        f"bounds size (z={z1-z0}, y={y1-y0}, x={x1-x0})"
                    )

                vol[z0:z1, y0:y1, x0:x1, :] = tile

    return vol


# ---------------------------------------------------------------------------
# ROI ↔ tiles relationship
# ---------------------------------------------------------------------------


def tiles_for_roi(
    manifest: TileManifestV07,
    roi: RoiV06,
) -> List[TileIndexV07]:
    """
    Return the list of tiles that intersect a given ROI.

    ROI is defined in voxel space:
        roi.x, roi.y, roi.z, roi.w, roi.h, roi.d

    Tile indices are determined by overlap in global coordinates.
    """
    dx, dy, dz = manifest.grid.dims
    tx_size, ty_size, tz_size = manifest.grid.tile

    # ROI bounds in [0, dims) coordinate space.
    x0 = roi.x
    y0 = roi.y
    z0 = roi.z
    x1 = roi.x + roi.w
    y1 = roi.y + roi.h
    z1 = roi.z + roi.d

    if x0 >= dx or y0 >= dy or z0 >= dz:
        return []
    if x1 <= 0 or y1 <= 0 or z1 <= 0:
        return []

    # Clamp ROI to volume, to avoid negative ranges.
    x0_clamped = max(0, x0)
    y0_clamped = max(0, y0)
    z0_clamped = max(0, z0)
    x1_clamped = min(dx, x1)
    y1_clamped = min(dy, y1)
    z1_clamped = min(dz, z1)

    if x1_clamped <= x0_clamped or y1_clamped <= y0_clamped or z1_clamped <= z0_clamped:
        return []

    # Tile ranges: any tile whose bounds overlap the ROI.
    # tile index range along each axis:
    #   t_start = floor(x0_clamped / tile_size)
    #   t_end   = floor((x1_clamped - 1) / tile_size)
    gx, gy, gz = manifest.grid.grid_dims()

    tx_start = x0_clamped // tx_size
    ty_start = y0_clamped // ty_size
    tz_start = z0_clamped // tz_size

    tx_end = (x1_clamped - 1) // tx_size
    ty_end = (y1_clamped - 1) // ty_size
    tz_end = (z1_clamped - 1) // tz_size

    tx_start = max(0, min(tx_start, gx - 1))
    ty_start = max(0, min(ty_start, gy - 1))
    tz_start = max(0, min(tz_start, gz - 1))

    tx_end = max(0, min(tx_end, gx - 1))
    ty_end = max(0, min(ty_end, gy - 1))
    tz_end = max(0, min(tz_end, gz - 1))

    indices: List[TileIndexV07] = []
    for tz in range(tz_start, tz_end + 1):
        for ty in range(ty_start, ty_end + 1):
            for tx in range(tx_start, tx_end + 1):
                indices.append(TileIndexV07(tx=tx, ty=ty, tz=tz))

    return indices
