# Corpus Informaticus

A volumetric, tensor-native data container for representing information as a **3D body** instead of a flat byte stream.

This repo implements the first two protocol versions:

- **v0.1 – Single-channel corpus**
  - 16 × 16 × 16 grid (4096 voxels)
  - 1 byte per voxel (payload only)
  - Fixed-capacity container for arbitrary data up to 4096 bytes
  - CRC32 integrity over the whole volume

- **v0.2 – Anatomy v1 (multi-channel voxels)**
  - Same 16 × 16 × 16 geometry
  - 4 channels per voxel:
    - `payload`  – primary data
    - `integrity` – per-voxel integrity / quality (0–255, v0.2 uses 255 everywhere)
    - `semantic`  – semantic label (0 = unknown for now)
    - `aux`       – auxiliary / experimental
  - CRC32 over all channels
  - Still 4096 bytes of payload capacity, but now with an anatomical field around it

The goal is to explore **multi-dimensional data transfer and storage** for:

- Robotics & simulation
- 3D sensing and digital twins
- AI memory structures and volumetric embeddings

---

## Layout

```text
corpus-informaticus/
  README.md
  specs/
    ci-v0.1-spec.md   # v0.1 formal spec
    ci-v0.2-spec.md   # v0.2 anatomy spec
  src/
    corpus_informaticus/
      __init__.py
      ci3_types.py     # header/footer defs, constants
      ci3_codec.py     # v0.1 + v0.2 encode/decode
      ci3_visualizer.py# simple slice viewer for v0.1
  examples/
    hello_corpus/      # v0.1 string demo + slice view
    file_roundtrip/    # v0.1 arbitrary file → CI3 → file
    v02/               # v0.2 encode/decode + channel inspection
