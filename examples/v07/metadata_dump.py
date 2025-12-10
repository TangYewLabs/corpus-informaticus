"""
examples/v07/metadata_dump.py

Print a sample TileManifestV07 as JSON.
"""

from __future__ import annotations

import json

from corpus_informaticus.tile_manifest_v07 import make_manifest_for_volume


def main() -> None:
    manifest = make_manifest_for_volume(
        dims=(512, 512, 256),
        channels=4,
        dtype="float32",
        tile=(64, 64, 64),
        compressor="none",
    )

    print("=== Tile Manifest v0.7 Sample ===")
    print(json.dumps(manifest.to_dict(), indent=2))


if __name__ == "__main__":
    main()
