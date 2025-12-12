# CIVD – Corpus Informaticus Volumetric Data

> A tiny research codec for **3D tensor capsules** – snapshotting multi‑channel volumes,
> file payloads, and robotics metadata into a single `.civd` container.

<p align="center">
  <img src="docs/media/civd_snapshot_tiling.png" width="90%">
</p>

---

<p align="center">

<a href="#-roadmap--status"><img src="https://img.shields.io/badge/status-research_proto-blueviolet" alt="Status: Research Prototype"></a>
<a href="#-features"><img src="https://img.shields.io/badge/api-python3-informational" alt="Python 3"></a>
<a href="#-getting-started"><img src="https://img.shields.io/badge/civd-v0.3--v0.7-green" alt="CIVD versions"></a>
<a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-lightgrey" alt="License: MIT"></a>

</p>

---

## Why CIVD exists

Most data formats are either:

- **File‑centric** (ZIP, TAR, HDF5, MCAP) – great for logs and events, but not native to 3D tensors.
- **Volume‑centric** (OpenVDB, NIfTI, raw tensors) – great for 3D grids, but awkward for bundling extra files,
  mission descriptors, or metadata.

**CIVD** sits in the middle:

- Treats a **3D volume as the primary object** – a dense multi‑channel tensor.
- Allows you to attach **files and metadata** around that volume (maps, configs, mission JSON, logs).
- Is intentionally **small, inspectable, and experimental** – meant for robotics labs, AI research,
  digital twins, and simulation workflows.

Think of a CIVD file as a **3D mission cartridge**:
a voxel grid + manifest + attachments in a single portable blob.

---

## High‑level architecture

CIVD (as implemented in this repo) is evolving through small, versioned steps:

- **v0.3 – Core header + dense volume**
- **v0.4 – File table capsules (multi‑file payloads)**
- **v0.5 – Adaptive geometry + capsule metadata**
- **v0.6 – Region‑of‑interest (ROI) volume access**
- **v0.7 – Tiling and scale‑out (tile packs)**

The core ideas:

1. A **dense multi‑channel 3D tensor** (x, y, z, C) stored as bytes.
2. A small **header + file table** (for multi‑file capsules).
3. Optional **capsule metadata** (JSON) describing what is inside.
4. A set of **Python helpers** for:
   - encoding / decoding capsules,
   - reading arbitrary ROIs from volumes,
   - tiling large volumes into per‑tile binaries for streaming and scale‑out.

---

## 📦 Version timeline

### v0.3 – Core dense capsule

- Single payload → encoded into a 3D volume with configurable dimensions + channels.
- Simple encode/decode round‑trip helpers.

Key implementation:
- `src/corpus_informaticus/codec_v03.py`
- `examples/v03/file_to_civd_v03.py`
- `examples/v03/civd_to_file_v03.py`

### v0.4 – Multi‑file capsules (file table)

- Introduces a **file table** for multiple named payloads in one capsule.
- Adds a clean separation between:
  - **table region** (names, offsets, sizes), and
  - **data region** (flattened byte payload).

Key implementation:
- `src/corpus_informaticus/filetable_v04.py`
- `src/corpus_informaticus/civd_v04_codec.py`
- Examples:
  - `examples/v04/preview.py`
  - `examples/v04/unpack.py`

Example usage:

```bash
python examples/v04/preview.py tmp_v04_test.civd
python examples/v04/unpack.py tmp_v04_test.civd
```

### v0.5 – Adaptive geometry & metadata

CIVD v0.5 is a **behavioral** upgrade:

- The encoder chooses a **cube volume automatically** based on payload size.
- Each capsule can carry optional metadata at `meta/civd.json`.

Spec:
- `specs/civd-v0.5-adaptive-geometry.md`

Core behavior (conceptual):

