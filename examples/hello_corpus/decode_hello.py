# examples/hello_corpus/decode_hello.py

import os
import sys

# Make sure we can import from src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import decode_ci3_file


def main() -> None:
    ci3_path = os.path.join(CURRENT_DIR, "hello.ci3")
    if not os.path.exists(ci3_path):
        print(f"Legacy CI3 file not found: {ci3_path}")
        print("Run encode_hello.py first.")
        return

    data, header = decode_ci3_file(ci3_path)
    print(f"Decoded corpus from: {ci3_path}")
    print(f"orig_length: {header.orig_length}")
    print("Recovered message:", data.decode("utf-8", errors="replace"))


if __name__ == "__main__":
    main()
