"""
corpus_informaticus
====================

Volumetric data capsules and tools for AI, robotics, and spatial systems.

This package currently provides:

- CIVD v0.3   : Core byte-level capsule codec (single payload).
- CIVD v0.4   : File-table capsules (multi-file payloads).
- CIVD v0.5   : Adaptive geometry + capsule metadata.
- CIVD v0.6   : Region-of-interest (ROI) volume access helpers.
- CIVD v0.7   : Tiling, scale-out, and snapshot helpers for large volumes.

The goal is to keep the top-level API small and stable, while
versioned modules can evolve underneath as needed.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Public API surface
# ---------------------------------------------------------------------------

__all__ = [
    # v0.3 core
    "encode_bytes_to_civd_v03",
    "decode_civd_to_bytes_v03",

    # v0.4 multi-file
    "encode_folder_to_civd_v04",
    "decode_civd_v04_to_folder",

    # v0.5 adaptive geometry + metadata
    "encode_folder_to_civd_v05",
    "decode_civd_v05",

    # v0.6 volume + ROI
    "VolumeSpecV06",
    "read_region_from_bytes",
    "full_volume_from_bytes",
    "RoiV06",
    "clamp_roi",
    "roi_to_slices",
    "read_region_from_bytes_roi",

    # v0.7 tiling
    "TileIndexV07",
    "tile_volume_buffer",
    "write_tile_pack",
    "query_tiles_for_roi",
    "tile_index_to_name",
    "name_to_tile_index",
    "TILE_MANIFEST_FILENAME",

    # v0.7 snapshot
    "SnapshotHeaderV07",
    "write_snapshot_v07",
    "read_snapshot_v07",
    "full_volume_from_snapshot_v07",
    "read_roi_from_snapshot_v07",
]

# ---------------------------------------------------------------------------
# CIVD v0.3 – core byte capsule
# ---------------------------------------------------------------------------

try:
    from .codec_v03 import (
        encode_bytes_to_civd_v03,
        decode_civd_to_bytes_v03,
    )
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# CIVD v0.4 – file-table capsules
# ---------------------------------------------------------------------------

try:
    from .civd_v04_codec import (
        encode_folder_to_civd_v04,
        decode_civd_v04_to_folder,
    )
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# CIVD v0.5 – adaptive geometry & capsule metadata
# ---------------------------------------------------------------------------

try:
    from .civd_v05_codec import (
        encode_folder_to_civd_v05,
        decode_civd_v05,
    )
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# CIVD v0.6 – ROI and dense volume helpers
# ---------------------------------------------------------------------------

try:
    from .roi_v06 import (
        VolumeSpecV06,
        read_region_from_bytes,
        full_volume_from_bytes,
        RoiV06,
        clamp_roi,
        roi_to_slices,
        read_region_from_bytes_roi,
    )
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# CIVD v0.7 – tiling (scale-out)
# ---------------------------------------------------------------------------

try:
    from .tile_manifest_v07 import TileIndexV07
    from .tile_pack_v07 import (
        tile_volume_buffer,
        write_tile_pack,
        query_tiles_for_roi,
        tile_index_to_name,
        name_to_tile_index,
        TILE_MANIFEST_FILENAME,
    )
except Exception:  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# CIVD v0.7 – snapshot helpers (dense snapshot container)
# ---------------------------------------------------------------------------

try:
    from .snapshot_v07 import (
        SnapshotHeaderV07,
        write_snapshot_v07,
        read_snapshot_v07,
        full_volume_from_snapshot_v07,
        read_roi_from_snapshot_v07,
    )
except Exception:  # pragma: no cover
    pass
