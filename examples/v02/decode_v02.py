# examples/v02/decode_v02.py
"""
Legacy CI3 v0.2 decode demo (historical / backward compatibility).

CI3 is an early precursor format retained only for backward compatibility and
historical reference.

Primary format going forward: CIVD (Corpus Informaticus Volumetric Data)
- Snapshot v0.7:  python examples/v07/snapshot_demo.py
- Snapshot v0.8:  python examples/v08/snapshot_v08_demo.py
- Tile-pack v0.8: python examples/v08/tile_pack_v08_demo.py
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
        print(f"Legacy CI3 v0.2 sample not found:\n  {legacy_path}")
        print()
        print("This is not an error if you removed legacy artifacts.")
        print("For CIVD demos, run:")
        print("  python examples/v08/snapshot_v08_demo.py")
        print("  python examples/v08/tile_pack_v08_demo.py")
        return

    with open(legacy_path, "rb") as f:
        raw = f.read()

    data, header = decode_ci3_v02(raw)

    print("Decoded legacy CI3 v0.2 corpus:")
    print("  path       :", legacy_path)
    print("  orig_length:", getattr(header, "orig_length", "<unknown>"))

    # Best-effort print for demo purposes
    try:
        msg = data.decode("utf-8", errors="replace")
        print("  payload    :", msg)
    except Exception:
        print(f"  payload    : <binary data> ({len(data)} bytes)")

    print()
    print("CIVD is the active format family going forward.")


if __name__ == "__main__":
    main()
