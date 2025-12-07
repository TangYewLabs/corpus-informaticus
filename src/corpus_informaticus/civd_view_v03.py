from __future__ import annotations

import argparse
from pathlib import Path
from typing import Tuple

import numpy as np
import matplotlib.pyplot as plt

from corpus_informaticus.codec_v03 import (
    HEADER_STRUCT,
    FOOTER_STRUCT,
    CI3Header,
    dims_to_volume_size,
)
import zlib


def load_civd_volume(path: Path) -> Tuple[np.ndarray, CI3Header, bool]:
    """
    Load a CIVD v0.3 corpus from disk and return:

      - volume: np.ndarray uint8 with shape (channels, dim_z, dim_y, dim_x)
      - header: CI3Header instance
      - crc_ok: bool
    """
    blob = path.read_bytes()

    header_size = HEADER_STRUCT.size
    footer_size = FOOTER_STRUCT.size

    if len(blob) < header_size + footer_size:
        raise ValueError("Blob too small to contain header + footer")

    # Parse header
    header = CI3Header.unpack(blob[:header_size])
    header.validate_basic()

    # Compute capacity and extract volume
    capacity = dims_to_volume_size(
        header.dim_x, header.dim_y, header.dim_z, header.channels
    )

    volume_bytes = blob[header_size:-footer_size]
    if len(volume_bytes) != capacity:
        raise ValueError(
            f"Volume length {len(volume_bytes)} != capacity {capacity}"
        )

    # Parse footer / CRC
    (crc_stored,) = FOOTER_STRUCT.unpack(blob[-footer_size:])
    crc_calc = zlib.crc32(volume_bytes) & 0xFFFFFFFF
    crc_ok = crc_calc == crc_stored

    # Turn flat bytes into 4D tensor: (channels, z, y, x)
    arr = np.frombuffer(volume_bytes, dtype=np.uint8)
    arr = arr.reshape(
        (header.channels, header.dim_z, header.dim_y, header.dim_x)
    )

    return arr, header, crc_ok


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Visualize a slice of a CIVD v0.3 corpus (.civd)."
    )
    parser.add_argument(
        "path",
        type=str,
        help="Path to .civd file (e.g. examples/file_roundtrip/sample.txt.civd)",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="Channel index to view (default: 0)",
    )
    parser.add_argument(
        "--z",
        type=int,
        default=0,
        help="Z-slice index to view (default: 0)",
    )
    args = parser.parse_args()

    in_path = Path(args.path)
    if not in_path.is_file():
        raise SystemExit(f"Input file not found: {in_path}")

    volume, header, crc_ok = load_civd_volume(in_path)

    dims = (header.dim_x, header.dim_y, header.dim_z)
    channels = header.channels

    print(f"File:      {in_path}")
    print(f"Version:   {header.version:#06x}")
    print(f"dims:      {dims}  (x, y, z)")
    print(f"channels:  {channels}")
    print(f"orig_len:  {header.orig_length} bytes")
    print(f"CRC OK:    {crc_ok}")

    # Clamp / validate indices
    ch = max(0, min(args.channel, channels - 1))
    z = max(0, min(args.z, header.dim_z - 1))

    if ch != args.channel:
        print(f"[info] Adjusted channel index to {ch} (valid range 0..{channels-1})")
    if z != args.z:
        print(f"[info] Adjusted z-slice index to {z} (valid range 0..{header.dim_z-1})")

    # volume has shape (channels, dim_z, dim_y, dim_x)
    slice_2d = volume[ch, z, :, :]

    plt.figure(figsize=(5, 5))
    plt.title(
        f"CIVD v0.3 slice\nchannel={ch}, z={z}, dims={dims}, CRC OK={crc_ok}"
    )
    plt.imshow(slice_2d, cmap="gray", interpolation="nearest")
    plt.colorbar(label="byte value (0–255)")
    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()
