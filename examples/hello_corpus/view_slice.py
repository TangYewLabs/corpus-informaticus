# examples/hello_corpus/view_slice.py

import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_visualizer import show_ci3_slice


def main() -> None:
    ci3_path = os.path.join(CURRENT_DIR, "hello.ci3")
    if not os.path.exists(ci3_path):
        print(f"CI3 file not found: {ci3_path}")
        print("Run encode_hello.py first.")
        return

    # For now, just show slice z=0
    show_ci3_slice(ci3_path, axis="z", index=0)


if __name__ == "__main__":
    main()
