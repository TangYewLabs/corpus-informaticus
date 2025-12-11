"""
tile_pack_v07.py — CIVD v0.7 tiling helpers.

This module is intentionally minimal and focused on *in-memory tiling*
of a dense CIVD v0.6 volume into per-tile binary chunks on disk.

It does NOT know about the on-disk .civd container layout — it only
operates on:

  - a dense buffer (bytes) representing the volume
  - a VolumeSpecV06 that describes that buffer logically
  - a tile size (tx, ty, tz)

v0.7 introduces:

  - a simple tiling spec (TileGridSpecV07)
  - a stable tile filename convention
  - a JSON manifest for reconstruction
  - a helper to answer: “which tiles intersect this ROI?”
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from math import ceil
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np

from .roi_v06 import VolumeSpecV06, RoiV06, clamp_roi, full_volume_from_bytes
from .tile_manifest_v07 import TileIndexV07

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TILE_MANIFEST_FILENAME = "tiling_manifest.json"


# ---------------------------------------------------------------------------
# Runtime tiling spec (v0.7)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TileGridSpecV07:
    """
    Runtime description of a v0.7 tile grid.

    volume_dims:
        (x, y, z) voxel dimensions of the *global* volume.
    tile_size:
        (tx, ty, tz) tile size in voxels.
    tiles_per_axis:
        (nx, ny, nz) number of tiles along each axis.
    channels:
        Number of channels per voxel.
    dtype:
        NumPy dtype name, e.g. 'uint8', 'float32'.
    order:
        Memory layout order ('C' or 'F') used by the dense buffer.
    signature:
        Logical layout signature (e.g., 'C_CONTIG'). For v0.7 we
        assume C_CONTIG/F_CONTIG matching VolumeSpecV06.
    """

    volume_dims: Tuple[int, int, int]
    tile_size: Tuple[int, int, int]
    tiles_per_axis: Tuple[int, int, int]
    channels: int
    dtype: str
    order: str
    signature: str


# ---------------------------------------------------------------------------
# Tile filename helpers
# ---------------------------------------------------------------------------


def tile_index_to_name(idx: TileIndexV07) -> str:
    """
    Stable filename convention for a tile index.

    Example:
        TileIndexV07(tx=1, ty=2, tz=3)
        -> "tile_tx1_ty2_tz3.bin"
    """
    return f"tile_tx{idx.tx}_ty{idx.ty}_tz{idx.tz}.bin"


def name_to_tile_index(name: str) -> TileIndexV07:
    """
    Parse a tile filename back into a TileIndexV07.

    We are intentionally strict: the expected pattern is
        "tile_tx{tx}_ty{ty}_tz{tz}.bin"
    """
    base = name
    if base.endswith(".bin"):
        base = base[:-4]

    if not base.startswith("tile_tx"):
        raise ValueError(f"Invalid tile name {name!r}: missing 'tile_tx' prefix")

    try:
        # base is "tile_tx{tx}_ty{ty}_tz{tz}"
        parts = base.split("_")
        # ["tile", "tx{tx}", "ty{ty}", "tz{tz}"]
        if len(parts) != 4:
            raise ValueError(f"Unexpected tile name structure: {name!r}")

        tx = int(parts[1][2:])  # strip "tx"
        ty = int(parts[2][2:])  # strip "ty"
        tz = int(parts[3][2:])  # strip "tz"
    except Exception as exc:
        raise ValueError(f"Could not parse tile index from name {name!r}") from exc

    return TileIndexV07(tx=tx, ty=ty, tz=tz)


# ---------------------------------------------------------------------------
# Core tiler: dense volume -> tiles (in memory)
# ---------------------------------------------------------------------------


def _compute_tiles_per_axis(
    dims: Tuple[int, int, int], tile_size: Tuple[int, int, int]
) -> Tuple[int, int, int]:
    x, y, z = dims
    tx, ty, tz = tile_size
    if tx <= 0 or ty <= 0 or tz <= 0:
        raise ValueError(f"tile_size must be positive in all dims, got {tile_size!r}")

    nx = ceil(x / tx)
    ny = ceil(y / ty)
    nz = ceil(z / tz)
    return nx, ny, nz


def tile_volume_buffer(
    buf: bytes,
    spec: VolumeSpecV06,
    tile_size: Tuple[int, int, int],
) -> Tuple[TileGridSpecV07, Dict[TileIndexV07, bytes], Dict]:
    """
    Split a dense CIVD v0.6 volume into a grid of tiles.

    Parameters
    ----------
    buf:
        Raw bytes of the dense volume (z, y, x, C) as described by 'spec'.
    spec:
        VolumeSpecV06 describing dims, channels, dtype, order, signature.
    tile_size:
        (tx, ty, tz) tile size in voxels along x, y, z.

    Returns
    -------
    (tiling_spec, tiles_dict, manifest_dict)
        tiling_spec:
            A TileGridSpecV07 describing the tiling layout.
        tiles_dict:
            Mapping TileIndexV07 -> tile bytes.
        manifest_dict:
            JSON-serializable dict for 'tiling_manifest.json'.
    """
    # Interpret the buffer as a 4D tensor (z, y, x, C)
    vol = full_volume_from_bytes(buf, spec, copy=False)
    x_max, y_max, z_max = spec.dims
    tx, ty, tz = tile_size

    nx, ny, nz = _compute_tiles_per_axis(spec.dims, tile_size)

    tiling_spec = TileGridSpecV07(
        volume_dims=spec.dims,
        tile_size=tile_size,
        tiles_per_axis=(nx, ny, nz),
        channels=spec.channels,
        dtype=spec.dtype,
        order=spec.order,
        signature=spec.signature,
    )

    tiles: Dict[TileIndexV07, bytes] = {}
    tiles_meta: List[Dict] = []

    for tz_idx in range(nz):
        for ty_idx in range(ny):
            for tx_idx in range(nx):
                # Global voxel bounds of this tile
                x0 = tx_idx * tx
                y0 = ty_idx * ty
                z0 = tz_idx * tz

                if x0 >= x_max or y0 >= y_max or z0 >= z_max:
                    continue  # completely outside

                x1 = min(x0 + tx, x_max)
                y1 = min(y0 + ty, y_max)
                z1 = min(z0 + tz, z_max)

                if x1 <= x0 or y1 <= y0 or z1 <= z0:
                    continue  # degenerate tile

                # vol shape is (z, y, x, C)
                tile_arr = vol[z0:z1, y0:y1, x0:x1, :]
                tile_bytes = tile_arr.tobytes()

                idx = TileIndexV07(tx=tx_idx, ty=ty_idx, tz=tz_idx)
                tiles[idx] = tile_bytes

                tiles_meta.append(
                    {
                        "tx": tx_idx,
                        "ty": ty_idx,
                        "tz": tz_idx,
                        "x0": x0,
                        "y0": y0,
                        "z0": z0,
                        "x1": x1,
                        "y1": y1,
                        "z1": z1,
                        "nbytes": len(tile_bytes),
                    }
                )

    manifest = {
        "version": "v0.7",
        "volume_dims": list(spec.dims),
        "tile_size": list(tile_size),
        "tiles_per_axis": [nx, ny, nz],
        "channels": spec.channels,
        "dtype": spec.dtype,
        "order": spec.order,
        "signature": spec.signature,
        "tiles": tiles_meta,
    }

    return tiling_spec, tiles, manifest


# ---------------------------------------------------------------------------
# Save / load tile packs
# ---------------------------------------------------------------------------


def save_tile_pack_to_folder(
    root: Path | str,
    tiling_spec: TileGridSpecV07,
    tiles: Dict[TileIndexV07, bytes],
    manifest: Dict,
) -> None:
    """
    Write tiles + manifest to a folder.

    Layout:
        root/
          tiling_manifest.json
          tile_tx{tx}_ty{ty}_tz{tz}.bin
          ...
    """
    root_path = Path(root)
    root_path.mkdir(parents=True, exist_ok=True)

    # Write manifest
    manifest_path = root_path / TILE_MANIFEST_FILENAME
    with manifest_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2, sort_keys=True)

    # Write each tile
    for idx, data in tiles.items():
        name = tile_index_to_name(idx)
        tile_path = root_path / name
        with tile_path.open("wb") as f:
            f.write(data)


def _tiles_for_clamped_roi(
    roi: RoiV06,
    volume_dims: Tuple[int, int, int],
    tile_size: Tuple[int, int, int],
    tiles_per_axis: Tuple[int, int, int],
) -> Iterable[TileIndexV07]:
    """
    Compute the set of tile indices that intersect a clamped ROI.

    Assumes:
      - roi is already clamped to [0, volume_dims)
      - roi.w/h/d may be zero (empty)
    """
    if roi.w <= 0 or roi.h <= 0 or roi.d <= 0:
        return []

    x0, y0, z0 = roi.x, roi.y, roi.z
    x1 = roi.x + roi.w
    y1 = roi.y + roi.h
    z1 = roi.z + roi.d

    tx, ty, tz = tile_size
    nx, ny, nz = tiles_per_axis

    # Map voxel coordinates to tile indices (inclusive ranges)
    tx_min = max(0, x0 // tx)
    ty_min = max(0, y0 // ty)
    tz_min = max(0, z0 // tz)

    tx_max = min(nx - 1, (x1 - 1) // tx)
    ty_max = min(ny - 1, (y1 - 1) // ty)
    tz_max = min(nz - 1, (z1 - 1) // tz)

    if tx_min > tx_max or ty_min > ty_max or tz_min > tz_max:
        return []

    for tz_idx in range(tz_min, tz_max + 1):
        for ty_idx in range(ty_min, ty_max + 1):
            for tx_idx in range(tx_min, tx_max + 1):
                yield TileIndexV07(tx=tx_idx, ty=ty_idx, tz=tz_idx)


def load_tile_bytes_for_roi(
    roi: RoiV06,
    root: Path | str,
) -> Dict[TileIndexV07, bytes]:
    """
    Given a global ROI and a tile pack folder, return the tile bytes
    for all tiles that intersect that ROI.

    This does NOT reconstruct the final ROI tensor — it only answers:
    “which tiles matter, and what are their raw bytes?”.
    """
    root_path = Path(root)
    manifest_path = root_path / TILE_MANIFEST_FILENAME
    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Tile manifest not found at {manifest_path}. "
            "Did you call save_tile_pack_to_folder()?"
        )

    with manifest_path.open("r", encoding="utf-8") as f:
        manifest = json.load(f)

    volume_dims = tuple(manifest["volume_dims"])
    tile_size = tuple(manifest["tile_size"])
    tiles_per_axis = tuple(manifest["tiles_per_axis"])

    # Clamp ROI to volume bounds
    clamped = clamp_roi(roi, volume_dims)  # type: ignore[arg-type]
    if clamped.w <= 0 or clamped.h <= 0 or clamped.d <= 0:
        return {}

    result: Dict[TileIndexV07, bytes] = {}
    for idx in _tiles_for_clamped_roi(clamped, volume_dims, tile_size, tiles_per_axis):
        name = tile_index_to_name(idx)
        tile_path = root_path / name
        if not tile_path.exists():
            # It is possible that some tiles were skipped in tiling.
            continue
        with tile_path.open("rb") as f:
            result[idx] = f.read()

    return result
