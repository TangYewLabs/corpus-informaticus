# src/corpus_informaticus/ci3_codec.py

from __future__ import annotations

import io
import zlib
from typing import Tuple

from .ci3_types import (
    CI3Header,
    FOOTER_STRUCT,
    MAX_PAYLOAD_V01,
    dims_to_volume_size,
    DEFAULT_DIMS,
    DEFAULT_CHANNELS,
)

from .ci3_types import MAGIC, VERSION_V02, DIMS_V02, CHANNELS_V02

def encode_bytes_to_ci3(data: bytes) -> bytes:
    """
    Encode an arbitrary byte sequence into a CI3 v0.1 corpus (in-memory bytes).

    - Uses fixed dims 16x16x16, 1 channel (v0.1).
    - Fills the volume linearly (index 0..N-1), remaining voxels = 0.
    - Computes CRC32 over the full 4096-byte volume.
    - Returns [header][volume][footer] as bytes.
    """
    orig_length = len(data)
    if orig_length > MAX_PAYLOAD_V01:
        raise ValueError(f"Payload too large for v0.1 corpus: {orig_length} > {MAX_PAYLOAD_V01}")

    dim_x, dim_y, dim_z = DEFAULT_DIMS
    channels = DEFAULT_CHANNELS

    volume_size = dims_to_volume_size(dim_x, dim_y, dim_z, channels)
    volume = bytearray(volume_size)  # all zeros initially

    # Fill volume in canonical order with data, pad with zeros
    # For v0.1 canonical order, index i maps directly to volume[i]
    for i in range(orig_length):
        volume[i] = data[i]

    # Compute CRC32 over volume
    crc32_value = zlib.crc32(volume) & 0xFFFFFFFF

    # Build header
    header = CI3Header(orig_length=orig_length)
    header_bytes = header.pack()

    # Build footer
    footer_bytes = FOOTER_STRUCT.pack(crc32_value)

    # Concatenate into final blob
    buf = io.BytesIO()
    buf.write(header_bytes)
    buf.write(volume)
    buf.write(footer_bytes)

    return buf.getvalue()


def encode_bytes_to_ci3_file(data: bytes, path: str) -> None:
    """
    Encode data into CI3 v0.1 and write to a file.
    """
    blob = encode_bytes_to_ci3(data)
    with open(path, "wb") as f:
        f.write(blob)


def decode_ci3(data: bytes) -> Tuple[bytes, CI3Header]:
    """
    Decode a CI3 v0.1 corpus (in-memory bytes) into original data and header.

    Steps:
    - Read header, validate magic/version/dims/channels.
    - Extract volume payload.
    - Verify CRC32.
    - Return first orig_length bytes as the original payload.
    """
    # Determine header/footer sizes
    header_size = len(CI3Header().pack())
    footer_size = FOOTER_STRUCT.size

    if len(data) < header_size + footer_size:
        raise ValueError("Data too short to be a valid CI3 file")

    # Slice header
    header_bytes = data[:header_size]
    header = CI3Header.unpack(header_bytes)
    header.validate_basic()

    dim_x, dim_y, dim_z = header.dim_x, header.dim_y, header.dim_z
    channels = header.channels

    volume_size = dims_to_volume_size(dim_x, dim_y, dim_z, channels)

    expected_size = header_size + volume_size + footer_size
    if len(data) != expected_size:
        raise ValueError(
            f"Unexpected CI3 size: got {len(data)}, expected {expected_size} "
            f"(header={header_size}, volume={volume_size}, footer={footer_size})"
        )

    # Slice volume and footer
    volume_start = header_size
    volume_end = volume_start + volume_size
    volume_bytes = data[volume_start:volume_end]

    footer_bytes = data[volume_end: volume_end + footer_size]
    (crc32_stored,) = FOOTER_STRUCT.unpack(footer_bytes)

    # CRC check
    crc32_calc = zlib.crc32(volume_bytes) & 0xFFFFFFFF
    if crc32_calc != crc32_stored:
        raise ValueError(
            f"CRC32 mismatch: stored {crc32_stored:#010x}, calculated {crc32_calc:#010x}"
        )

    # Reconstruct original data using orig_length
    orig_length = header.orig_length
    if orig_length > volume_size:
        raise ValueError("orig_length in header exceeds volume capacity")

    recovered = bytes(volume_bytes[:orig_length])
    return recovered, header


def decode_ci3_file(path: str) -> Tuple[bytes, CI3Header]:
    """
    Decode a CI3 v0.1 corpus from a file on disk.
    """
    with open(path, "rb") as f:
        blob = f.read()
    return decode_ci3(blob)

# ---------------------------------------------------------------------------
# v0.2 – Multi-channel anatomy (payload + integrity + semantic + aux)
# ---------------------------------------------------------------------------

