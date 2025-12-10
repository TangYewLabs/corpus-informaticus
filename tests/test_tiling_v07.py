"""
tests/test_tiling_v07.py

Light-weight tests for CIVD v0.7 tiling:

- Tiling + reassembly roundtrip
- tiles_for_roi returns a reasonable set of tiles
"""

from __future__ import annotations

import numpy as np

from corpus_informaticus.tile_manifest_v07 import make_manifest_for_volume
from corpus_informaticus.tiler_v07 import (
    tile_volume,
    assemble_volume_from_tiles,
    tiles_for_roi,
)
from corpus_informaticus.roi_v06 import RoiV06


def test_tiling_roundtrip() -> None:
    dims = (96, 80, 40)  # (x, y, z)
    channels = 2

    x, y, z = dims
    vol = np.arange(
        z * y * x * channels, dtype=np.int32
    ).reshape((z, y, x, channels))

    manifest = make_manifest_for_volume(
        dims=dims,
        channels=channels,
        dtype="int32",
        tile=(32, 32, 16),
    )

    tiles = tile_volume(vol, manifest)
    recon = assemble_volume_from_tiles(manifest, tiles)

    assert recon.shape == vol.shape
    assert np.array_equal(vol, recon)


def test_tiles_for_roi() -> None:
    dims = (256, 256, 128)
    channels = 3
    manifest = make_manifest_for_volume(
        dims=dims,
        channels=channels,
        dtype="uint8",
        tile=(64, 64, 32),
    )

    roi = RoiV06(x=80, y=80, z=40, w=64, h=64, d=32)
    indices = tiles_for_roi(manifest, roi)

    # Basic sanity checks
    assert len(indices) > 0
    assert len(indices) <= manifest.grid.tile_count()

    # All returned indices should be within grid bounds
    gx, gy, gz = manifest.grid.grid_dims()
    for idx in indices:
        assert 0 <= idx.tx < gx
        assert 0 <= idx.ty < gy
        assert 0 <= idx.tz < gz


if __name__ == "__main__":
    # Simple CLI harness
    print("Running test_tiling_roundtrip...")
    test_tiling_roundtrip()
    print("  OK")

    print("Running test_tiles_for_roi...")
    test_tiles_for_roi()
    print("  OK")

    print("All v0.7 tiling tests passed.")
