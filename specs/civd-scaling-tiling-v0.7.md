# CIVD v0.7 — Scale & Tiling Specification

**Status:** Draft  
**Author:** Mike + Corpus Informaticus Engineering  
**Audience:** Robotics, Simulation, AI Infrastructure, HPC  

---

# 1. Motivation

CIVD v0.6 introduced dense volumetric snapshots and high-performance ROI extraction. However, dense volumes scale poorly beyond ~256³–512³ depending on hardware constraints.

To handle large environments, high-resolution twins, multi-sensor tensors and more, we introduce formal tiling, streaming, and multi-capsule orchestration.

v0.7 moves CIVD from *format* → *scalable volumetric data system*.

---

# 2. Scaling Strategy Overview

## 2.1 Capsule Tiling  
Divide the global volume into NxNxN tiles; each tile is its own `.civd` capsule.

## 2.2 Multi-Resolution Pyramid  
Optional downscaled levels (L0 full res → L1 half res → ...).

## 2.3 Temporal Tiling  
Tiles can exist across time steps.

---

# 3. Tiled Capsule Structure

Each tile has metadata including index, tile dims, global dims, origin voxel, resolution.

---

# 4. Dataset Layout

```
scene/
    dataset.json
    tiles/
        x0_y0_z0.civd
        x0_y1_z0.civd
        ...
```

---

# 5. ROI Query Model

Global ROI is resolved into tile-local ROI operations then merged.

---

# 6. GPU Streaming

Async mmap → pinned memory → CUDA ingestion.

---

# 7. Compression

Per tile compression: `"nvcomp_lz4"`, `"blosc"`, `"none"`.

---

# 8. Guarantees & Constraints

CIVD is a baked format. Tiled-streaming allows high scalability.

---

# 9. Tile Generation Algorithms

Dense → Tiled  
Tiled → Dense reconstruction (optional)

---

# 10. Use Cases

Robotics, simulation, AI training, medical imaging, mapping, SLAM.

---

# 11. Version Notes

v0.7 introduces tiling. v0.8 Morton-ordering. v0.9 GPU-native compression. v1.0 stable long-term.

---

# 12. Example Metadata

```json
{
  "civd_version": "0.7",
  "tile": {
    "index": [3,0,1],
    "tile_dims": [256,256,256],
    "global_dims": [2048,2048,2048],
    "origin_voxel": [768,0,256],
    "resolution_meters": 0.05
  },
  "volume": {
    "channels": 8,
    "dtype": "uint16",
    "signature": "C_CONTIG"
  },
  "compression": "blosc"
}
```

---

# 13. Implementation Roadmap

Reader/writer, tile coordinate math, global ROI engine, generator scripts, visualization, caching.

---

# 14. Boardroom Summary

CIVD tiling transforms CIVD into a scalable volumetric OS for robots and simulations — 3D EXR for machines.
