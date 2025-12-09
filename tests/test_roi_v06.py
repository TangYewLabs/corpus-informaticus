"""
Basic sanity tests for CIVD v0.6 ROI utilities.

These tests focus on:
- ROI clamping against volume dimensions
- Conversion of ROI → Python slices

They assume the following public API in roi_v06.py:

    from dataclasses import dataclass
    @dataclass
    class RoiV06:
        x: int
        y: int
        z: int
        w: int
        h: int
        d: int

    def clamp_roi(roi: RoiV06, dims: tuple[int, int, int]) -> RoiV06: ...
    def roi_to_slices(roi: RoiV06) -> tuple[slice, slice, slice]: ...
"""

from corpus_informaticus.roi_v06 import RoiV06, clamp_roi, roi_to_slices


def _roi_to_tuple(roi: RoiV06) -> tuple[int, int, int, int, int, int]:
    """Helper to compare ROI values as a tuple."""
    return (roi.x, roi.y, roi.z, roi.w, roi.h, roi.d)


def test_roi_inside_bounds():
    """
    ROI completely inside the volume should be unchanged after clamping.
    """
    dims = (10, 8, 6)  # (X, Y, Z)

    roi = RoiV06(x=2, y=1, z=0, w=3, h=2, d=2)
    clamped = clamp_roi(roi, dims)

    assert _roi_to_tuple(clamped) == _roi_to_tuple(roi), (
        "ROI that is already inside bounds should not be modified by clamp_roi()"
    )

    z_s, y_s, x_s = roi_to_slices(clamped)

    # Check that slices produce the expected index ranges
    assert (z_s.start, z_s.stop) == (roi.z, roi.z + roi.d)
    assert (y_s.start, y_s.stop) == (roi.y, roi.y + roi.h)
    assert (x_s.start, x_s.stop) == (roi.x, roi.x + roi.w)


def test_roi_clamped_on_negative_and_overflow():
    """
    ROI that starts negative or extends beyond volume dims should be clamped
    to [0, dim) in each axis, with width/height/depth adjusted accordingly.
    """
    dims = (10, 8, 6)  # (X, Y, Z)

    # Start far outside on the negative side and overshoot on the positive side
    roi = RoiV06(x=-5, y=-3, z=-1, w=50, h=50, d=50)
    clamped = clamp_roi(roi, dims)

    # After clamping we expect:
    # - origin at (0,0,0)
    # - w,h,d cropped to the volume dimensions
    assert _roi_to_tuple(clamped) == (0, 0, 0, 10, 8, 6), (
        f"Unexpected clamped ROI for dims={dims}: {_roi_to_tuple(clamped)}"
    )

    z_s, y_s, x_s = roi_to_slices(clamped)

    # Slices should reflect the clamped box: full volume in each axis
    assert (z_s.start, z_s.stop) == (0, 6)
    assert (y_s.start, y_s.stop) == (0, 8)
    assert (x_s.start, x_s.stop) == (0, 10)


def test_roi_partial_overflow_on_upper_edges():
    """
    ROI that starts inside but runs off the upper edges should be cropped
    only on the overflowing side.
    """
    dims = (10, 8, 6)  # (X, Y, Z)

    roi = RoiV06(x=8, y=7, z=5, w=10, h=10, d=10)
    clamped = clamp_roi(roi, dims)

    # X: starts at 8, max dim_x = 10 → w = 2
    # Y: starts at 7, max dim_y = 8  → h = 1
    # Z: starts at 5, max dim_z = 6  → d = 1
    assert _roi_to_tuple(clamped) == (8, 7, 5, 2, 1, 1), (
        f"Unexpected clamped ROI for upper-edge overflow: {_roi_to_tuple(clamped)}"
    )

    z_s, y_s, x_s = roi_to_slices(clamped)

    assert (z_s.start, z_s.stop) == (5, 6)
    assert (y_s.start, y_s.stop) == (7, 8)
    assert (x_s.start, x_s.stop) == (8, 10)


if __name__ == "__main__":
    # Minimal runner so you can call:
    #    python tests/test_roi_v06.py
    # without needing pytest installed.
    tests = [
        test_roi_inside_bounds,
        test_roi_clamped_on_negative_and_overflow,
        test_roi_partial_overflow_on_upper_edges,
    ]

    for t in tests:
        t()
        print(f"{t.__name__}: OK")

    print("All ROI v0.6 tests passed.")
