from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from .ci3_types import CI3Header, HEADER_STRUCT, dims_to_volume_size


def ci3_to_numpy(path: Path) -> tuple[np.ndarray, dict]:
    """
    Load a CI3 file and return a NumPy array of shape (Z, Y, X, C)
    plus a small info dict.

    IMPORTANT:
    - We read the raw volume payload directly from the file,
      not the trimmed original payload returned by decode_ci3.
    - This gives us the full voxel grid (including unused voxels),
      which is what we want for visualization.
    """
    raw = path.read_bytes()

    if len(raw) < HEADER_STRUCT.size + 4:
        raise ValueError("File too small to be a valid CI3 corpus")

    # 1) Parse header
    header_bytes = raw[: HEADER_STRUCT.size]
    header = CI3Header.unpack(header_bytes)

    dim_x = header.dim_x
    dim_y = header.dim_y
    dim_z = header.dim_z
    channels = header.channels

    # 2) Compute volume capacity in bytes
    capacity = dims_to_volume_size(dim_x, dim_y, dim_z, channels)

    # 3) Slice out the volume payload directly from the raw file
    # Layout is: [header][volume][crc32]
    start = HEADER_STRUCT.size
    end = start + capacity

    if end + 4 > len(raw):
        raise ValueError(
            f"File too small for expected volume payload "
            f"({capacity} bytes) and CRC32 footer"
        )

    volume_bytes = raw[start:end]

    if len(volume_bytes) != capacity:
        raise ValueError(
            f"Volume slice length {len(volume_bytes)} does not match "
            f"volume capacity {capacity}"
        )

    # 4) Interpret as uint8 and reshape into (Z, Y, X, C)
    volume = np.frombuffer(volume_bytes, dtype=np.uint8)
    volume = volume.reshape((dim_z, dim_y, dim_x, channels))

    info = {
        "dim_x": dim_x,
        "dim_y": dim_y,
        "dim_z": dim_z,
        "channels": channels,
        "orig_length": header.orig_length,
    }
    return volume, info


def show_slice(
    volume: np.ndarray,
    info: dict,
    axis: str = "z",
    index: int | None = None,
    channel: int = 0,
) -> None:
    """
    Show a single 2D slice from the 3D volume for a given channel.
    axis: 'x', 'y', or 'z'
    index: which slice index along that axis (default: middle slice)
    channel: which channel to view (default: 0 = payload)
    """
    dim_z, dim_y, dim_x, channels = volume.shape

    if channel < 0 or channel >= channels:
        raise ValueError(f"Channel {channel} out of range [0, {channels-1}]")

    if axis == "z":
        max_idx = dim_z
    elif axis == "y":
        max_idx = dim_y
    elif axis == "x":
        max_idx = dim_x
    else:
        raise ValueError("axis must be one of 'x', 'y', or 'z'")

    if index is None:
        index = max_idx // 2  # middle slice

    if not (0 <= index < max_idx):
        raise ValueError(f"Index {index} out of range [0, {max_idx-1}]")

    # Extract slice along the chosen axis
    if axis == "z":
        slice_2d = volume[index, :, :, channel]
        title_axis = f"Z={index}"
    elif axis == "y":
        slice_2d = volume[:, index, :, channel]
        title_axis = f"Y={index}"
    else:  # axis == "x"
        slice_2d = volume[:, :, index, channel]
        title_axis = f"X={index}"

    plt.figure(figsize=(5, 5))
    plt.imshow(slice_2d, cmap="gray", interpolation="nearest")
    plt.colorbar(label="value (0–255)")
    plt.title(
        f"CI3 slice ({title_axis}, channel={channel})\n"
        f"{info['dim_x']}×{info['dim_y']}×{info['dim_z']}, channels={info['channels']}"
    )
    plt.tight_layout()
    plt.show()


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Visualize a slice of a CI3 corpus as a 2D image."
    )
    parser.add_argument("path", type=Path, help="Path to a .ci3 file")
    parser.add_argument(
        "--axis",
        choices=["x", "y", "z"],
        default="z",
        help="Axis along which to slice (default: z)",
    )
    parser.add_argument(
        "--index",
        type=int,
        default=None,
        help="Slice index along the chosen axis (default: middle slice)",
    )
    parser.add_argument(
        "--channel",
        type=int,
        default=0,
        help="Channel to visualize (default: 0 = payload)",
    )

    args = parser.parse_args(argv)

    volume, info = ci3_to_numpy(args.path)
    show_slice(volume, info, axis=args.axis, index=args.index, channel=args.channel)


if __name__ == "__main__":
    main()
