# examples/v02/decode_v02.py
"""
Legacy CI3 v0.2 decode demo (historical / backward compatibility).

This script exists only to prove legacy CI3 artifacts can still be decoded.

Primary format going forward: CIVD (Corpus Informaticus Volumetric Data)
- Snapshot demo:  examples/v07/snapshot_demo.py
- Snapshot v0.8:  examples/v08/snapshot_v08_demo.py
- Tile-pack v0.8: examples/v08/tile_pack_v08_demo.py
"""

import os
import sys

# Make sure we can import from src/
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import decode_ci3_v02  # legacy CI3


def main() -> None:
    # NOTE: the legacy sample file was moved to examples/legacy_ci3/
    legacy_path = os.path.join(PROJECT_ROOT, "examples", "legacy_ci3", "hello_v02.ci3")

    if not os.path.exists(legacy_path):
        print("Legacy CI3 v0.2 file not found:", legacy_path)
        print("If you removed legacy artifacts, this is expected.")
        print("For CIVD demos, run:")
        print("  python examples/v08/snapshot_v08_demo.py")
        print("  python examples/v08/tile_pack_v08_demo.py")
        return

    data, header = decode_ci3_v02(open(legacy_path, "rb").read())

    print("Decoded legacy CI3 v0.2 corpus:")
    print("  path       :", legacy_path)
    print("  orig_length:", header.orig_length)
    try:
        msg = data.decode("utf-8", errors="replace")
        print("  payload    :", msg)
    except Exception:
        print("  payload    : <binary data> (not utf-8)")

    print("\nCIVD is the active format family going forward.")


if __name__ == "__main__":
    main()
