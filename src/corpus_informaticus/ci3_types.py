# src/corpus_informaticus/ci3_types.py

from __future__ import annotations

import dataclasses
import struct
from typing import Tuple

# --- Constants from the v0.1 spec ---

MAGIC = b"CI3\x00"        # "CI3\0"
VERSION_V01 = 0x0001      # v0.1

# --- Constants for v0.2 (Anatomy v1) ---

VERSION_V02 = 0x0002      # v0.2
DIMS_V02 = (16, 16, 16)
CHANNELS_V02 = 4

# Header layout (24 bytes total), little-endian:
# 4s  H    H      H      H      B    3s      I           I
# magic,version,dim_x,dim_y,dim_z,channels,reserved1,orig_length,reserved2
HEADER_STRUCT = struct.Struct("<4s H H H H B 3s I I")

# Footer layout: just CRC32 of volume payload
FOOTER_STRUCT = struct.Struct("<I")

# v0.1 fixed geometry
DEFAULT_DIMS = (16, 16, 16)
DEFAULT_CHANNELS = 1
MAX_PAYLOAD_V01 = DEFAULT_DIMS[0] * DEFAULT_DIMS[1] * DEFAULT_DIMS[2] * DEFAULT_CHANNELS


@dataclasses.dataclass
class CI3Header:
    """
    In-memory representation of the v0.1 CI3 header.

    Matches the spec:
    - magic:      "CI3\\0"
    - version:    0x0001
    - dim_x/y/z:  16,16,16 for v0.1
    - channels:   1
    - reserved1:  3 zero bytes
    - orig_length: length of original payload (<= 4096)
    - reserved2:  0
    """
    magic: bytes = MAGIC
    version: int = VERSION_V01
    dim_x: int = DEFAULT_DIMS[0]
    dim_y: int = DEFAULT_DIMS[1]
    dim_z: int = DEFAULT_DIMS[2]
    channels: int = DEFAULT_CHANNELS
    reserved1: bytes = b"\x00\x00\x00"
    orig_length: int = 0
    reserved2: int = 0

    def pack(self) -> bytes:
        """Serialize the header to 24 bytes."""
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
        """Parse 24 bytes into a CI3Header instance."""
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
            reserved1=reserved1,
            orig_length=orig_length,
            reserved2=reserved2,
        )

    def validate_basic(self) -> None:
        """Basic sanity checks according to v0.1 spec."""
        if self.magic != MAGIC:
            raise ValueError(f"Invalid magic: {self.magic!r}, expected {MAGIC!r}")
        if self.version != VERSION_V01:
            raise ValueError(f"Unsupported version: {self.version}")
        if (self.dim_x, self.dim_y, self.dim_z) != DEFAULT_DIMS:
            raise ValueError(f"Unexpected dims: {(self.dim_x, self.dim_y, self.dim_z)}")
        if self.channels != DEFAULT_CHANNELS:
            raise ValueError(f"Unexpected channels: {self.channels}")
        if self.reserved1 != b"\x00\x00\x00":
            raise ValueError(f"reserved1 must be zero, got {self.reserved1!r}")
        if self.reserved2 != 0:
            raise ValueError(f"reserved2 must be zero, got {self.reserved2}")


def dims_to_volume_size(dim_x: int, dim_y: int, dim_z: int, channels: int) -> int:
    """Compute number of bytes in the volume payload."""
    return dim_x * dim_y * dim_z * channels
