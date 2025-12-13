from corpus_informaticus.tile_header_v08 import (
    TileHeaderV08, try_parse_tile_header_v08, TILE_HEADER_LEN_V08
)

def test_tile_header_roundtrip():
    hdr = TileHeaderV08(
        tile_format_ver=8,
        header_len=TILE_HEADER_LEN_V08,
        flags=0,
        tx=1, ty=2, tz=3,
        tile_size=(16,16,16),
        channels=4,
        dtype="uint8",
        signature="C_CONTIG",
        order="C",
        payload_nbytes=1234,
    )
    blob = hdr.to_bytes() + (b"\x00" * 1234)
    parsed = try_parse_tile_header_v08(blob)
    assert parsed is not None
    assert parsed.tx == 1 and parsed.ty == 2 and parsed.tz == 3
    assert parsed.payload_nbytes == 1234

if __name__ == "__main__":
    test_tile_header_roundtrip()
    print("test_tile_header_roundtrip: OK")
