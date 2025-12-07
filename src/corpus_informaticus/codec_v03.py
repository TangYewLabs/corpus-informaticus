# codec_v03.py
# Standalone CIVD v0.3 encoder/decoder
# Does NOT depend on ci3_types.py, so it is self-consistent.

from __future__ import annotations

import struct
import zlib
from dataclasses import asdict
from typing import Dict, Tuple, Any

# --- Basic constants ---

MAGIC = b"CI3\x00"      # 4-byte magic
VERSION_V03 = 0x0003     # CIVD v0.3

# Header layout (24 bytes total), little-endian:
# 4s  H    H      H      H      B    3s      I           I
# magic,version,dim_x,dim_y,dim_z,channels,reserved1,orig_length,reserved2
HEADER_STRUCT = struct.Struct("<4s H H H H B 3s I I")

# Footer: CRC32 of volume payload
FOOTER_STRUCT = struct.Struct("<I")


def dims_to_volume_size(x: int, y: int, z: int, channels: int) -> int:
    return x * y * z * channels


class CI3Header:
    """Minimal header representation for CIVD/CI3.

    This is scoped to v0.3 usage here and kept independent from ci3_types.py
    to avoid mismatch issues. Layout matches HEADER_STRUCT exactly.
    """

    __slots__ = (
        "magic",
        "version",
        "dim_x",
        "dim_y",
        "dim_z",
        "channels",
        "reserved1",
        "orig_length",
        "reserved2",
    )

    def __init__(
        self,
        magic: bytes,
        version: int,
        dim_x: int,
        dim_y: int,
        dim_z: int,
        channels: int,
        orig_length: int,
        reserved1: bytes = b"\x00\x00\x00",
        reserved2: int = 0,
    ) -> None:
        self.magic = magic
        self.version = version
        self.dim_x = dim_x
        self.dim_y = dim_y
        self.dim_z = dim_z
        self.channels = channels
        self.reserved1 = reserved1
        self.orig_length = orig_length
        self.reserved2 = reserved2

    def pack(self) -> bytes:
        return HEADER_STRUCT.pack(
            self.magic,
            self.version,
            self.dim_x,
            self.dim_y,
            self.dim_z,
            self.channels,
            self.reserved1,
            self.orig_length,
            self.reserved2,
        )

    @classmethod
    def unpack(cls, data: bytes) -> "CI3Header":
        if len(data) != HEADER_STRUCT.size:
            raise ValueError(f"Expected {HEADER_STRUCT.size} bytes for header, got {len(data)}")
        (
            magic,
            version,
            dim_x,
            dim_y,
            dim_z,
            channels,
            reserved1,
            orig_length,
            reserved2,
        ) = HEADER_STRUCT.unpack(data)
        return cls(
            magic=magic,
            version=version,
            dim_x=dim_x,
            dim_y=dim_y,
            dim_z=dim_z,
            channels=channels,
            orig_length=orig_length,
            reserved1=reserved1,
            reserved2=reserved2,
        )

    def validate_basic(self) -> None:
        if self.magic != MAGIC:
            raise ValueError(f"Invalid magic: {self.magic!r}, expected {MAGIC!r}")
        if self.version != VERSION_V03:
            raise ValueError(f"Unsupported version for codec_v03: {self.version}")
        if self.dim_x <= 0 or self.dim_y <= 0 or self.dim_z <= 0:
            raise ValueError(
                f"All dims must be > 0, got {(self.dim_x, self.dim_y, self.dim_z)}"
            )
        if self.channels <= 0:
            raise ValueError(f"channels must be > 0, got {self.channels}")
        if self.reserved1 != b"\x00\x00\x00":
            raise ValueError(f"reserved1 must be zero, got {self.reserved1!r}")
        if self.reserved2 != 0:
            raise ValueError(f"reserved2 must be zero, got {self.reserved2}")


# -------------------------------------------------------------------
# ENCODER
# -------------------------------------------------------------------

def encode_bytes_to_civd_v03(
    payload: bytes,
    dims: Tuple[int, int, int] = (32, 32, 32),
    channels: int = 4,
) -> bytes:
    if channels <= 0:
        raise ValueError("channels must be > 0")

    dx, dy, dz = dims
    if dx <= 0 or dy <= 0 or dz <= 0:
        raise ValueError("All dims must be > 0")

    capacity = dims_to_volume_size(dx, dy, dz, channels)

    if len(payload) > capacity:
        raise ValueError(f"Payload too large: {len(payload)} > capacity {capacity}")

    header = CI3Header(
        magic=MAGIC,
        version=VERSION_V03,
        dim_x=dx,
        dim_y=dy,
        dim_z=dz,
        channels=channels,
        orig_length=len(payload),
        reserved1=b"\x00\x00\x00",
        reserved2=0,
    )

    volume = payload + b"\x00" * (capacity - len(payload))

    crc = zlib.crc32(volume) & 0xFFFFFFFF

    return header.pack() + volume + FOOTER_STRUCT.pack(crc)


# -------------------------------------------------------------------
# DECODER
# -------------------------------------------------------------------

def decode_civd_v03(blob: bytes) -> Tuple[bytes, Dict[str, Any]]:
    header_size = HEADER_STRUCT.size
    footer_size = FOOTER_STRUCT.size

    if len(blob) < header_size + footer_size:
        raise ValueError("Blob too small to contain header + footer")

    header = CI3Header.unpack(blob[:header_size])
    header.validate_basic()

    capacity = dims_to_volume_size(
        header.dim_x, header.dim_y, header.dim_z, header.channels
    )

    volume = blob[header_size:-footer_size]
    if len(volume) != capacity:
        raise ValueError(f"Volume length {len(volume)} != capacity {capacity}")

    (crc_stored,) = FOOTER_STRUCT.unpack(blob[-footer_size:])
    crc_calc = zlib.crc32(volume) & 0xFFFFFFFF
    crc_ok = crc_calc == crc_stored

    payload = volume[: header.orig_length]

    info: Dict[str, Any] = {
        "header": header,
        "dims": (header.dim_x, header.dim_y, header.dim_z),
        "channels": header.channels,
        "capacity": capacity,
        "crc_ok": crc_ok,
    }

    return payload, info
