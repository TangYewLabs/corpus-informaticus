# examples/file_roundtrip/file_to_ci3.py

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import encode_bytes_to_ci3_file
from corpus_informaticus.ci3_types import MAX_PAYLOAD_V01


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python file_to_ci3.py <input_file>")
        sys.exit(1)

    in_path = os.path.abspath(sys.argv[1])
    if not os.path.exists(in_path):
        print(f"Input file not found: {in_path}")
        sys.exit(1)

    with open(in_path, "rb") as f:
        data = f.read()

    if len(data) > MAX_PAYLOAD_V01:
        print(f"Error: file too large for v0.1 corpus ({len(data)} bytes > {MAX_PAYLOAD_V01})")
        sys.exit(1)

    base_name = os.path.basename(in_path)
    out_name = base_name + ".ci3"
    out_path = os.path.join(CURRENT_DIR, out_name)

    encode_bytes_to_ci3_file(data, out_path)

    print(f"Encoded '{in_path}' ({len(data)} bytes) into corpus:")
    print(f"  {out_path}")


if __name__ == "__main__":
    main()
