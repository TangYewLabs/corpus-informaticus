# examples/v02/encode_v02.py

import os
import sys

# Make sure src/ is importable
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import encode_bytes_to_ci3_v02_file


def main():
    message = b"CORPUS INFORMATICUS V0.2 ANATOMY TEST"
    out_path = os.path.join(CURRENT_DIR, "hello_v02.ci3")

    encode_bytes_to_ci3_v02_file(message, out_path)

    print("Encoded message into:")
    print(" ", out_path)
    print("Length:", len(message), "bytes")


if __name__ == "__main__":
    main()
