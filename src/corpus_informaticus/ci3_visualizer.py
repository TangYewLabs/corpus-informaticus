# src/corpus_informaticus/ci3_visualizer.py

from __future__ import annotations

import os
from typing import Tuple

import matplotlib.pyplot as plt
import numpy as np

from .ci3_codec import decode_ci3_file
from .ci3_types import dims_to_volume_size


def load_volume_from_ci3(path: str) -> Tuple[np.ndarray, object]:
    """
    Load a CI3 v0.1 file, return (volume, header).

    volume shape: (z, y, x) as uint8 numpy array.
    """
    data, header = decode_ci3_file(path)
    dim_x, dim_y, dim_z = header.dim_x, header.dim_y, header.dim_z
    channels = header.channels

    volume_size = dims_to_volume_size(dim_x, dim_y, dim_z, channels)

    # We filled volume linearly 0..volume_size-1; reshape accordingly.
    # Canonical order in v0.1: i = x + dim_x * (y + dim_y * z)
    # If we take bytes in order 0..volume_size-1, that is z-major if we reshape as (z, y, x).
    padded_data = np.zeros(volume_size, dtype=np.uint8)
    padded_data[: len(data)] = np.frombuffer(data, dtype=np.uint8)

    volume = padded_data.reshape((dim_z, dim_y, dim_x))
    return volume, header


def show_slice(volume: np.ndarray, axis: str = "z", index: int = 0) -> None:
    """
    Show a single 2D slice of the 3D volume using matplotlib.

    axis: 'z', 'y', or 'x'
    index: slice index along that axis
    """
    axis = axis.lower()
    if axis not in ("z", "y", "x"):
        raise ValueError("axis must be one of 'z', 'y', 'x'")

    z_dim, y_dim, x_dim = volume.shape

    if axis == "z":
        if not (0 <= index < z_dim):
            raise ValueError(f"index out of range for z axis: 0..{z_dim-1}")
        slice_2d = volume[index, :, :]
        title = f"Slice axis=z, index={index}"
    elif axis == "y":
        if not (0 <= index < y_dim):
            raise ValueError(f"index out of range for y axis: 0..{y_dim-1}")
        slice_2d = volume[:, index, :]
        title = f"Slice axis=y, index={index}"
    else:  # axis == "x"
        if not (0 <= index < x_dim):
            raise ValueError(f"index out of range for x axis: 0..{x_dim-1}")
        slice_2d = volume[:, :, index]
        title = f"Slice axis=x, index={index}"

    plt.figure()
    plt.imshow(slice_2d, cmap="gray", interpolation="nearest")
    plt.colorbar(label="Value")
    plt.title(title)
    plt.xlabel("X")
    plt.ylabel("Y or Z")
    plt.tight_layout()
    plt.show()


def show_ci3_slice(path: str, axis: str = "z", index: int = 0) -> None:
    """
    Convenience helper: load a CI3 file and display a slice.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"CI3 file not found: {path}")

    volume, header = load_volume_from_ci3(path)
    print(
        f"Loaded CI3 corpus from {path}\n"
        f"Dims: (z={header.dim_z}, y={header.dim_y}, x={header.dim_x}), "
        f"orig_length={header.orig_length}"
    )
    show_slice(volume, axis=axis, index=index)
