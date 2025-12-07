#!/usr/bin/env python3
"""
Unpack a CIVD v0.4 capsule into a folder.

Usage:
    python unpack.py <capsule.civd> [--out <folder>]
"""

import os
import argparse
from corpus_informaticus.civd_v04_codec import decode_civd_v04

def ensure_dir(path):
    if not os.path.exists(path):
        os.makedirs(path)

def main():
    parser = argparse.ArgumentParser(description="Unpack CIVD v0.4 capsule")
    parser.add_argument("path", help="Path to .civd capsule")
    parser.add_argument("--out", help="Output folder", default=None)
    args = parser.parse_args()

    capsule_path = args.path
    if not os.path.isfile(capsule_path):
        print(f"ERROR: File not found: {capsule_path}")
        return

    # Choose output folder
    if args.out:
        out_dir = args.out
    else:
        base = os.path.splitext(os.path.basename(capsule_path))[0]
        out_dir = base + "_unpacked"

    ensure_dir(out_dir)

    # Load capsule
    with open(capsule_path, "rb") as f:
        blob = f.read()

    print("=== Unpacking CIVD v0.4 Capsule ===")
    print("Capsule:", capsule_path)

    # Decode capsule
    table, files, meta = decode_civd_v04(blob)

    print("Dims:", meta["dims"], "Channels:", meta["channels"])
    print("File count:", meta["file_count"])
    print("Output folder:", out_dir)
    print()

    # Write each file
    for name, data in files.items():
        target_path = os.path.join(out_dir, name)
        folder = os.path.dirname(target_path)
        ensure_dir(folder)

        with open(target_path, "wb") as f:
            f.write(data)

        print(f"Wrote: {target_path} ({len(data)} bytes)")

    print("\nDone.")

if __name__ == "__main__":
    main()
