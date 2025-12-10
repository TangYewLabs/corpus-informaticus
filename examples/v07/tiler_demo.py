"""
examples/v07/tiler_demo.py

Demonstrate tiling a synthetic volume and reconstructing it.
"""

from __future__ import annotations

import numpy as np

from corpus_informaticus.tile_manifest_v07 import make_manifest_for_volume
from corpus_informaticus.tiler_v07 import tile_volume, assemble_volume_from_tiles


def main() -> None:
    # Synthetic volume: dims=(x, y, z) => shape (z, y, x, C)
    dims = (128, 96, 48)  # (x, y, z)
    channels = 4

    x, y, z = dims
    vol = np.zeros((z, y, x, channels), dtype=np.uint8)

    # Simple pattern: encode coordinates into channels
    zz, yy, xx = np.meshgrid(
        np.arange(z), np.arange(y), np.arange(x), indexing="ij"
    )
    vol[..., 0] = xx % 256
    vol[..., 1] = yy % 256
    vol[..., 2] = zz % 256
    vol[..., 3] = (xx + yy + zz) % 256

    manifest = make_manifest_for_volume(
        dims=dims,
        channels=channels,
        dtype="uint8",
        tile=(64, 64, 32),  # explicit for the demo
    )

    print("=== Tiler v0.7 Demo ===")
    print(f"dims: {dims}")
    print(f"tile: {manifest.grid.tile}")
    print(f"grid_dims: {manifest.grid.grid_dims()}")
    print(f"tile_count: {manifest.grid.tile_count()}")

    tiles = tile_volume(vol, manifest)
    print(f"Produced {len(tiles)} tiles")

    recon = assemble_volume_from_tiles(manifest, tiles)

    equal = np.array_equal(vol, recon)
    print(f"Roundtrip equality: {equal}")


if __name__ == "__main__":
    main()
