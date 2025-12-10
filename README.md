# Corpus Informaticus: CIVD — Volumetric Data Capsules for Robotics & AI

[![Status: Experimental](https://img.shields.io/badge/status-experimental-blue)]()
[![Domain: Robotics & AI](https://img.shields.io/badge/domain-robotics%20%26%20AI-brightgreen)]()
[![Data: 3D Volumetric](https://img.shields.io/badge/data-3D%20volumetric-orange)]()
[![License](https://img.shields.io/badge/license-MIT-lightgrey)]()

**Corpus Informaticus** is an experimental playground for **CIVD** — the **Corpus Informaticus Volumetric Data** format.

CIVD is a family of **3D-native data capsules** designed for:
- Robotics
- Simulation & digital twins
- Sensor fusion (LIDAR, RGB, depth, semantics, telemetry)
- AI pipelines that want to read **spatial snapshots** instead of loose files

The core idea:

> Treat a dataset as a **single volumetric capsule** you can ship, mount, and slice —
> not just a folder full of disconnected files.

---

## 1. Mental model — what is a CIVD capsule?

A CIVD file is conceptually two things in one:

1. A **File Plane** (optional, v0.4+)  
   - A compact file table (`CivdFileTableV04`) representing paths like `nav/map.pcd`, `vision/front.jpg`, `meta/civd.json`.
   - Great for configuration, metadata, small assets, and mission descriptors.

2. A **Volume Plane** (always present)  
   - A dense 3D tensor: `(X, Y, Z, C)`
   - Encoded as a continuous voxel buffer optimized for fast region-of-interest reads.

Think of it as a **game cartridge for robots**:

```text
+--------------------------------------------------------+
| CIVD Header (v0.3-compatible)                          |
+--------------------------------------------------------+
| Optional File Table (v0.4+)                            |
|   - nav/map.pcd                                        |
|   - nav/waypoints.json                                 |
|   - vision/front.jpg                                   |
|   - meta/civd.json   <-- v0.5 capsule metadata         |
+--------------------------------------------------------+
| Volumetric Payload (3D tensor snapshot)                |
|   - dims: (X, Y, Z)                                    |
|   - channels: C (e.g. RGB + depth + semantics + etc.)  |
|   - layout: C- or F-contiguous                         |
+--------------------------------------------------------+
```

You **bake** a snapshot once, and then consumers mount it and read:

- **files** via the file table (e.g. `meta/civd.json`)
- **spatial regions** via ROI reads into tensors

---

## 2. Version overview

CIVD evolves in **feature levels** (v0.1, v0.2, …) while keeping the **core header** stable and v0.3-compatible.

### v0.3 — Core volumetric container

- 3D voxel volume + channels
- Fixed geometry chosen by the user
- Simple encode/decode of bytes → volume → bytes
- Foundation for robotics / AI volumetric data

### v0.4 — File bundles inside the volume

- Adds `CivdFileTableV04`, a compact in-capsule file table
- Supports **multi-file capsules** (e.g., map + waypoints + image)
- Introduces **CLI v0.4** for encoding, inspecting, and extracting
- Example: `examples/v04/preview.py`, `examples/v04/unpack.py`

### v0.5 — Adaptive geometry & capsule metadata

- **Adaptive geometry**: automatically chooses `(X, Y, Z)` based on payload size
- **Capsule metadata** (`meta/civd.json`):
  - Human + machine-readable description of what’s inside
  - Purpose, mission tags, group, minimum firmware, etc.
- No breaking changes: stays compatible with v0.3/v0.4 header and table

### v0.6 — Region-of-Interest (ROI) & spatial snapshots

- Introduces `roi_v06.py` and a **Region-of-Interest API** for dense volumes
- Logical view: `(Z, Y, X, C)` tensor in NumPy
- Functions like `read_region_from_bytes` and `full_volume_from_bytes` let you:
  - Load just a cube around the robot’s current position
  - Select only relevant channels (e.g. just semantics or velocity)
- Tested by `tests/test_roi_v06.py`
- Demonstrated in `examples/v06/roi_demo.py`

---

## 3. Repository layout

```text
corpus-informaticus/
├── specs/
│   ├── civd-v0.4-filetable.md      # v0.4 file table spec (example name)
│   ├── civd-v0.5-adaptive-geometry.md
│   └── civd-v0.6-roi.md
├── src/corpus_informaticus/
│   ├── __init__.py
│   ├── ci3_types.py                # core types for CIVD
│   ├── filetable_v04.py            # CIVD v0.4 file table implementation
│   ├── civd_v04_codec.py           # v0.4 encoder/decoder
│   ├── civd_v05_codec.py           # v0.5 encoder/decoder (adaptive + metadata)
│   ├── roi_v06.py                  # v0.6 ROI helpers (dense tensor view)
│   └── cli_v04.py                  # CLI: encode / inspect / extract
├── examples/
│   ├── hello_corpus/               # simple hello-world
│   ├── v03/                        # v0.3 round-trip examples
│   ├── v04/                        # preview + unpack for multi-file capsules
│   ├── v05/                        # v0.5 capsule with metadata
│   └── v06/                        # v0.6 ROI demo
├── tests/
│   └── test_roi_v06.py             # unit tests for ROI API
└── pyproject.toml                  # package definition
```

(Exact filenames may evolve, but the structure is intentionally clean: **specs → src → examples → tests**.)

---

## 4. Installing & running locally

Clone the repo:

```bash
git clone https://github.com/IoTIVP/corpus-informaticus.git
cd corpus-informaticus
```

Install in editable mode:

```bash
python -m venv .venv
.venv\Scripts\activate         # PowerShell on Windows
pip install -e .
```

Confirm import:

```bash
python -c "import corpus_informaticus; print('CIVD ready')"
```

---

## 5. v0.4: Multi-file capsules via CLI

v0.4 adds a file table and a CLI for encoding, inspecting, and extracting `.civd` capsules.

### 5.1. Encode a folder into a v0.4 capsule

Create a small test folder:

```bash
mkdir tmp_v04_test
echo "hello from file A" > tmp_v04_test/a.txt
echo "file B content"    > tmp_v04_test/b.txt
echo "CIVD rocks"        > tmp_v04_test/c.txt
```

Encode using the CLI:

```bash
python -m corpus_informaticus.cli_v04 encode tmp_v04_test tmp_v04_test.civd
```

### 5.2. Inspect the capsule

```bash
python examples/v04/preview.py tmp_v04_test.civd
```

Example output:

```text
=== CIVD v0.4 Capsule Preview ===
Path:          tmp_v04_test.civd
Dims:          (64, 64, 32)
Channels:      4
Orig length:   164
File count:    3
Table size:    64 bytes
Data region:   100 bytes
Payload size:  164 bytes

Files in capsule:
- a.txt  (40 bytes)   preview: hello from file A
- b.txt  (34 bytes)   preview: file B content
- c.txt  (26 bytes)   preview: CIVD rocks
```

### 5.3. Unpack the capsule

```bash
python examples/v04/unpack.py tmp_v04_test.civd
```

This writes a folder like `tmp_v04_test_unpacked/` with the decoded files.

---

## 6. v0.5: Adaptive geometry + capsule metadata

v0.5 moves geometry selection and metadata into the **codec behavior**, without changing the core header.

### 6.1. Adaptive cubic geometry

For a payload of size `N` bytes and `C` channels, v0.5 computes:

```text
voxels_needed = ceil(N / C)
d             = ceil(voxels_needed ** (1/3))
dims          = (d, d, d)
```

The encoder chooses a **minimal cube** that fits the payload. This is ideal for:

- predictable tensor shapes
- GPU-friendly memory layouts
- fixed-size allocations in robotics systems

### 6.2. Capsule metadata at `meta/civd.json`

Capsules can carry a small JSON descriptor:

```json
{
  "schema": "civd.meta.v1",
  "created": "2025-12-06T22:10:05Z",
  "mission": "robot_navigation_update",
  "tags": ["nav", "map", "vision"],
  "group": "robot_A/shift_5",
  "requires": {
    "robot_model": "XR-21",
    "min_fw": "2.5.1"
  }
}
```

The JSON lives inside the file table at:

```text
meta/civd.json
```

and is completely optional. Older decoders that just see “some random JSON file” remain valid.

### 6.3. v0.5 Python usage example

```python
from corpus_informaticus.civd_v05_codec import (
    encode_folder_to_civd_v05,
    decode_civd_v05,
)

capsule_meta = {
    "schema": "civd.meta.v1",
    "mission": "v05_demo_navigation",
    "tags": ["nav", "vision", "log"],
    "group": "robot_A/test_v05",
    "requires": {"robot_model": "XR-21", "min_fw": "2.5.1"},
}

# Encode a folder (e.g., tmp_v04_test) into a v0.5 capsule with metadata
blob, info = encode_folder_to_civd_v05("tmp_v04_test", capsule_meta=capsule_meta)
print("ENC info:", info)

# Decode back
table, files, meta = decode_civd_v05(blob)
print("DEC capsule_meta:", meta["capsule_meta"])

for name, data in files.items():
    print(name, "->", len(data), "bytes")
```

---

## 7. v0.6: ROI engine — spatial snapshots for AI & robotics

v0.6 introduces an explicit **Region-of-Interest (ROI) layer**.

Instead of always loading the full volume, you can read just a **3D cube** and (optionally) a subset of channels.

### 7.1. Volume specification (logical view)

`src/corpus_informaticus/roi_v06.py` defines:

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class VolumeSpecV06:
    dims: Tuple[int, int, int]   # (x, y, z)
    channels: int
    dtype: str = "uint8"
    order: str = "C"             # 'C' or 'F'
    signature: str = "C_CONTIG"  # logical layout
```

This gives a **logical view** of the volume for NumPy/tensor access.

### 7.2. Core ROI API

```python
from corpus_informaticus.roi_v06 import (
    VolumeSpecV06,
    read_region_from_bytes,
    full_volume_from_bytes,
)

spec = VolumeSpecV06(dims=(64, 64, 32), channels=4, dtype="uint8")

# Suppose 'volume_bytes' is a raw dense voxel buffer for that spec...
roi = read_region_from_bytes(
    buf=volume_bytes,
    spec=spec,
    x=0, y=0, z=0,          # origin of ROI
    w=16, h=16, d=16,       # size of ROI
    channels=[0, 1, 2],     # e.g. RGB only
    copy=True,
)

print("ROI shape:", roi.shape)   # (d, h, w, C_sel)
```

And for whole-volume ingestion:

```python
vol = full_volume_from_bytes(volume_bytes, spec, copy=False)
print("Volume shape:", vol.shape)  # (z, y, x, C)
```

### 7.3. ROI box & utilities

v0.6 also defines a small ROI box helper:

```python
from dataclasses import dataclass
from typing import Tuple

@dataclass(frozen=True)
class RoiV06:
    x: int
    y: int
    z: int
    w: int
    h: int
    d: int

    def as_bounds(self) -> Tuple[int, int, int, int, int, int]:
        return (
            self.x,
            self.x + self.w,
            self.y,
            self.y + self.h,
            self.z,
            self.z + self.d,
        )
```

Helpers:

- `clamp_roi(roi, dims)` — keep an ROI safely inside volume bounds
- `roi_to_slices(roi)` — convert ROI to NumPy slices `(z_slice, y_slice, x_slice)`
- `read_region_from_bytes_roi(...)` — ROI-based convenience wrapper

Unit tests live in `tests/test_roi_v06.py` and can be run with:

```bash
python tests/test_roi_v06.py
```

### 7.4. ROI demo

A small demo is in `examples/v06/roi_demo.py`, which:

- Builds a synthetic volume
- Picks an ROI
- Shows how ROI extraction works in practice

---

## 8. Why CIVD instead of “just use HDF5 / MCAP / ROS bag”?

CIVD does **not** try to replace mature containers everywhere. Instead, it explores a niche:

- **Single-shot spatial snapshots** for robots and AI systems
- **3D-native layout** with a volume as the first-class citizen
- **Multi-channel voxels** (RGB + depth + semantics + flow + whatever you want)
- A small, readable spec you can understand in an afternoon

Where CIVD aims to shine:

- **Robotics mission packs** — “Here is the environment, map, and mission in one file.”
- **Simulation / digital twin frames** — “Here is a snapshot of the world at T = 42.0s.”
- **AI training capsules** — “Here is a volumetric training example with all modalities aligned.”

CIVD is experimental by design. It should coexist with, not replace, things like ROS bags, HDF5, or MCAP.

---

## 9. Roadmap (high-level)

These are **exploratory directions**, not promises:

- **v0.7+ compression profiles**  
  - Block compression for sparse or mostly-empty volumes  
  - Optional GPU-accelerated compression/decompression

- **Streaming / chunked CIVD**  
  - Append-only or streamable variants for real-time sensors

- **Physics-aware & semantics-aware channels**  
  - Standard channel layouts for common robotics stacks  
  - Integration patterns for ROS / Isaac / PX4 / industrial systems

- **Crypto-sealed capsules (CIVD-Secure — future)**  
  - For environments that require tamper-evidence or attestation  
  - Would be layered on top of the foundational format, not baked in

---

## 10. Status

This repository is:

- **Work-in-progress** and experimental  
- Focused on **clarity, composability, and future-proof building blocks**  
- Open to feedback from the robotics, simulation, and AI communities

The path so far:

- v0.3 — core volumetric container
- v0.4 — file table & CLI
- v0.5 — adaptive geometry & capsule metadata
- v0.6 — ROI / spatial snapshot API

If you work on robotics, digital twins, or AI systems that care about **where** data is in space, CIVD is a place to experiment with new kinds of volumetric containers.

---

**License:** MIT  
**Author / Maintainer:** IoTIVP (and collaborators)  
**Project:** Corpus Informaticus — experiments in volumetric data for intelligent systems.
