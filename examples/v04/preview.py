"""
preview.py — CIVD v0.4 capsule inspector

Usage:

    python examples/v04/preview.py path/to/capsule.civd

This will:

- Decode the CIVD v0.4 capsule.
- Print basic header/meta information.
- List all embedded files.
- Show a short preview of each file:
  - Try UTF-8 text.
  - If that fails, try UTF-16-LE (common on Windows).
  - If that fails, show a hex snippet.
"""

from __future__ import annotations

import argparse
from typing import Optional

from corpus_informaticus.civd_v04_codec import decode_civd_v04


def _preview_bytes(buf: bytes, max_len: int = 80) -> str:
    """
    Return a human-friendly preview of `buf`:

    - Try UTF-8.
    - If that fails, try UTF-16-LE (common Windows encoding).
    - If that fails, return a short hex string.
    """
    # Trim for preview
    snippet = buf[: max_len * 4]  # allow for multibyte encodings

    # Try UTF-8
    try:
        return snippet.decode("utf-8").strip()
    except UnicodeDecodeError:
        pass

    # Try UTF-16 LE
    try:
        return snippet.decode("utf-16-le").strip()
    except UnicodeDecodeError:
        pass

    # Fallback: hex
    return snippet.hex() + "  (hex)"


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(
        description="Preview contents of a CIVD v0.4 capsule"
    )
    parser.add_argument(
        "path",
        help="Path to .civd file",
    )
    args = parser.parse_args(argv)

    # Load capsule
    with open(args.path, "rb") as f:
        blob = f.read()

    # Decode via CIVD v0.4
    table, files, meta = decode_civd_v04(blob)

    print("=== CIVD v0.4 Capsule Preview ===")
    print(f"Path:          {args.path}")
    print(f"Dims:          {meta.get('dims')}")
    print(f"Channels:      {meta.get('channels')}")
    print(f"Orig length:   {meta.get('orig_length')}")
    print(f"File count:    {meta.get('file_count')}")
    print(f"Table size:    {meta.get('table_size')} bytes")
    print(f"Data region:   {meta.get('data_region_size')} bytes")
    print(f"Payload size:  {meta.get('payload_size')} bytes")
    print()

    print("Files in capsule:")
    for entry in table.entries:
        name = entry.name
        data = files[name]
        size = len(data)
        preview = _preview_bytes(data)
        print(f"- {name}  ({size} bytes)")
        print(f"    preview: {preview}")
    print()


if __name__ == "__main__":
    main()
