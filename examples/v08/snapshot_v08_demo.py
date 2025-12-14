from __future__ import annotations

"""
examples/v08/snapshot_v08_demo.py

CIVD v0.8 snapshot demo matched to the CURRENT implementation:

- write_snapshot_v08 requires volume_buf (bytes)
- read_snapshot_v08 returns (header, spec, volume_buf) OR (header, spec, volume_buf, meta)
"""

import json
import os
import tempfile
from typing import Any, Dict, Tuple, Optional

import numpy as np

from corpus_informaticus import (
    VolumeSpecV06,
    RoiV06,
    read_region_from_bytes,
    write_snapshot_v08,
    read_snapshot_v08,
)


def _coerce_meta(meta: Any) -> Dict[str, Any]:
    if meta is None:
        return {}
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, (bytes, bytearray)):
        try:
            return json.loads(meta.decode("utf-8"))
        except Exception:
            return {"_raw_meta_bytes_len": len(meta)}
    return {"_meta_repr": repr(meta)}


def _is_bytes_like(x: Any) -> bool:
    return isinstance(x, (bytes, bytearray, memoryview))


def _unpack_read_snapshot(out: Any) -> Tuple[Any, VolumeSpecV06, bytes, Dict[str, Any]]:
    """
    Normalize possible read_snapshot_v08 outputs into:

        (header, spec, buf_bytes, meta_dict)

    Supported shapes:
      - (header, spec, buf)
      - (header, spec, buf, meta)
      - {"header":..., "spec":..., "buf":..., "meta":...}
    """
    if isinstance(out, dict):
        header = out.get("header") or out.get("hdr")
        spec = out.get("spec") or out.get("volume_spec")
        buf = out.get("buf") or out.get("buffer") or out.get("volume_buf") or out.get("volume_bytes")
        meta = out.get("meta") or out.get("metadata") or out.get("capsule_meta")
        if spec is None or buf is None:
            raise TypeError("read_snapshot_v08 returned dict but missing spec or buf.")
        if not isinstance(spec, VolumeSpecV06):
            raise TypeError(f"Expected spec to be VolumeSpecV06, got {type(spec)}")
        if not _is_bytes_like(buf):
            raise TypeError(f"Expected buf to be bytes-like, got {type(buf)}")
        return header, spec, bytes(buf), _coerce_meta(meta)

    if isinstance(out, (tuple, list)):
        if len(out) == 3:
            header, spec, buf = out
            meta = {}
        elif len(out) == 4:
            header, spec, buf, meta = out
        else:
            raise TypeError(f"Unsupported tuple size from read_snapshot_v08: {len(out)}")

        if not isinstance(spec, VolumeSpecV06):
            raise TypeError(f"Expected element[1] to be VolumeSpecV06, got {type(spec)}")
        if not _is_bytes_like(buf):
            raise TypeError(f"Expected element[2] to be bytes-like, got {type(buf)}")

        return header, spec, bytes(buf), _coerce_meta(meta)

    raise TypeError(f"Unsupported return from read_snapshot_v08: {type(out)}")


def main() -> None:
    print("[v0.8 demo] Building synthetic volume...")

    # Build synthetic volume: shape (z, y, x, C)
    z, y, x, c = 8, 12, 16, 4
    vol = np.zeros((z, y, x, c), dtype=np.uint8)

    zz, yy, xx = np.indices((z, y, x), dtype=np.uint16)
    base = (xx + 2 * yy + 3 * zz) % 256
    for ch in range(c):
        vol[..., ch] = ((base * (ch + 1)) % 256).astype(np.uint8)

    # Spec uses dims in (x, y, z)
    spec = VolumeSpecV06(
        dims=(x, y, z),
        channels=c,
        dtype="uint8",
        order="C",
        signature="C_CONTIG",
    )

    meta = {"mission": "v08_demo", "schema": "civd.meta.v1"}

    outdir = tempfile.mkdtemp()
    path = os.path.join(outdir, "demo_snapshot_v08.civd")

    volume_buf = vol.tobytes()

    print("[v0.8 demo] Writing snapshot:", path)
    write_snapshot_v08(
        path=path,
        volume_buf=volume_buf,
        spec=spec,
        meta=meta,
    )

    print("[v0.8 demo] Reading snapshot back...")
    header, spec2, buf, meta2 = _unpack_read_snapshot(read_snapshot_v08(path))

    def hget(obj: Any, key: str, default: Any = None) -> Any:
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    print("[v0.8 demo] Header:")
    print("  version :", hget(header, "version", hget(header, "schema_version", "<?>")))
    print("  dims    :", hget(header, "dims", hget(header, "dimensions", spec2.dims)))
    print("  channels:", hget(header, "channels", spec2.channels))
    print("  dtype   :", hget(header, "dtype", spec2.dtype))
    print("[v0.8 demo] Meta keys:", sorted(meta2.keys()))
    print("[v0.8 demo] Spec readback dims:", spec2.dims)

    # ROI extraction using v0.6 reader over the snapshot buffer
    roi = RoiV06(x=3, y=4, z=2, w=6, h=4, d=3)

    roi_tensor = read_region_from_bytes(
        buf=buf,
        spec=spec2,
        x=roi.x,
        y=roi.y,
        z=roi.z,
        w=roi.w,
        h=roi.h,
        d=roi.d,
        channels=None,
        copy=True,
    )

    expected = vol[
        roi.z : roi.z + roi.d,
        roi.y : roi.y + roi.h,
        roi.x : roi.x + roi.w,
        :,
    ]

    print("[v0.8 demo] ROI matches original:", np.array_equal(roi_tensor, expected))
    print("[v0.8 demo] Done.")


if __name__ == "__main__":
    main()
