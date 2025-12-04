# examples/file_roundtrip/ci3_to_file.py

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import decode_ci3_file


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python ci3_to_file.py <input_ci3_file>")
        sys.exit(1)

    ci3_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(ci3_path):
        print(f"CI3 file not found: {ci3_path}")
        sys.exit(1)

    data, header = decode_ci3_file(ci3_path)
    print(f"Decoded CI3 corpus:")
    print(f"  Path: {ci3_path}")
    print(f"  orig_length: {header.orig_length} bytes")

    # Reconstruct original filename by stripping .ci3
    if ci3_path.lower().endswith(".ci3"):
        out_path = ci3_path[:-4]
    else:
        out_path = ci3_path + ".out"

    # To avoid overwriting accidentally, add suffix if needed
    if os.path.exists(out_path):
        base, ext = os.path.splitext(out_path)
        out_path = base + ".restored" + ext

    with open(out_path, "wb") as f:
        f.write(data)

    print(f"Restored payload to:")
    print(f"  {out_path}")


if __name__ == "__main__":
    main()
