# examples/hello_corpus/encode_hello.py

import os
import sys

# Make sure we can import from src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import encode_bytes_to_ci3_file


def main() -> None:
    message = b"HELLO CORPUS INFORMATICUS"
    out_path = os.path.join(CURRENT_DIR, "hello.ci3")
    encode_bytes_to_ci3_file(message, out_path)
    print(f"Written {len(message)} bytes into corpus: {out_path}")


if __name__ == "__main__":
    main()
