"""
roi_v06.py — CIVD v0.6 Region-of-Interest (ROI) helpers.

This module defines a small, focused API for extracting 3D regions
from a dense multi-channel volume buffer. It is deliberately generic:
it does NOT depend on the on-disk CIVD layout, only on an already
decoded dense volume (bytes + metadata).

This is the foundation for:
- CIVD v0.6 spatial snapshots
- AI / robotics region-of-interest loading
- GPU / tensor-friendly data access
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

try:
    import numpy as np
except ImportError as exc:  # pragma: no cover
    raise ImportError(
        "roi_v06 requires NumPy. Install with: pip install numpy"
    ) from exc


# ---------------------------------------------------------------------------
# Volume specification (v0.6 logical view)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VolumeSpecV06:
    """
    Logical description of a dense CIVD volume for v0.6 ROI access.

    dims:
        (x, y, z) voxel dimensions.
    channels:
        Number of channels per voxel (e.g. 4 for RGBA or multi-sensor).
    dtype:
        Name of the NumPy dtype (e.g. 'uint8', 'float32').
    order:
        Memory order: 'C' (row-major) or 'F' (column-major).
    signature:
        Logical layout / encoding. For v0.6 we support:
          - 'C_CONTIG'  : standard dense C-contiguous tensor
          - 'F_CONTIG'  : dense F-contiguous tensor
        Future:
          - 'MORTON'    : Morton / Z-order (not yet implemented here).
    """

    dims: Tuple[int, int, int]
    channels: int
    dtype: str = "uint8"
    order: str = "C"
    signature: str = "C_CONTIG"

    def voxel_count(self) -> int:
        x, y, z = self.dims
        return x * y * z

    def expected_nbytes(self) -> int:
        x, y, z = self.dims
        itemsize = np.dtype(self.dtype).itemsize
        return x * y * z * self.channels * itemsize


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------


def _volume_view_from_bytes(buf: bytes, spec: VolumeSpecV06) -> "np.ndarray":
    """
    Interpret a raw bytes buffer as a 4D volume view:

        shape = (z, y, x, channels)

    No copies are made; this returns a NumPy view over 'buf'.

    Raises ValueError if the buffer size does not match the spec.
    """
    expected = spec.expected_nbytes()
    if len(buf) != expected:
        raise ValueError(
            f"Buffer size {len(buf)} does not match expected {expected} "
            f"for dims={spec.dims}, channels={spec.channels}, dtype={spec.dtype}"
        )

    dtype = np.dtype(spec.dtype)

    if spec.signature not in ("C_CONTIG", "F_CONTIG"):
        raise NotImplementedError(
            f"Volume signature '{spec.signature}' is not implemented yet. "
            "Supported: 'C_CONTIG', 'F_CONTIG'."
        )

    # For v0.6 we standardize on internal view shape:
    #   (z, y, x, channels)
    x, y, z = spec.dims
    total_voxels = x * y * z

    arr = np.frombuffer(buf, dtype=dtype)

    if arr.size != total_voxels * spec.channels:
        raise ValueError(
            f"Buffer length {arr.size} elements does not match "
            f"voxels*channels = {total_voxels * spec.channels}"
        )

    if spec.order not in ("C", "F"):
        raise ValueError(f"Unsupported order: {spec.order!r}. Use 'C' or 'F'.")

    vol = arr.reshape((z, y, x, spec.channels), order=spec.order)
    return vol


def read_region_from_bytes(
    buf: bytes,
    spec: VolumeSpecV06,
    x: int,
    y: int,
    z: int,
    w: int,
    h: int,
    d: int,
    channels: Optional[List[int]] = None,
    copy: bool = True,
) -> "np.ndarray":
    """
    Extract a 3D region-of-interest (ROI) from a dense CIVD volume buffer.

    Parameters
    ----------
    buf:
        Raw bytes containing the volume in the layout described by 'spec'.
    spec:
        VolumeSpecV06 describing dims, channels, dtype, order, signature.
    x, y, z:
        Origin of the ROI in voxel coordinates (0-based, inclusive).
    w, h, d:
        Size of the ROI in voxels along x, y, z.
    channels:
        Optional list of channel indices to extract. If None, all channels
        are returned.
    copy:
        If True, returns a copy of the data. If False, returns a view
        over the underlying NumPy array. For safety, the default is True.

    Returns
    -------
    np.ndarray
        A 4D tensor of shape (d, h, w, C_sel) where C_sel is either
        'spec.channels' or len(channels) if subset selection is used.
    """
    vol = _volume_view_from_bytes(buf, spec)

    x0, y0, z0 = x, y, z
    x1, y1, z1 = x + w, y + h, z + d

    x_max, y_max, z_max = spec.dims

    if not (0 <= x0 < x1 <= x_max):
        raise ValueError(f"ROI x-range [{x0}, {x1}) is out of bounds [0, {x_max})")
    if not (0 <= y0 < y1 <= y_max):
        raise ValueError(f"ROI y-range [{y0}, {y1}) is out of bounds [0, {y_max})")
    if not (0 <= z0 < z1 <= z_max):
        raise ValueError(f"ROI z-range [{z0}, {z1}) is out of bounds [0, {z_max})")

    # vol shape: (z, y, x, C)
    roi = vol[z0:z1, y0:y1, x0:x1, :]

    if channels is not None:
        # Basic validation of requested channel indices.
        for c in channels:
            if c < 0 or c >= spec.channels:
                raise ValueError(
                    f"Requested channel index {c} is out of range [0, {spec.channels})"
                )
        roi = roi[..., channels]

    if copy:
        roi = roi.copy()

    return roi


# ---------------------------------------------------------------------------
# Convenience function for "full volume" read
# ---------------------------------------------------------------------------


def full_volume_from_bytes(
    buf: bytes, spec: VolumeSpecV06, copy: bool = False
) -> "np.ndarray":
    """
    Return the entire volume as a 4D tensor (z, y, x, C).

    Useful for cases where a consumer wants to ingest the full snapshot
    into GPU memory or a digital twin.
    """
    vol = _volume_view_from_bytes(buf, spec)
    return vol.copy() if copy else vol


# ---------------------------------------------------------------------------
# ROI box helpers (v0.6)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoiV06:
    """
    Simple ROI box for CIVD v0.6.

    Coordinates are in voxel space:

        x, y, z : origin (0-based, inclusive)
        w, h, d : size along x, y, z (number of voxels)
    """

    x: int
    y: int
    z: int
    w: int
    h: int
    d: int

    def as_bounds(self) -> Tuple[int, int, int, int, int, int]:
        """
        Return (x0, x1, y0, y1, z0, z1) with x1/y1/z1 as exclusive bounds.
        """
        return (
            self.x,
            self.x + self.w,
            self.y,
            self.y + self.h,
            self.z,
            self.z + self.d,
        )


def _clamp_interval(start: int, length: int, max_size: int) -> Tuple[int, int]:
    """
    Clamp a 1D interval [start, start+length) to [0, max_size).

    Returns (clamped_start, clamped_length). If the interval is empty
    after clamping, the length will be 0.
    """
    if length <= 0:
        return 0, 0

    s = max(0, start)
    e = min(max_size, start + length)

    if e <= s:
        # Fully outside; normalize to an empty interval at 0.
        return 0, 0

    return s, e - s


def clamp_roi(roi: RoiV06, dims: Tuple[int, int, int]) -> RoiV06:
    """
    Clamp an ROI to the given volume dimensions (x_max, y_max, z_max).

    This is a defensive helper so that downstream code can safely
    call roi_to_slices() without worrying about out-of-bounds indices.
    """
    x_max, y_max, z_max = dims

    x, w = _clamp_interval(roi.x, roi.w, x_max)
    y, h = _clamp_interval(roi.y, roi.h, y_max)
    z, d = _clamp_interval(roi.z, roi.d, z_max)

    return RoiV06(x=x, y=y, z=z, w=w, h=h, d=d)


def roi_to_slices(roi: RoiV06) -> Tuple[slice, slice, slice]:
    """
    Convert an ROI into NumPy slices for a (z, y, x, C) volume.

    Volume layout is assumed to be:

        vol[z, y, x, c]

    so the slices are returned in (z, y, x) order.
    """
    z0, z1 = roi.z, roi.z + roi.d
    y0, y1 = roi.y, roi.y + roi.h
    x0, x1 = roi.x, roi.x + roi.w

    return slice(z0, z1), slice(y0, y1), slice(x0, x1)


def read_region_from_bytes_roi(
    buf: bytes,
    spec: VolumeSpecV06,
    roi: RoiV06,
    channels: Optional[List[int]] = None,
    copy: bool = True,
) -> "np.ndarray":
    """
    Convenience wrapper: read a region-of-interest specified as a RoiV06.

    This simply forwards to read_region_from_bytes() using ROI fields.
    """
    return read_region_from_bytes(
        buf=buf,
        spec=spec,
        x=roi.x,
        y=roi.y,
        z=roi.z,
        w=roi.w,
        h=roi.h,
        d=roi.d,
        channels=channels,
        copy=copy,
    )
