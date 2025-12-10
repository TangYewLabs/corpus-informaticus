"""
examples/v07/streaming_demo.py

Show which tiles are needed for a given ROI, simulating a "streaming" scenario.
"""

from __future__ import annotations

import numpy as np

from corpus_informaticus.tile_manifest_v07 import make_manifest_for_volume
from corpus_informaticus.tiler_v07 import tile_volume, tiles_for_roi
from corpus_informaticus.roi_v06 import RoiV06


def main() -> None:
    dims = (256, 256, 128)  # (x, y, z)
    channels = 3

    x, y, z = dims
    vol = np.random.randint(
        0, 255, size=(z, y, x, channels), dtype=np.uint8
    )

    manifest = make_manifest_for_volume(
        dims=dims,
        channels=channels,
        dtype="uint8",
        tile=(64, 64, 32),
    )

    tiles = tile_volume(vol, manifest)

    # Region of interest: a local cube in the middle of the volume.
    roi = RoiV06(x=80, y=80, z=40, w=64, h=64, d=32)

    tile_indices = tiles_for_roi(manifest, roi)

    print("=== Streaming ROI Demo (v0.7) ===")
    print(f"Volume dims (x,y,z): {dims}")
    print(f"Tile size: {manifest.grid.tile}")
    print(f"Grid dims: {manifest.grid.grid_dims()}")
    print(f"Total tiles: {manifest.grid.tile_count()}")
    print()
    print(f"ROI: {roi}")
    print(f"Tiles touching ROI: {len(tile_indices)}")

    for idx in tile_indices:
        x0, x1, y0, y1, z0, z1 = manifest.grid.tile_bounds(idx)
        print(
            f"  Tile {idx.as_tuple()} -> "
            f"x[{x0}:{x1}), y[{y0}:{y1}), z[{z0}:{z1})"
        )

    # In a real system, you would now:
    #   1) Load only these tiles from disk/network.
    #   2) Extract the ROI voxels from those tiles.
    # This demo just prints which tiles would be needed.


if __name__ == "__main__":
    main()
