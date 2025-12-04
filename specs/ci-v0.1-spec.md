# Corpus Informaticus v0.1 Specification

Version: 0.1  
File extension: `.ci3`  
Endianness: Little-endian for all numeric fields.

---

## 1. Purpose

Corpus Informaticus v0.1 defines a **3D volumetric container** for arbitrary byte data:

- A fixed-size 16×16×16 grid (4096 voxels)
- One byte of payload per voxel
- A small binary header and footer
- A simple integrity check (CRC32 over the volume bytes)

This is the minimal, working version of the “information body” format.

---

## 2. Volume Geometry

For v0.1 the corpus is:

- `X = 16`
- `Y = 16`
- `Z = 16`
- `channels = 1` (future expansion)

Total voxels: `X * Y * Z = 4096`  
Each voxel holds 1 byte → **4096 bytes of payload capacity**.

Coordinate ranges:

- `x ∈ [0, X - 1]`
- `y ∈ [0, Y - 1]`
- `z ∈ [0, Z - 1]`

---

## 3. Voxel Definition (Cellula Informatica v0.1)

A single voxel in v0.1:

```text
struct Voxel {
    uint8 payload;  // 0–255
}
