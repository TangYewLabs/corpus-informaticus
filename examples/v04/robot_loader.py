#!/usr/bin/env python3
"""
robot_loader.py — CIVD v0.4 "robot-side" loader demo.

Given a .civd capsule, this script:
- Uses v0.3 codec to reconstruct a 4D volumetric tensor view.
- Uses v0.4 codec to read the file table + embedded files.
- Prints a concise summary that a robot / simulator could use.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple, Dict

import numpy as np

from corpus_informaticus.codec_v03 import decode_civd_v03
from corpus_informaticus.civd_v04_codec import decode_civd_v04


def build_tensor_from_payload(
    payload: bytes,
    dims: Tuple[int, int, int],
    channels: int,
) -> np.ndarray:
    """
    Convert linear payload into (Z, Y, X, C) 4D tensor for robotics.
    """
    dim_x, dim_y, dim_z = dims
    capacity = dim_x * dim_y * dim_z * channels

    if len(payload) > capacity:
        raise ValueError(
            f"Payload length {len(payload)} exceeds volume capacity {capacity}"
        )

    flat = np.zeros(capacity, dtype=np.uint8)
    flat[: len(payload)] = np.frombuffer(payload, dtype=np.uint8)

    tensor = flat.reshape(dim_z, dim_y, dim_x, channels)
    return tensor


def load_civd_capsule(path: Path):
    """
    High-level loader that returns:
    - 4D tensor
    - files dict
    - v0.3 info (dims, channels)
    - v0.4 metadata (file_count, table sizes, etc.)
    """
    blob = path.read_bytes()

    payload, v03_info = decode_civd_v03(blob)
    dims = v03_info["dims"]
    channels = v03_info["channels"]

    tensor = build_tensor_from_payload(payload, dims, channels)

    table, files, v04_meta = decode_civd_v04(blob)

    return tensor, files, v03_info, v04_meta


def summarize_capsule(
    path: Path,
    tensor: np.ndarray,
    files: Dict[str, bytes],
    v03_info: dict,
    v04_meta: dict,
) -> None:
    """
    Human-readable summary for robots.
    """
    print("=== CIVD v0.4 Robot Loader Summary ===")
    print(f"Capsule:       {path}")
    print(f"Dims:          {v03_info['dims']}")
    print(f"Channels:      {v03_info['channels']}")
    print(f"Tensor shape:  {tensor.shape} (Z, Y, X, C)")
    print()

    print("File Table:")
    print(f"  File count:  {v04_meta.get('file_count')}")
    print(f"  Table size:  {v04_meta.get('table_size')} bytes")
    print(f"  Data region: {v04_meta.get('data_region_size')} bytes")
    print(f"  Payload size:{v04_meta.get('payload_size')} bytes")
    print()

    if not files:
        print("No embedded files.")
        return

    print("Embedded files:")
    for name, data in files.items():
        size = len(data)

        try:
            preview = data.decode("utf-8").splitlines()[0][:60]
        except UnicodeDecodeError:
            preview = "<binary>"

        print(f"- {name} ({size} bytes)")
        print(f"    preview: {preview}")
    print()

    print("Robot Notes:")
    print("  • Tensor can be fed into AI perception or simulation systems.")
    print("  • Files can contain configs, maps, mission packs, logs, etc.")
    print("  • This capsule = full robot state transfer + assets.")


def main():
    parser = argparse.ArgumentParser(
        description="Robot-side loader for CIVD v0.4 capsules."
    )
    parser.add_argument("path", help="Path to .civd capsule")
    args = parser.parse_args()

    p = Path(args.path)
    if not p.exists():
        raise SystemExit(f"File not found: {p}")

    tensor, files, v03_info, v04_meta = load_civd_capsule(p)
    summarize_capsule(p, tensor, files, v03_info, v04_meta)


if __name__ == "__main__":
    main()