```python
from corpus_informaticus.civd_v05_codec import encode_folder_to_civd_v05

capsule_meta = {
    "schema": "civd.meta.v1",
    "mission": "robot_navigation_update",
    "tags": ["nav", "map", "vision"],
    "group": "robot_A/shift_5",
    "requires": {"robot_model": "XR-21", "min_fw": "2.5.1"},
}

blob, info = encode_folder_to_civd_v05("nav_payload_folder", capsule_meta=capsule_meta)
```

### v0.6 – Region‑of‑interest (ROI) volume access

v0.6 introduces a **logical view of dense volumes** and ROI helpers.

Core concepts:

- `VolumeSpecV06` – describes a dense 3D tensor:
  - dims = (x, y, z)
  - channels
  - dtype (e.g. `"uint8"`, `"float32"`)
  - memory order (`"C"`/`"F"`)
  - signature (`"C_CONTIG"`, `"F_CONTIG"`)
- `read_region_from_bytes(...)` – extract a `(d, h, w, C_sel)` sub‑tensor given x/y/z + w/h/d.
- ROI helper type `RoiV06` + `clamp_roi(...)` for safe, in‑bounds region queries.

Implementation:
- `src/corpus_informaticus/roi_v06.py`
- `examples/v06/roi_demo.py`
- Spec: `specs/civd-v0.6-roi.md`

Visualization (conceptual layout):

![Voxel Anatomy](docs/media/voxel_anatomy.png)

Every CIVD dense volume is treated as a **4D tensor**:

```text
(z, y, x, channels)
```

`roi_v06` provides precise, array‑friendly slices into that tensor.

### v0.7 – Tiling & scale‑out

v0.7 addresses **scale**: how do we handle large volumes without loading everything at once?

We introduce a **tiling layer**:

- Partition a dense volume into fixed‑size 3D tiles (`tile_size = (tx, ty, tz)`).
- Store per‑tile binaries (e.g. `tile_tx1_ty2_tz3.bin`).
- Maintain a **tiling manifest** (`tiling_manifest.json`) describing:
  - volume dims
  - tile size
  - number of tiles along each axis
- Provide helpers to:
  - tile an in‑memory buffer,
  - write a tile pack directory,
  - query which tiles intersect a given ROI.

Implementation:
- `src/corpus_informaticus/tile_manifest_v07.py`
- `src/corpus_informaticus/tile_pack_v07.py`
- `examples/v07/tile_pack_demo.py`
- Spec: `specs/civd-scaling-tiling-v0.7.md`

Conceptual layout of a **tile pack**:

```text
tile_pack_root/
├── tiling_manifest.json
├── tile_tx0_ty0_tz0.bin
├── tile_tx0_ty0_tz1.bin
├── tile_tx0_ty1_tz0.bin
├── tile_tx0_ty1_tz1.bin
├── tile_tx1_ty0_tz0.bin
├── tile_tx1_ty0_tz1.bin
├── tile_tx1_ty1_tz0.bin
└── tile_tx1_ty1_tz1.bin
```

The ROI + tiling story:

- **v0.6** says: “Here’s how to precisely slice the volume tensor.”
- **v0.7** says: “Here’s how to split that volume into tiles and choose which tiles matter for a given ROI.”

The combination is what makes CIVD usable for **large‑scale robotics and AI** workloads.

---

## 🔧 Getting started

### 1. Clone & install (editable)

```bash
git clone https://github.com/TangYewLabs/corpus-informaticus.git
cd corpus-informaticus

python -m venv .venv
source .venv/bin/activate   # PowerShell: .venv\Scripts\Activate.ps1

pip install -e .
```

### 2. Run basic examples

v0.3 round‑trip:

```bash
python examples/v03/file_to_civd_v03.py
python examples/v03/civd_to_file_v03.py
```

v0.4 multi‑file capsule preview + unpack:

```bash
python examples/v04/preview.py tmp_v04_test.civd
python examples/v04/unpack.py tmp_v04_test.civd
```

v0.5 encoding with metadata:

```bash
python examples/v05/encode_with_meta.py
python examples/v05/preview_with_meta.py
```

