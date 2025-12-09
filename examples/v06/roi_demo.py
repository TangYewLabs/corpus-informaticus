"""
examples/v06/roi_demo.py

Small demonstration of CIVD v0.6 ROI helpers:
- Builds a synthetic dense volume.
- Serializes it to bytes.
- Uses roi_v06 to extract a region-of-interest.
"""

from __future__ import annotations
import numpy as np

from corpus_informaticus.roi_v06 import (
    VolumeSpecV06,
    read_region_from_bytes,
    full_volume_from_bytes,
)


def main() -> None:
    dims = (8, 8, 8)
    channels = 4
    spec = VolumeSpecV06(
        dims=dims,
        channels=channels,
        dtype="uint8",
        order="C",
        signature="C_CONTIG"
    )

    x, y, z = dims
    grid = np.zeros((z, y, x, channels), dtype=np.uint8)

    for zz in range(z):
        for yy in range(y):
            for xx in range(x):
                grid[zz, yy, xx, 0] = xx     # X coordinate
                grid[zz, yy, xx, 1] = yy     # Y coordinate
                grid[zz, yy, xx, 2] = zz     # Z coordinate
                grid[zz, yy, xx, 3] = 255    # Tag / mask

    buf = grid.tobytes(order="C")

    vol = full_volume_from_bytes(buf, spec)
    print("Full volume shape:", vol.shape)

    roi = read_region_from_bytes(
        buf,
        spec,
        x=2, y=3, z=1,
        w=2, h=2, d=2,
        channels=[0, 1, 2, 3],
    )

    print("ROI shape:", roi.shape)

    for iz in range(roi.shape[0]):
        for iy in range(roi.shape[1]):
            for ix in range(roi.shape[2]):
                vx = int(roi[iz, iy, ix, 0])
                vy = int(roi[iz, iy, ix, 1])
                vz = int(roi[iz, iy, ix, 2])
                tag = int(roi[iz, iy, ix, 3])
                print(f"  voxel @ ({vx}, {vy}, {vz}) tag={tag}")


if __name__ == "__main__":
    main()
