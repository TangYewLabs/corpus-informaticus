"""
tile_header_v08.py — CIVD v0.8 tile header (streaming-ready).

Backward compatible:
- If magic != CIVDTILE, tile is treated as raw v0.7.
"""

from __future__ import annotations

from dataclasses import dataclass
import struct
from typing import Optional, Tuple

MAGIC_TILE_V08 = b"CIVDTILE"  # 8 bytes
TILE_HEADER_STRUCT_V08 = struct.Struct("<8s H H I 3I 3I I H H B 7x Q")
TILE_HEADER_LEN_V08 = TILE_HEADER_STRUCT_V08.size  # 64 bytes


# dtype codes (minimal set; extend later)
DTYPE_CODE = {
    "uint8": 1,
    "uint16": 2,
    "float32": 3,
}
DTYPE_NAME = {v: k for k, v in DTYPE_CODE.items()}

# signature codes
SIGNATURE_CODE = {
    "C_CONTIG": 1,
    "F_CONTIG": 2,
}
SIGNATURE_NAME = {v: k for k, v in SIGNATURE_CODE.items()}

# order codes
ORDER_CODE = {"C": 1, "F": 2}
ORDER_NAME = {v: k for k, v in ORDER_CODE.items()}


@dataclass(frozen=True)
class TileHeaderV08:
    tile_format_ver: int
    header_len: int
    flags: int
    tx: int
    ty: int
    tz: int
    tile_size: Tuple[int, int, int]  # (sx, sy, sz) in (x,y,z)
    channels: int
    dtype: str
    signature: str
    order: str
    payload_nbytes: int

    def to_bytes(self) -> bytes:
        if self.tile_format_ver != 8:
            raise ValueError("TileHeaderV08.tile_format_ver must be 8")
        if self.header_len != TILE_HEADER_LEN_V08:
            raise ValueError(f"TileHeaderV08.header_len must be {TILE_HEADER_LEN_V08}")
        sx, sy, sz = self.tile_size
        dtype_code = DTYPE_CODE.get(self.dtype)
        if dtype_code is None:
            raise ValueError(f"Unsupported dtype: {self.dtype!r}")
        sig_code = SIGNATURE_CODE.get(self.signature)
        if sig_code is None:
            raise ValueError(f"Unsupported signature: {self.signature!r}")
        order_code = ORDER_CODE.get(self.order)
        if order_code is None:
            raise ValueError(f"Unsupported order: {self.order!r}")

        return TILE_HEADER_STRUCT_V08.pack(
            MAGIC_TILE_V08,
            self.tile_format_ver,
            self.header_len,
            self.flags,
            self.tx,
            self.ty,
            self.tz,
            sx,
            sy,
            sz,
            self.channels,
            dtype_code,
            sig_code,
            order_code,
            self.payload_nbytes,
        )


def try_parse_tile_header_v08(blob: bytes) -> Optional[TileHeaderV08]:
    """
    If 'blob' begins with CIVDTILE magic and a valid v0.8 header, return TileHeaderV08.
    Otherwise return None (caller treats as raw v0.7 tile).
    """
    if len(blob) < TILE_HEADER_LEN_V08:
        return None
    magic = blob[:8]
    if magic != MAGIC_TILE_V08:
        return None

    (
        magic,
        tile_format_ver,
        header_len,
        flags,
        tx,
        ty,
        tz,
        sx,
        sy,
        sz,
        channels,
        dtype_code,
        sig_code,
        order_code,
        payload_nbytes,
    ) = TILE_HEADER_STRUCT_V08.unpack_from(blob, 0)

    if tile_format_ver != 8:
        return None
    if header_len != TILE_HEADER_LEN_V08:
        return None

    dtype = DTYPE_NAME.get(dtype_code)
    signature = SIGNATURE_NAME.get(sig_code)
    order = ORDER_NAME.get(order_code)

    if dtype is None or signature is None or order is None:
        return None

    return TileHeaderV08(
        tile_format_ver=tile_format_ver,
        header_len=header_len,
        flags=flags,
        tx=tx,
        ty=ty,
        tz=tz,
        tile_size=(sx, sy, sz),
        channels=channels,
        dtype=dtype,
        signature=signature,
        order=order,
        payload_nbytes=payload_nbytes,
    )
