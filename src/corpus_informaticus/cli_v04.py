#!/usr/bin/env python3
"""
CIVD v0.4 CLI

Subcommands:

  civd encode  <folder> <output.civd> [--dims X Y Z] [--channels N]
  civd inspect <capsule.civd> [--preview-bytes N]
  civd extract <capsule.civd> <out_folder>

Usage examples (from repo root):

  python -m corpus_informaticus.cli_v04 encode tmp_v04_test tmp_v04_test.civd
  python -m corpus_informaticus.cli_v04 inspect tmp_v04_test.civd
  python -m corpus_informaticus.cli_v04 extract tmp_v04_test.civd tmp_v04_test_out
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Tuple

from .civd_v04_codec import encode_folder_to_civd_v04, decode_civd_v04


# ---------------------------------------------------------------------------
# Subcommand implementations
# ---------------------------------------------------------------------------


def cmd_encode(args: argparse.Namespace) -> int:
    """Encode a folder into a CIVD v0.4 capsule."""
    folder = Path(args.folder)
    if not folder.is_dir():
        print(f"[ERROR] Folder does not exist or is not a directory: {folder}", file=sys.stderr)
        return 1

    # dims: either user-provided or default (64, 64, 32)
    if args.dims is not None:
        if len(args.dims) != 3:
            print("[ERROR] --dims requires exactly 3 integers: X Y Z", file=sys.stderr)
            return 1
        dims: Tuple[int, int, int] = (args.dims[0], args.dims[1], args.dims[2])
    else:
        dims = (64, 64, 32)

    channels = args.channels

    print(f"[ENCODE] Folder: {folder}")
    print(f"[ENCODE] Output: {args.output}")
    print(f"[ENCODE] Dims: {dims}, Channels: {channels}")

    blob, info = encode_folder_to_civd_v04(str(folder), dims=dims, channels=channels)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(blob)

    print("\n[ENCODE] Done.")
    print(f"  Capsule:      {out_path}")
    print(f"  Bytes written: {len(blob)}")
    print(f"  dims:          {info.get('dims')}")
    print(f"  channels:      {info.get('channels')}")
    print(f"  file_count:    {info.get('file_count')}")
    print(f"  payload_size:  {info.get('payload_size')} bytes")
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Inspect a CIVD v0.4 capsule (metadata + file table preview)."""
    capsule_path = Path(args.capsule)
    if not capsule_path.is_file():
        print(f"[ERROR] Capsule not found: {capsule_path}", file=sys.stderr)
        return 1

    blob = capsule_path.read_bytes()
    table, files, meta = decode_civd_v04(blob)

    print("=== CIVD v0.4 Capsule Inspect ===")
    print(f"Path:          {capsule_path}")
    print(f"Dims:          {meta.get('dims')}")
    print(f"Channels:      {meta.get('channels')}")
    print(f"Orig length:   {meta.get('orig_length')}")
    print(f"File count:    {meta.get('file_count')}")
    print(f"Table size:    {meta.get('table_size')} bytes")
    print(f"Data region:   {meta.get('data_region_size')} bytes")
    print(f"Payload size:  {meta.get('payload_size')} bytes")
    print()

    max_bytes = args.preview_bytes
    print("Files in capsule:")
    for entry in table.entries:
        name = entry.name
        size = entry.size
        print(f"- {name}  ({size} bytes)")

        data = files.get(name, b"")
        if not data:
            print("    [no data found for this entry]")
            continue

        # Preview
        snippet = data[:max_bytes]
        try:
            text = snippet.decode("utf-8", errors="replace")
            print(f"    preview: {text!r}")
        except Exception:
            # Fallback: show hex
            print(f"    preview (hex): {snippet.hex()}")
    return 0


def cmd_extract(args: argparse.Namespace) -> int:
    """Extract the contents of a CIVD v0.4 capsule into a folder."""
    capsule_path = Path(args.capsule)
    out_folder = Path(args.output)

    if not capsule_path.is_file():
        print(f"[ERROR] Capsule not found: {capsule_path}", file=sys.stderr)
        return 1

    blob = capsule_path.read_bytes()
    table, files, meta = decode_civd_v04(blob)

    print("=== CIVD v0.4 Capsule Extract ===")
    print(f"Capsule: {capsule_path}")
    print(f"Dims:    {meta.get('dims')} Channels: {meta.get('channels')}")
    print(f"Files:   {meta.get('file_count')}")
    print(f"Output:  {out_folder}")
    print()

    out_folder.mkdir(parents=True, exist_ok=True)

    for entry in table.entries:
        name = entry.name
        size = entry.size
        data = files.get(name, b"")

        dest = out_folder / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)

        print(f"Wrote: {dest} ({len(data)} bytes, expected {size})")

    print("\nDone.")
    return 0


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="civd",
        description="CIVD v0.4 — 3D volumetric data capsules",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # encode
    p_enc = subparsers.add_parser(
        "encode",
        help="Encode a folder into a CIVD v0.4 capsule",
    )
    p_enc.add_argument("folder", help="Input folder containing files to pack")
    p_enc.add_argument("output", help="Output .civd capsule path")
    p_enc.add_argument(
        "--dims",
        nargs=3,
        type=int,
        metavar=("X", "Y", "Z"),
        help="Volume dimensions (default: 64 64 32)",
    )
    p_enc.add_argument(
        "--channels",
        type=int,
        default=4,
        help="Number of channels (default: 4)",
    )
    p_enc.set_defaults(func=cmd_encode)

    # inspect
    p_ins = subparsers.add_parser(
        "inspect",
        help="Inspect a CIVD v0.4 capsule (metadata + file table preview)",
    )
    p_ins.add_argument("capsule", help="Input .civd capsule path")
    p_ins.add_argument(
        "--preview-bytes",
        type=int,
        default=80,
        help="Number of bytes to preview per file (default: 80)",
    )
    p_ins.set_defaults(func=cmd_inspect)

    # extract
    p_ext = subparsers.add_parser(
        "extract",
        help="Extract files from a CIVD v0.4 capsule into a folder",
    )
    p_ext.add_argument("capsule", help="Input .civd capsule path")
    p_ext.add_argument("output", help="Output folder")
    p_ext.set_defaults(func=cmd_extract)

    return parser


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    parser = build_parser()
    args = parser.parse_args(argv)

    func = getattr(args, "func", None)
    if func is None:
        parser.print_help()
        return 1

    return func(args)


if __name__ == "__main__":
    raise SystemExit(main())
