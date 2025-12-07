#!/usr/bin/env python3

import argparse
import os
from pathlib import Path

from corpus_informaticus.civd_v04_codec import (
    encode_folder_to_civd_v04,
    decode_civd_v04,
)
from corpus_informaticus.filetable_v04 import CivdFileEntryV04


def cmd_encode_folder(args):
    folder = args.folder
    output_path = args.output

    if not os.path.isdir(folder):
        raise SystemExit(f"Error: Folder not found: {folder}")

    blob, info = encode_folder_to_civd_v04(folder)

    with open(output_path, "wb") as f:
        f.write(blob)

    print("=== CIVD v0.4 Encode Completed ===")
    print(f"Input folder: {folder}")
    print(f"Output file:  {output_path}")
    print(f"Dims:         {info['dims']}")
    print(f"Channels:     {info['channels']}")
    print(f"Files:        {info['files']}")
    print(f"Payload size: {info['payload_size']} bytes")
    print()


def cmd_preview(args):
    path = args.civd
    if not os.path.isfile(path):
        raise SystemExit(f"Error: File not found: {path}")

    with open(path, "rb") as f:
        blob = f.read()

    table, files, meta = decode_civd_v04(blob)

    print("=== CIVD v0.4 Capsule Preview ===")
    print(f"Path:          {path}")
    print(f"Dims:          {meta['dims']}")
    print(f"Channels:      {meta['channels']}")
    print(f"File count:    {meta['file_count']}")
    print(f"Table size:    {meta['table_size']} bytes")
    print(f"Data region:   {meta['data_region_size']} bytes")
    print(f"Payload size:  {meta['payload_size']} bytes")
    print()
    print("Files in capsule:")

    for entry in table.entries:
        print(f"- {entry.name} ({entry.size} bytes)")
        data = files[entry.name]

        preview = ""
        try:
            preview = data.decode("utf-8")[:60].replace("\n", " ")
        except:
            preview = data[:32].hex() + " (binary)"

        print("   preview:", preview)
    print()


def cmd_unpack(args):
    path = args.civd
    out_dir = args.output

    if not os.path.isfile(path):
        raise SystemExit(f"Error: File not found: {path}")

    with open(path, "rb") as f:
        blob = f.read()

    table, files, meta = decode_civd_v04(blob)

    os.makedirs(out_dir, exist_ok=True)

    print("=== Unpacking CIVD v0.4 Capsule ===")
    print(f"Capsule:       {path}")
    print(f"Dims:          {meta['dims']}")
    print(f"Channels:      {meta['channels']}")
    print(f"File count:    {meta['file_count']}")
    print(f"Output folder: {out_dir}")
    print()

    for entry in table.entries:
        file_path = os.path.join(out_dir, entry.name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        with open(file_path, "wb") as f:
            f.write(files[entry.name])

        print(f"Wrote: {file_path} ({entry.size} bytes)")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(
        description="CIVD v0.4 Command Line Interface"
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # encode-folder
    p_enc = sub.add_parser(
        "encode-folder",
        help="Encode a folder into a CIVD v0.4 capsule.",
    )
    p_enc.add_argument("folder", help="Folder to encode")
    p_enc.add_argument("output", help="Output .civd file")
    p_enc.set_defaults(func=cmd_encode_folder)

    # preview
    p_prev = sub.add_parser(
        "preview",
        help="Preview metadata and file table inside a CIVD capsule.",
    )
    p_prev.add_argument("civd", help="Input .civd file")
    p_prev.set_defaults(func=cmd_preview)

    # unpack
    p_unpack = sub.add_parser(
        "unpack",
        help="Extract all files from a CIVD capsule.",
    )
    p_unpack.add_argument("civd", help="Input .civd file")
    p_unpack.add_argument("output", help="Output directory")
    p_unpack.set_defaults(func=cmd_unpack)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