v0.6 ROI demo (region‑of‑interest reads):

```bash
python examples/v06/roi_demo.py
```

v0.7 tiling demo (tile packs + ROI‑relevant tiles):

```bash
python examples/v07/tile_pack_demo.py
```

> Note: Paths and filenames in examples are intentionally small and
> simple. They are intended as **reference code**, not production utilities.

### 3. Run tests

```bash
python tests/test_roi_v06.py
python tests/test_tile_pack_v07.py
```

These cover:

- ROI math and clamping to volume bounds.
- Tiling correctness (dimensions, tile naming, manifest fields).
- Mapping ROIs to the correct set of tiles.

---

## 🧠 How to think about CIVD in your stack

CIVD is:

- A **research‑grade container** for:
  - robot mission snapshots,
  - multi‑sensor 3D fields,
  - digital twin states,
  - simulation assets + configs.
- A way to unify:
  - **structured tensors** (the volume),
  - **unstructured files** (logs, configs, models),
  - **explicit metadata** (`meta/civd.json`).

Notably, CIVD is **not**:

- A general‑purpose filesystem.
- A streaming event log.
- A compression library.

Instead, treat a `.civd` file as a **baked snapshot**:

1. Gather the files + tensors you care about.
2. Encode once into a CIVD capsule or tile pack.
3. Deploy it as a read‑mostly artifact to robots, simulators, or AI systems.

This avoids the complexity of live mutation and focuses on **fast, predictable reads**.

---

## 🔭 Roadmap toward v1.0 (high‑level)

The current line (v0.3–v0.7) establishes:

- Header + dense volume (v0.3).
- File‑table capsules (v0.4).
- Adaptive geometry / metadata (v0.5).
- ROI access (v0.6).
- Tiling & scaling (v0.7).

Candidate directions as we move toward v1.0:

1. **Compression‑aware volumes**
   - Pluggable compression (e.g. Zstd/LZ4) per capsule or per tile.
   - Metadata to describe compression choices.

2. **Multi‑capsule mission packs**
   - Simple manifests for sets of CIVD files per mission / scene.

3. **GPU‑friendly interop**
   - Clear mapping to CUDA / PyTorch / JAX tensors.
   - Zero‑copy slicing for compatible layouts.

4. **Production‑grade reference readers**
   - C++ / Rust implementations for embedded and robotics stacks.

Security, cryptographic sealing, and deep enterprise hardening are explicitly **out of scope for this repo**.
Those belong in higher‑level systems that adopt CIVD as one of their internal container formats.

---

## 📁 Repository layout (abridged)

```text
src/corpus_informaticus/
    __init__.py
    codec_v03.py            # v0.3 single‑payload codec
    filetable_v04.py        # v0.4 file table
    civd_v04_codec.py       # v0.4 multi‑file capsules
    civd_v05_codec.py       # v0.5 adaptive geometry + metadata
    roi_v06.py              # v0.6 volume + ROI helpers
    tile_manifest_v07.py    # v0.7 tiling metadata
    tile_pack_v07.py        # v0.7 tiling engine

examples/
    v03/                    # v0.3 round‑trip examples
    v04/                    # v0.4 preview/unpack examples
    v05/                    # v0.5 metadata examples
    v06/                    # v0.6 ROI demo
    v07/                    # v0.7 tiling demo

specs/
    civd-v0.5-adaptive-geometry.md
    civd-v0.6-roi.md
    civd-scaling-tiling-v0.7.md

tests/
    test_roi_v06.py
    test_tile_pack_v07.py

docs/media/
    banner.png
    voxel_anatomy.png
```

---

## ⚠️ Disclaimer

This repository is:

- Experimental
- Evolving
- Not yet optimized or hardened for production environments

Use it as a **playground and reference implementation** for:

- 3D tensor capsules
- spatial snapshots
- tiling strategies for large volumetric data

Contributions, feedback, and critique from robotics, simulation,
and AI infrastructure engineers are very welcome.
