"""
snapshot_demo.py — CIVD v0.7 snapshot + ROI demo.

This example shows:

1) Build a small synthetic dense volume (z, y, x, C).
2) Wrap it in a CIVD v0.7 snapshot with metadata.
3) Read it back from disk.
4) Extract a region-of-interest (ROI) using the v0.6 ROI helpers.
"""

from __future__ import annotations

from pathlib import Path
import tempfile

import numpy as np

from corpus_informaticus import (
    VolumeSpecV06,
    RoiV06,
    write_snapshot_v07,
    read_snapshot_v07,
    read_roi_from_snapshot_v07,
    full_volume_from_snapshot_v07,
)


def build_demo_volume(dims=(16, 12, 8), channels=4):
    """
    Build a synthetic volume with a deterministic pattern.

    dims = (x, y, z)
    returns:
        vol  : np.ndarray with shape (z, y, x, C)
        spec : VolumeSpecV06
        buf  : raw bytes (C-contiguous)
    """
    x, y, z = dims
    C = channels

    spec = VolumeSpecV06(
        dims=dims,
        channels=C,
        dtype="uint8",
        order="C",
        signature="C_CONTIG",
    )

    vol = np.zeros((z, y, x, C), dtype=np.uint8)

    for zi in range(z):
        for yi in range(y):
            for xi in range(x):
                base = (zi * 11 + yi * 5 + xi * 3) % 256
                vol[zi, yi, xi, 0] = base           # channel 0: base pattern
                if C > 1:
                    vol[zi, yi, xi, 1] = (base * 2) % 256
                if C > 2:
                    vol[zi, yi, xi, 2] = (base + 42) % 256
                if C > 3:
                    vol[zi, yi, xi, 3] = (zi * 17) % 256  # encodes z-slice index

    buf = vol.tobytes(order="C")
    return vol, spec, buf


def main():
    print("[demo] Building synthetic volume...")
    vol, spec, buf = build_demo_volume(dims=(16, 12, 8), channels=4)
    print(f"[demo] Volume shape (z, y, x, C): {vol.shape}")
    print(f"[demo] Volume dims (x, y, z): {spec.dims}, channels={spec.channels}")

    meta = {
        "schema": "civd.meta.v1",
        "mission": "snapshot_v07_demo",
        "tags": ["demo", "snapshot", "roi"],
        "group": "robot_A/demo",
        "notes": "Synthetic volume for CIVD v0.7 snapshot + ROI demo.",
    }

    # Write snapshot to a temporary directory by default
    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = Path(tmpdir) / "demo_snapshot_v07.civd"
        print(f"[demo] Writing snapshot to: {out_path}")
        blob, hdr = write_snapshot_v07(buf, spec, meta=meta, path=out_path)

        print("[demo] Snapshot header fields:")
        print(f"        version   : {hdr.version}")
        print(f"        layout    : {hdr.layout}")
        print(f"        dims      : {hdr.dims}")
        print(f"        channels  : {hdr.channels}")
        print(f"        dtype     : {hdr.dtype}")
        print(f"        signature : {hdr.signature}")
        print(f"        meta.mission: {hdr.meta.get('mission') if hdr.meta else None}")

        # Read it back using the file-based API
        print("[demo] Reading snapshot back from disk...")
        hdr2, spec2, buf2 = read_snapshot_v07(out_path)
        print(f"[demo] Read header.dimensions: {hdr2.dims}")
        print(f"[demo] Read spec.dims: {spec2.dims}")

        # Full volume tensor from snapshot
        print("[demo] Loading full volume tensor from snapshot...")
        hdr3, spec3, vol2 = full_volume_from_snapshot_v07(out_path, copy=True)
        print(f"[demo] vol2.shape: {vol2.shape}")
        print(f"[demo] vol2 dtype: {vol2.dtype}")
        print(
            f"[demo] full volume equality vs original: "
            f"{np.array_equal(vol2, vol)}"
        )

        # Define a 3D region-of-interest in voxel coordinates (x, y, z)
        roi = RoiV06(x=3, y=4, z=2, w=6, h=4, d=3)
        print(
            "[demo] ROI:", 
            f"origin=(x={roi.x}, y={roi.y}, z={roi.z}), "
            f"size=(w={roi.w}, h={roi.h}, d={roi.d})"
        )

        # Use the v0.7 helper which internally:
        #  - reads snapshot
        #  - clamps ROI against dims
        #  - calls v0.6 ROI extraction
        print("[demo] Extracting ROI from snapshot...")
        roi_arr = read_roi_from_snapshot_v07(
            out_path,
            roi,
            channels=None,   # all channels
            copy=True,
        )
        print(f"[demo] ROI tensor shape: {roi_arr.shape}")

        # Compare to direct slicing from the original volume
        z0, z1 = roi.z, roi.z + roi.d
        y0, y1 = roi.y, roi.y + roi.h
        x0, x1 = roi.x, roi.x + roi.w
        expected_roi = vol[z0:z1, y0:y1, x0:x1, :]

        same = np.array_equal(roi_arr, expected_roi)
        print(f"[demo] ROI matches direct slicing from original: {same}")

        # Show a small numeric summary so users can see it's "real data"
        print("[demo] ROI stats (per-channel min/max):")
        C = roi_arr.shape[-1]
        for c in range(C):
            ch = roi_arr[..., c]
            print(
                f"        channel {c}: "
                f"min={int(ch.min())}, max={int(ch.max())}, mean={ch.mean():.2f}"
            )

    print("[demo] Done. CIVD v0.7 snapshot + ROI demo completed.")


if __name__ == "__main__":
    main()
