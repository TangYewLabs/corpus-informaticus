import sys
from pathlib import Path

from corpus_informaticus.codec_v03 import decode_v03


def main():
    if len(sys.argv) < 2:
        print("Usage: python civd_to_file_v03.py <input.civd> [output_file]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.is_file():
        print(f"Input CIVD file not found: {input_path}")
        sys.exit(1)

    blob = input_path.read_bytes()
    result = decode_v03(blob)

    header = result["header"]
    payload = result["payload"]
    crc_ok = result["crc_ok"]

    print("CIVD v0.3 corpus info:")
    print(f"  Dims:      {header.dim_x} x {header.dim_y} x {header.dim_z}")
    print(f"  Channels:  {header.channels}")
    print(f"  Length:    {header.orig_length} bytes")
    print(f"  CRC OK:    {crc_ok}")

    if not crc_ok:
        print("WARNING: CRC mismatch! Restoring anyway, but data may be corrupted.")

    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        # Default: strip .civd, add .restored before extension
        if input_path.suffix == ".civd":
            base = input_path.with_suffix("")
            output_path = base.with_suffix(base.suffix + ".restored")
        else:
            output_path = input_path.with_suffix(input_path.suffix + ".restored")

    output_path.write_bytes(payload)

    print("Restored payload to:")
    print(f"  {output_path}")


if __name__ == "__main__":
    main()
