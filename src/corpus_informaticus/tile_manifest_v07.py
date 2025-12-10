"""
tile_manifest_v07.py — CIVD v0.7 tiling and scaling helpers.

This module describes how a large logical volume is split into smaller
tiles for streaming and region-of-interest access.

It is purely a *logical* description:
- how big the global volume is (dims)
- how big each tile is (tile)
- how many tiles exist (grid_dims)
- basic metadata about dtype/channels/layout

Actual bytes are handled by higher-level code (e.g., tiler_v07 or CIVD codecs).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Tuple, Optional


# ---------------------------------------------------------------------------
# Tile indices and grid specification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TileIndexV07:
    """
    Index of a single tile in the 3D grid.

    tx, ty, tz are integer coordinates in tile-space.
    """
    tx: int
    ty: int
    tz: int

    def as_tuple(self) -> Tuple[int, int, int]:
        return (self.tx, self.ty, self.tz)


@dataclass(frozen=True)
class TileGridSpecV07:
    """
    Logical description of how a volume is divided into tiles.

    dims:
        Global volume dimensions in voxels: (x, y, z).
    tile:
        Tile size in voxels: (tile_x, tile_y, tile_z).
    """

    dims: Tuple[int, int, int]
    tile: Tuple[int, int, int]

    def __post_init__(self) -> None:
        x, y, z = self.dims
        tx, ty, tz = self.tile
        if x <= 0 or y <= 0 or z <= 0:
            raise ValueError(f"dims must be positive, got {self.dims}")
        if tx <= 0 or ty <= 0 or tz <= 0:
            raise ValueError(f"tile must be positive, got {self.tile}")

    def grid_dims(self) -> Tuple[int, int, int]:
        """
        Number of tiles along each axis, using ceil division.
        """
        x, y, z = self.dims
        tx, ty, tz = self.tile

        def ceil_div(a: int, b: int) -> int:
            return (a + b - 1) // b

        return (
            ceil_div(x, tx),
            ceil_div(y, ty),
            ceil_div(z, tz),
        )

    def tile_count(self) -> int:
        gx, gy, gz = self.grid_dims()
        return gx * gy * gz

    def tile_bounds(self, idx: TileIndexV07) -> Tuple[int, int, int, int, int, int]:
        """
        Return global voxel bounds for a tile:

            (x0, x1, y0, y1, z0, z1)

        where x1, y1, z1 are exclusive bounds.
        """
        x, y, z = self.dims
        tx, ty, tz = self.tile
        gx, gy, gz = self.grid_dims()

        if not (0 <= idx.tx < gx and 0 <= idx.ty < gy and 0 <= idx.tz < gz):
            raise ValueError(
                f"Tile index {idx} out of range for grid_dims={self.grid_dims()}"
            )

        x0 = idx.tx * tx
        y0 = idx.ty * ty
        z0 = idx.tz * tz

        x1 = min(x0 + tx, x)
        y1 = min(y0 + ty, y)
        z1 = min(z0 + tz, z)

        return x0, x1, y0, y1, z0, z1


# ---------------------------------------------------------------------------
# Manifest: tiling + volume metadata
# ---------------------------------------------------------------------------


@dataclass
class TileManifestV07:
    """
    High-level tiling manifest for a volume.

    This is intended to be stored as JSON (e.g. alongside a CIVD capsule),
    so that a reader can know how tiles are arranged and how to interpret
    the voxel values.

    Fields:
        version:
            Logical tiling version, e.g. "0.7".
        grid:
            TileGridSpecV07 describing dims and tile sizes.
        channels:
            Number of channels per voxel.
        dtype:
            String name of the data type, e.g. "uint8", "float32".
        order:
            Memory order when reconstructing dense tensors: "C" or "F".
        signature:
            Layout signature. For now we default to "C_CONTIG" for a
            C-contiguous dense 4D array (z, y, x, C).
        compressor:
            Optional text label for any compression scheme used inside
            tiles (e.g. "none", "lz4", "zstd"). No behavior is enforced
            here; this is a hint for higher-level code.
    """

    version: str
    grid: TileGridSpecV07
    channels: int
    dtype: str
    order: str = "C"
    signature: str = "C_CONTIG"
    compressor: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize to a JSON-friendly dict.
        """
        return {
            "schema": "civd.tiling.v0.7",
            "version": self.version,
            "dims": list(self.grid.dims),
            "tile": list(self.grid.tile),
            "channels": int(self.channels),
            "dtype": str(self.dtype),
            "order": str(self.order),
            "signature": str(self.signature),
            "compressor": self.compressor,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TileManifestV07":
        """
        Deserialize from a JSON-like dict.
        """
        dims = tuple(data["dims"])
        tile = tuple(data["tile"])
        grid = TileGridSpecV07(dims=dims, tile=tile)
        return cls(
            version=str(data.get("version", "0.7")),
            grid=grid,
            channels=int(data["channels"]),
            dtype=str(data["dtype"]),
            order=str(data.get("order", "C")),
            signature=str(data.get("signature", "C_CONTIG")),
            compressor=data.get("compressor"),
        )


# ---------------------------------------------------------------------------
# Heuristic helpers
# ---------------------------------------------------------------------------


def default_tile_for_dims(
    dims: Tuple[int, int, int],
    max_tile: Tuple[int, int, int] = (64, 64, 64),
) -> Tuple[int, int, int]:
    """
    Choose a simple default tile size for a given volume.

    Strategy:
        - Cap tile size at max_tile.
        - Never make tiles larger than the volume itself.
        - This defaults to 64^3 for large volumes, but shrinks gracefully
          for smaller volumes.

    This is intentionally conservative; more advanced heuristics can be added
    later without breaking the API.
    """
    x, y, z = dims
    tx = min(x, max_tile[0])
    ty = min(y, max_tile[1])
    tz = min(z, max_tile[2])
    return (tx, ty, tz)


def make_manifest_for_volume(
    dims: Tuple[int, int, int],
    channels: int,
    dtype: str = "uint8",
    order: str = "C",
    signature: str = "C_CONTIG",
    compressor: Optional[str] = None,
    tile: Optional[Tuple[int, int, int]] = None,
    version: str = "0.7",
) -> TileManifestV07:
    """
    Convenience helper: build a TileManifestV07 from a simple volume spec.

    Example:
        manifest = make_manifest_for_volume(
            dims=(512, 512, 256),
            channels=4,
            dtype="uint8",
        )
    """
    if tile is None:
        tile = default_tile_for_dims(dims)
    grid = TileGridSpecV07(dims=dims, tile=tile)
    return TileManifestV07(
        version=version,
        grid=grid,
        channels=channels,
        dtype=dtype,
        order=order,
        signature=signature,
        compressor=compressor,
    )