def encode_bytes_to_ci3_v02(data: bytes) -> bytes:
    """
    Encode an arbitrary byte sequence into a CI3 v0.2 corpus (in-memory bytes).

    v0.2 changes:
    - dims:      16x16x16 (same number of voxels as v0.1)
    - channels:  4 (payload, integrity, semantic, aux)
    - payload:   first N voxels get data bytes, rest padded with 0
    - integrity: set to 255 for all voxels
    - semantic:  0 for all voxels
    - aux:       0 for all voxels
    """
    orig_length = len(data)

    dim_x, dim_y, dim_z = DIMS_V02
    channels = CHANNELS_V02

    num_voxels = dim_x * dim_y * dim_z
    max_payload = num_voxels  # one payload byte per voxel

    if orig_length > max_payload:
        raise ValueError(f"Payload too large for v0.2 corpus: {orig_length} > {max_payload}")

    volume_size = num_voxels * channels
    volume = bytearray(volume_size)

    # Fill voxels
    for i in range(num_voxels):
        offset = i * channels

        if i < orig_length:
            payload = data[i]
        else:
            payload = 0

        volume[offset + 0] = payload        # payload
        volume[offset + 1] = 255            # integrity (max)
        volume[offset + 2] = 0              # semantic (unknown)
        volume[offset + 3] = 0              # aux (unused)

    # CRC over entire volume
    crc32_value = zlib.crc32(volume) & 0xFFFFFFFF

    # Build header for v0.2
    header = CI3Header(
        magic=MAGIC,
        version=VERSION_V02,
        dim_x=dim_x,
        dim_y=dim_y,
        dim_z=dim_z,
        channels=channels,
        orig_length=orig_length,
    )
    header_bytes = header.pack()

    footer_bytes = FOOTER_STRUCT.pack(crc32_value)

    buf = io.BytesIO()
    buf.write(header_bytes)
    buf.write(volume)
    buf.write(footer_bytes)

    return buf.getvalue()


def encode_bytes_to_ci3_v02_file(data: bytes, path: str) -> None:
    """
    Encode data into CI3 v0.2 and write to a file.
    """
    blob = encode_bytes_to_ci3_v02(data)
    with open(path, "wb") as f:
        f.write(blob)


def decode_ci3_v02(data: bytes) -> Tuple[bytes, CI3Header]:
    """
    Decode a CI3 v0.2 corpus (in-memory bytes) into original data and header.

    Uses:
    - version == 0x0002
    - dims    == (16,16,16)
    - channels == 4
    - payload channel (byte 0 of each voxel) to reconstruct data.
    """
    header_size = len(CI3Header().pack())
    footer_size = FOOTER_STRUCT.size

    if len(data) < header_size + footer_size:
        raise ValueError("Data too short to be a valid CI3 file")

    header_bytes = data[:header_size]
    header = CI3Header.unpack(header_bytes)

    # Manual validation for v0.2
    if header.magic != MAGIC:
        raise ValueError(f"Invalid magic for CI3 v0.2: {header.magic!r}")
    if header.version != VERSION_V02:
        raise ValueError(f"Unsupported version for v0.2 decoder: {header.version}")
    if (header.dim_x, header.dim_y, header.dim_z) != DIMS_V02:
        raise ValueError(
            f"Unexpected dims for v0.2: {(header.dim_x, header.dim_y, header.dim_z)}"
        )
    if header.channels != CHANNELS_V02:
        raise ValueError(f"Unexpected channels for v0.2: {header.channels}")

    dim_x, dim_y, dim_z = header.dim_x, header.dim_y, header.dim_z
    channels = header.channels

    num_voxels = dim_x * dim_y * dim_z
    volume_size = num_voxels * channels

    expected_size = header_size + volume_size + footer_size
    if len(data) != expected_size:
        raise ValueError(
            f"Unexpected CI3 v0.2 size: got {len(data)}, expected {expected_size} "
            f"(header={header_size}, volume={volume_size}, footer={footer_size})"
        )

    volume_start = header_size
    volume_end = volume_start + volume_size
    volume_bytes = data[volume_start:volume_end]

    footer_bytes = data[volume_end: volume_end + footer_size]
    (crc32_stored,) = FOOTER_STRUCT.unpack(footer_bytes)

    crc32_calc = zlib.crc32(volume_bytes) & 0xFFFFFFFF
    if crc32_calc != crc32_stored:
        raise ValueError(
            f"CRC32 mismatch for v0.2: stored {crc32_stored:#010x}, calculated {crc32_calc:#010x}"
        )

    # Reconstruct payload from payload channel (index 0 in each voxel)
    orig_length = header.orig_length
    if orig_length > num_voxels:
        raise ValueError("orig_length in header exceeds voxel capacity for v0.2")

    out = bytearray(orig_length)
    for i in range(orig_length):
        offset = i * channels
        out[i] = volume_bytes[offset + 0]  # payload channel

    return bytes(out), header


def decode_ci3_v02_file(path: str) -> Tuple[bytes, CI3Header]:
    """
    Decode a CI3 v0.2 corpus from a file on disk.
    """
    with open(path, "rb") as f:
        blob = f.read()
    return decode_ci3_v02(blob)
