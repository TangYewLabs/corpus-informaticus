# Corpus Informaticus v0.2 Specification – Anatomy v1

Version: 0.2  
File extension: `.ci3`  
Endianness: Little-endian for all numeric fields.

---

## 1. Purpose

Corpus Informaticus v0.2 extends v0.1 by introducing **multi-channel voxels**.

Each voxel is no longer just a single payload byte. It becomes an **anatomical information cell** with 4 channels:

1. `payload`  – primary data
2. `integrity` – per-voxel integrity / quality measure
3. `semantic`  – semantic label/category
4. `aux`       – auxiliary channel for experiments / extensions

This forms the first **anatomy-aware Corpus**.

---

## 2. Volume Geometry

Same base geometry as v0.1:

- `dim_x = 16`
- `dim_y = 16`
- `dim_z = 16`
- `channels = 4` (new in v0.2)

Total voxels: `16 * 16 * 16 = 4096`  
Total channel slots: `4096 * 4 = 16384` bytes.

---

## 3. Voxel Definition (Cellula Informatica v1)

A single voxel in v0.2:

```text
struct Voxel_v1 {
    uint8 payload;    // primary data byte
    uint8 integrity;  // 0–255 integrity / quality score
    uint8 semantic;   // semantic label or type
    uint8 aux;        // auxiliary: flags, experimental data, etc.
}
