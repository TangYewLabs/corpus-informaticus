from __future__ import annotations

import argparse
from pathlib import Path

from .ci3_codec import decode_ci3
from .ci3_types import dims_to_volume_size


def inspect_ci3(path: Path) -> None:
    """Load a CI3 file, decode it, and print a human-readable summary."""
    if not path.is_file():
        print(f"[ERROR] File not found: {path}")
        return

    raw = path.read_bytes()

    try:
        payload, header = decode_ci3(raw)
    except Exception as e:
        print(f"[ERROR] Failed to decode CI3 file: {e}")
        return

    print(f"File:           {path}")
    print(f"Size on disk:   {len(raw)} bytes")
    print()
    print("Header")
    print("------")
    print(f"  Magic:        {header.magic!r}")
    print(f"  Version:      0x{header.version:04X}")
    print(f"  Dims:         {header.dim_x} × {header.dim_y} × {header.dim_z}")
    print(f"  Channels:     {header.channels}")
    print(f"  Orig length:  {header.orig_length} bytes")
    print(f"  Reserved1:    {header.reserved1!r}")
    print(f"  Reserved2:    {header.reserved2}")
    print()

    capacity = dims_to_volume_size(
        header.dim_x, header.dim_y, header.dim_z, header.channels
    )
    print("Derived")
    print("-------")
    print(
        f"  Volume capacity: {capacity} bytes "
        f"({header.dim_x}×{header.dim_y}×{header.dim_z}×{header.channels})"
    )
    print(f"  Payload bytes:   {len(payload)} bytes")
    print(f"  Payload matches header.orig_length: {len(payload) == header.orig_length}")
    print()

    if header.channels == 1:
        print("Channel layout (v0.1):")
        print("  [0] payload")
    elif header.channels == 4:
        print("Channel layout (v0.2 suggested):")
        print("  [0] payload")
        print("  [1] integrity")
        print("  [2] semantic")
        print("  [3] aux")
    else:
        print("Channel layout:")
        print(f"  0..{header.channels - 1} (application defined)")

    print()
    print("Status")
    print("------")
    print("  CI3 decode: OK (CRC and header checks passed if no errors above).")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Inspect a Corpus Informaticus (CI3) file."
    )
    parser.add_argument(
        "path",
        type=Path,
        help="Path to a .ci3 file",
    )
    args = parser.parse_args(argv)
    inspect_ci3(args.path)


if __name__ == "__main__":
    main()
