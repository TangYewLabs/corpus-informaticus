# examples/v02/decode_v02.py

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import decode_ci3_v02_file


def main():
    ci3_path = os.path.join(CURRENT_DIR, "hello_v02.ci3")

    if not os.path.exists(ci3_path):
        print("CI3 file not found:", ci3_path)
        print("Run encode_v02.py first.")
        return

    data, hdr = decode_ci3_v02_file(ci3_path)

    print("Decoded v0.2 file:")
    print("  Path:", ci3_path)
    print("  Version:", hdr.version)
    print("  Channels:", hdr.channels)
    print("  Original length:", hdr.orig_length)
    print("  Message:", data.decode('utf-8', errors='replace'))


if __name__ == "__main__":
    main()
