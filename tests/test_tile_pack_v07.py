"""
test_tile_pack_v07.py — tests for CIVD v0.7 tiling utilities.

These tests exercise:

- TileIndexV07 <-> filename roundtrip
- Tiling a dense VolumeSpecV06 buffer into per-tile binaries
- Writing a tile pack folder + JSON manifest
- Loading the manifest back into a TilingSpecV07
- Querying which tiles intersect a given RoiV06

They are intentionally small and deterministic so they can run quickly.
"""

from __future__ import annotations

import os
import shutil
from typing import Tuple

import numpy as np

from corpus_informaticus.roi_v06 import VolumeSpecV06, RoiV06
from corpus_informaticus.tile_manifest_v07 import TileIndexV07
from corpus_informaticus.tile_pack_v07 import (
    TILE_MANIFEST_FILENAME,
    TilingSpecV07,
    load_tile_manifest,
    name_to_tile_index,
    query_tiles_for_roi,
    tile_index_to_name,
    tile_volume_buffer,
    write_tile_pack,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_test_volume(
    dims: Tuple[int, int, int] = (16, 16, 16),
    channels: int = 2,
) -> Tuple[bytes, VolumeSpecV06]:
    """
    Build a deterministic dense volume of shape (z, y, x, C) with dtype=uint8.

    Pattern:
      channel 0: ramp mod 256
      channel 1: (ramp * 3) mod 256

    Computation is done in uint16 to avoid overflow issues, then cast to uint8.
    """
    x, y, z = dims
    spec = VolumeSpecV06(dims=dims, channels=channels, dtype="uint8", order="C")

    total_voxels = x * y * z

    # Use uint16 for intermediate math, then downcast.
    base16 = np.arange(total_voxels, dtype=np.uint16).reshape((z, y, x))

    ch0 = (base16 % 256).astype(np.uint8)
    ch1 = ((base16 * 3) % 256).astype(np.uint8)

    vol = np.zeros((z, y, x, channels), dtype=np.uint8)
    vol[..., 0] = ch0
    if channels > 1:
        vol[..., 1] = ch1

    buf = vol.tobytes()
    return buf, spec


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_tile_name_roundtrip() -> None:
    idx = TileIndexV07(tx=1, ty=2, tz=3)
    name = tile_index_to_name(idx)
    parsed = name_to_tile_index(name)

    assert name == "tile_tx1_ty2_tz3.bin", f"Unexpected tile filename: {name}"
    assert parsed == idx, f"Roundtrip failed: {parsed!r} != {idx!r}"

    print("test_tile_name_roundtrip: OK")


def test_tiling_basic() -> None:
    buf, spec = _make_test_volume(dims=(16, 16, 16), channels=2)

    tile_size = (8, 8, 8)
    tiling_spec, tiles = tile_volume_buffer(buf, spec, tile_size=tile_size)

    # Check tiling spec
    assert tiling_spec.volume_dims == (16, 16, 16)
    assert tiling_spec.tile_size == tile_size
    assert tiling_spec.tiles_per_axis == (2, 2, 2)

    # We expect 2 * 2 * 2 = 8 tiles
    assert len(tiles) == 8, f"Expected 8 tiles, got {len(tiles)}"

    # Each tile is at most 8x8x8 voxels with 2 channels, uint8
    # That means 8 * 8 * 8 * 2 = 1024 bytes per full tile.
    for idx, tile_buf in tiles.items():
        assert isinstance(idx, TileIndexV07)
        assert isinstance(tile_buf, (bytes, bytearray))
        assert len(tile_buf) == 8 * 8 * 8 * 2, f"Unexpected tile size: {len(tile_buf)}"

    print("test_tiling_basic: OK")


def test_write_pack_and_manifest() -> None:
    buf, spec = _make_test_volume(dims=(16, 16, 16), channels=2)
    tile_size = (8, 8, 8)
    tiling_spec, tiles = tile_volume_buffer(buf, spec, tile_size=tile_size)

    out_dir = "tmp_test_tile_pack_v07"
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    write_tile_pack(out_dir, tiling_spec, tiles)

    # Manifest must exist
    manifest_path = os.path.join(out_dir, TILE_MANIFEST_FILENAME)
    assert os.path.isfile(manifest_path), "Manifest file was not written"

    # A few tile files must exist
    sample_idx = TileIndexV07(tx=0, ty=0, tz=0)
    sample_name = tile_index_to_name(sample_idx)
    sample_path = os.path.join(out_dir, sample_name)
    assert os.path.isfile(sample_path), f"Sample tile file missing: {sample_name}"

    # Load manifest and compare tiling spec
    loaded_spec = load_tile_manifest(out_dir)
    assert isinstance(loaded_spec, TilingSpecV07)
    assert loaded_spec.volume_dims == tiling_spec.volume_dims
    assert loaded_spec.tile_size == tiling_spec.tile_size
    assert loaded_spec.tiles_per_axis == tiling_spec.tiles_per_axis

    # Clean up
    shutil.rmtree(out_dir)

    print("test_write_pack_and_manifest: OK")


def test_query_tiles_for_full_volume_roi() -> None:
    buf, spec = _make_test_volume(dims=(16, 16, 16), channels=2)
    tile_size = (8, 8, 8)
    tiling_spec, tiles = tile_volume_buffer(buf, spec, tile_size=tile_size)

    # Full-volume ROI should intersect all tiles
    roi = RoiV06(x=0, y=0, z=0, w=16, h=16, d=16)
    selected = query_tiles_for_roi(tiling_spec, roi)

    # Expect exactly 8 tiles for a 2x2x2 layout
    assert len(selected) == 8, f"Expected 8 tiles for full-volume ROI, got {len(selected)}"

    expected_indices = {
        TileIndexV07(tx=0, ty=0, tz=0),
        TileIndexV07(tx=1, ty=0, tz=0),
        TileIndexV07(tx=0, ty=1, tz=0),
        TileIndexV07(tx=1, ty=1, tz=0),
        TileIndexV07(tx=0, ty=0, tz=1),
        TileIndexV07(tx=1, ty=0, tz=1),
        TileIndexV07(tx=0, ty=1, tz=1),
        TileIndexV07(tx=1, ty=1, tz=1),
    }

    assert set(selected) == expected_indices, (
        f"ROI tile set mismatch.\nExpected: {expected_indices}\nGot:      {set(selected)}"
    )

    print("test_query_tiles_for_full_volume_roi: OK")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    test_tile_name_roundtrip()
    test_tiling_basic()
    test_write_pack_and_manifest()
    test_query_tiles_for_full_volume_roi()
    print("All v0.7 tiling tests passed.")


if __name__ == "__main__":
    main()
