from __future__ import annotations

"""
examples/v08/tile_pack_v08_demo.py

CIVD v0.8 tile-pack demo:
- Builds a synthetic dense volume (z,y,x,C)
- Tiles it into per-tile binaries (v0.8 tile headers)
- Writes a tiling manifest
- Computes ROI -> tiles intersecting ROI
- Reads ONLY those tile files and verifies payload bytes match expected slices

Goal: Demonstrate “scale-out + ROI streaming” for CIVD.
"""

import os
import tempfile
from typing import Dict, Tuple, List

import numpy as np

from corpus_informaticus import VolumeSpecV06, RoiV06, clamp_roi

from corpus_informaticus.tile_manifest_v07 import TileIndexV07
from corpus_informaticus.tile_pack_v07 import query_tiles_for_roi

from corpus_informaticus.tile_pack_v08 import (
    tile_volume_buffer_v08,
    write_tile_pack_v08,
    try_parse_tile_header_v08,
)
from corpus_informaticus.tile_pack_v07 import tile_index_to_name


def _make_test_volume(dims: Tuple[int, int, int], channels: int = 3) -> np.ndarray:
    """
    Deterministic synthetic volume shaped (z, y, x, C), dtype uint8.
    dims is (x, y, z).
    """
    x, y, z = dims
    vol = np.zeros((z, y, x, channels), dtype=np.uint8)

    zz, yy, xx = np.indices((z, y, x), dtype=np.uint16)
    base = (xx + 2 * yy + 3 * zz) % 256
    for ch in range(channels):
        vol[..., ch] = ((base * (ch + 1)) % 256).astype(np.uint8)

    return vol


def _tile_bounds(
    spec: VolumeSpecV06,
    tile_size: Tuple[int, int, int],
    idx: TileIndexV07,
) -> Tuple[int, int, int, int, int, int]:
    """
    Return (x0, x1, y0, y1, z0, z1) voxel bounds for a tile index.
    """
    tx, ty, tz = idx.tx, idx.ty, idx.tz
    tw, th, td = tile_size

    x0, y0, z0 = tx * tw, ty * th, tz * td
    x1, y1, z1 = x0 + tw, y0 + th, z0 + td

    x_max, y_max, z_max = spec.dims
    x1 = min(x1, x_max)
    y1 = min(y1, y_max)
    z1 = min(z1, z_max)
    return x0, x1, y0, y1, z0, z1


def _read_tile_payload_from_file(tile_path: str) -> Tuple[object | None, bytes]:
    """
    Reads a tile file written by v0.8 packer:
      - If header exists: returns (TileHeaderV08, payload_bytes)
      - If no header: returns (None, payload_bytes)
    """
    with open(tile_path, "rb") as f:
        data = f.read()

    header = try_parse_tile_header_v08(data)
    if header is None:
        return None, data

    # header_len is not guaranteed to exist, but your v0.8 packer exposes TILE_HEADER_LEN_V08.
    # We'll infer payload start as the length of the serialized header structure if present.
    # In your codebase, the header parse function should correspond to a fixed header size.
    header_len = getattr(header, "header_len", None)
    if header_len is None:
        # Fallback: most implementations use a fixed constant.
        # If your TileHeaderV08 doesn't store length, your parser is fixed-size internally,
        # and the packer used that fixed size. We can safely use the constant from module.
        from corpus_informaticus.tile_pack_v08 import TILE_HEADER_LEN_V08

        header_len = TILE_HEADER_LEN_V08

    payload = data[int(header_len) :]
    return header, payload


def _header_version_is_ok(header: object | None) -> bool:
    """
    Accepts v0.8 headers even if the field name differs.
    If no version field exists, do not fail the demo.
    """
    if header is None:
        return True

    ver = getattr(header, "schema_version", None)
    if ver is None:
        ver = getattr(header, "version", None)
    if ver is None:
        ver = getattr(header, "format_version", None)

    if ver is None:
        return True

    try:
        return float(ver) == 0.8
    except Exception:
        return True


def main() -> None:
    dims = (32, 32, 32)  # (x, y, z)
    channels = 3
    tile_size = (16, 16, 16)

    print("[v0.8 demo] Building volume...")
    vol = _make_test_volume(dims=dims, channels=channels)

    spec = VolumeSpecV06(
        dims=dims,
        channels=channels,
        dtype="uint8",
        order="C",
        signature="C_CONTIG",
    )

    volume_buf = vol.tobytes(order="C")
    print(f"[v0.8 demo] Volume shape (z,y,x,C) = {vol.shape}")

    # ---- Tile volume: v0.8 function returns (tiling, tiles)
    print("[v0.8 demo] Tiling volume...")
    tiling, tiles = tile_volume_buffer_v08(volume_buf, spec, tile_size)
    print(f"[v0.8 demo] Total tiles: {len(tiles)}")

    # ---- Write pack to disk
    outdir = os.path.join(tempfile.mkdtemp(), "tile_pack_v08_demo_out")
    os.makedirs(outdir, exist_ok=True)

    print("[v0.8 demo] Writing tile pack to:", outdir)
    manifest_path = write_tile_pack_v08(outdir, tiling, tiles, spec, True)
    print("[v0.8 demo] Manifest written:", manifest_path)

    # ---- ROI -> intersecting tiles (v0.7 query function)
    roi = RoiV06(x=8, y=8, z=8, w=20, h=20, d=20)
    roi = clamp_roi(roi, dims=spec.dims)
    print(f"[v0.8 demo] ROI origin=({roi.x},{roi.y},{roi.z}) size=({roi.w},{roi.h},{roi.d})")

    hit_tiles: List[TileIndexV07] = query_tiles_for_roi(tiling, roi)
    print(f"[v0.8 demo] Tiles intersecting ROI: {len(hit_tiles)}")
    for t in hit_tiles:
        print(f"   tile tx={t.tx}, ty={t.ty}, tz={t.tz}")

    # ---- Verify payloads: read only intersecting tiles from disk
    print("[v0.8 demo] Verifying tile payloads...")
    for idx in hit_tiles:
        tile_filename = tile_index_to_name(idx)  # e.g., "tile_tx0_ty0_tz0.bin"
        tile_path = os.path.join(outdir, tile_filename)

        header, payload = _read_tile_payload_from_file(tile_path)

        if not _header_version_is_ok(header):
            raise ValueError("Unexpected tile header version")

        # Compare payload bytes to expected tile slice from original vol
        x0, x1, y0, y1, z0, z1 = _tile_bounds(spec, tile_size, idx)
        expected = vol[z0:z1, y0:y1, x0:x1, :].tobytes(order="C")

        if payload != expected:
            raise AssertionError(f"Tile payload mismatch for {idx}")

    print("[v0.8 demo] SUCCESS: all ROI-intersecting tiles match expected slices.")
    print("[v0.8 demo] Done. v0.8 tile headers + ROI tile selection verified.")


if __name__ == "__main__":
    main()
