"""
tile_pack_demo.py — CIVD v0.7 tiling + v0.6 ROI demo.

What this shows:

1. Build a synthetic dense volume (z, y, x, C) in memory.
2. Describe it with VolumeSpecV06.
3. Use the v0.7 tiler to:
   - split the volume into 3D tiles
   - write them as a tile pack in a folder
4. Define a Region Of Interest (ROI) in world voxel coordinates.
5. Ask the tiler: “which tiles intersect this ROI?” and load only those.

This is deliberately simple and does NOT yet:
- Reconstruct the exact ROI tensor from tiles.
- Integrate with a .civd on-disk layout.

It’s a sanity check that:
- v0.6 volume spec + v0.7 tiling metadata + ROI logic all agree.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import numpy as np

from corpus_informaticus.roi_v06 import VolumeSpecV06, RoiV06
from corpus_informaticus.tile_pack_v07 import (
    tile_volume_buffer,
    save_tile_pack_to_folder,
    load_tile_bytes_for_roi,
)


def build_demo_volume(
    dims: Tuple[int, int, int] = (32, 32, 32),
    channels: int = 3,
) -> Tuple[bytes, VolumeSpecV06]:
    """
    Build a small synthetic volume:

        dims = (x, y, z)
        layout = (z, y, x, C)

    Channel semantics (for demo only):
      - C0: x coordinate modulo 256
      - C1: y coordinate modulo 256
      - C2: z coordinate modulo 256
    """
    x, y, z = dims
    spec = VolumeSpecV06(dims=dims, channels=channels, dtype="uint8", order="C")

    # Create coordinate grids
    xs = np.arange(x, dtype=np.uint8)
    ys = np.arange(y, dtype=np.uint8)
    zs = np.arange(z, dtype=np.uint8)

    # Broadcast to (z, y, x)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="xy")  # shapes: (y, x, z)
    # Reorder to (z, y, x) to match our volume layout
    X = np.transpose(X, (2, 0, 1))
    Y = np.transpose(Y, (2, 0, 1))
    Z = np.transpose(Z, (2, 0, 1))

    # Stack into channels
    # vol shape: (z, y, x, C)
    vol = np.stack([X, Y, Z], axis=-1).astype(np.uint8)

    print(f"[demo] Built volume with shape {vol.shape} (z, y, x, C)")

    buf = vol.tobytes()
    expected = spec.expected_nbytes()
    assert len(buf) == expected, f"Buffer size {len(buf)} != expected {expected}"

    return buf, spec


def main() -> None:
    # ------------------------------------------------------------------
    # 1. Build synthetic volume & spec
    # ------------------------------------------------------------------
    volume_buf, spec = build_demo_volume(dims=(32, 32, 32), channels=3)

    # ------------------------------------------------------------------
    # 2. Tile the volume using v0.7 tiler
    # ------------------------------------------------------------------
    tile_size = (16, 16, 16)  # (tx, ty, tz)
    print(f"[demo] Tiling volume dims={spec.dims} with tile_size={tile_size}")

    tiling_spec, tiles_dict, manifest = tile_volume_buffer(
        volume_buf,
        spec,
        tile_size=tile_size,
    )

    print(f"[demo] Tiling spec: volume_dims={tiling_spec.volume_dims}, "
          f"tile_size={tiling_spec.tile_size}, tiles_per_axis={tiling_spec.tiles_per_axis}")
    print(f"[demo] Total tiles produced: {len(tiles_dict)}")

    # ------------------------------------------------------------------
    # 3. Save tile pack to folder
    # ------------------------------------------------------------------
    out_root = Path("examples/v07/tile_pack_demo_out")
    out_root.mkdir(parents=True, exist_ok=True)

    print(f"[demo] Saving tile pack to folder: {out_root}")
    save_tile_pack_to_folder(out_root, tiling_spec, tiles_dict, manifest)

    # Quick listing
    print("[demo] Files written:")
    for path in sorted(out_root.glob("*.bin")):
        print("   ", path.name)
    manifest_path = out_root / "tiling_manifest.json"
    if manifest_path.exists():
        print("    ", manifest_path.name)

    # ------------------------------------------------------------------
    # 4. Define a Region Of Interest (ROI) in global voxel coordinates
    # ------------------------------------------------------------------
    # Example: a 20x20x20 cube starting at (x=8, y=8, z=8)
    roi = RoiV06(x=8, y=8, z=8, w=20, h=20, d=20)
    print(f"[demo] ROI: origin=({roi.x}, {roi.y}, {roi.z}), "
          f"size=({roi.w}, {roi.h}, {roi.d})")

    # ------------------------------------------------------------------
    # 5. Ask: which tiles intersect this ROI? Load only those tiles.
    # ------------------------------------------------------------------
    tiles_for_roi = load_tile_bytes_for_roi(roi, out_root)
    print(f"[demo] Tiles intersecting ROI: {len(tiles_for_roi)}")

    for idx, tbuf in sorted(tiles_for_roi.items(), key=lambda kv: (kv[0].tz, kv[0].ty, kv[0].tx)):
        print(f"   tile (tx={idx.tx}, ty={idx.ty}, tz={idx.tz}) -> {len(tbuf)} bytes")

    print("[demo] Done. This demonstrates:")
    print("  - v0.6 VolumeSpec + dense buffer")
    print("  - v0.7 tiling into per-tile binaries")
    print("  - ROI query to choose tiles relevant to a region-of-interest")


if __name__ == "__main__":
    main()
