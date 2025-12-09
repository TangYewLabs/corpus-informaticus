# CIVD v0.6 — Region-of-Interest (ROI) & Volume Spec

CIVD v0.6 formalizes the **3D volume plane** of a CIVD capsule.

Up to v0.5, the format defined:

- A 3D **voxel container** (v0.3)
- A **file table** for multiple logical files (v0.4)
- **Adaptive geometry** and **capsule metadata** (v0.5)

v0.6 adds:

1. A **canonical volume layout** description (`VolumeSpecV06`)
2. A standard, implementation-agnostic definition of:
   - How to compute **linear offsets** into the dense volume
   - How to extract a **Region-of-Interest (ROI)** as a 3D sub-volume tensor
3. Clear separation between:
   - **File plane** (random-access logical files)
   - **Volume plane** (dense, tensor-like spatial snapshot)

CIVD v0.6 is aimed directly at **robotics, simulation, and AI pipelines** that need fast, deterministic access to localized 3D regions inside a larger spatial snapshot.

---

## 1. Versioning & compatibility

CIVD v0.6 is a **behavioral extension** on top of v0.5:

- The **on-disk header** remains v0.3-compatible.
- The **file table layout** remains v0.4-compatible.
- v0.5’s **adaptive geometry** and `meta/civd.json` conventions remain unchanged.
- v0.6 formally defines how the **dense volume** is described and accessed.

In other words:

- A **v0.6 capsule** is still a valid v0.3/v0.4/v0.5 capsule.
- Older decoders:
  - Can ignore v0.6 conventions.
  - Can still treat the voxel region as an opaque blob.
- v0.6-aware decoders gain:
  - A **standard VolumeSpec**
  - A standard **ROI access pattern**

---

## 2. Mental model — dual plane design

A CIVD capsule is conceptually split into two cooperating planes:

1. **File plane** (logical files)
   - Implemented via the v0.4 file table.
   - Provides `read_file(name) -> bytes`.
   - Holds things like:
     - `meta/civd.json` (capsule-level metadata)
     - JSON configs
     - Small images, logs, scripts, etc.

2. **Volume plane** (dense 3D tensor)
   - A single **dense voxel volume** (or a small number of them in future versions).
   - Provides **region-of-interest (ROI)** access:
     - `read_region(x, y, z, w, h, d, channels=None) -> tensor`

The **volume plane** is where CIVD becomes **AI-native and robotics-native**:

- You can think of it as a "mission tensor":
  - A frozen snapshot of space, state, or environment.
  - Directly mappable to GPU tensors and simulation grids.

---

## 3. VolumeSpecV06 — canonical volume description

v0.6 introduces a canonical **VolumeSpec** structure that describes how to interpret the dense volume.

### 3.1. Logical structure

A volume is:

- A **dense 4D tensor**:

```
V[z, y, x, c]   where:
  0 <= z < dim_z
  0 <= y < dim_y
  0 <= x < dim_x
  0 <= c < channels
```

- Backed by a **contiguous byte buffer** in the capsule.

### 3.2. VolumeSpecV06 fields

A `VolumeSpecV06` contains:

- `dims`: `(dim_x, dim_y, dim_z)` — integer dimensions along X/Y/Z
- `channels`: integer number of channels per voxel (e.g., 1–8 typical)
- `dtype`: the scalar type of each channel  
  (e.g., `"u8"`, `"u16"`, `"f16"`, `"f32"`, `"f64"`)
- `layout`: memory layout descriptor  
  v0.6 defines a single canonical layout: `"zyxc"` (C‑contiguous with channels innermost)
- `offset_bytes`: byte offset to the first voxel inside the packed volume
- `stride_bytes`: optional stride hints (reserved for future)
- `voxel_size`: optional physical spacing (`dx, dy, dz`)
- `channels_meta`: optional list describing semantics of channels

### 3.3. Canonical layout `"zyxc"`

Physical memory is ordered:

```
index = (((z * dim_y + y) * dim_x + x) * channels) + c
offset = base_offset + index * bytes_per_channel
```

This matches GPU‑friendly tensor formats.

---

## 4. ROI access — Region of Interest

### 4.1. ROI definition

Defined by:

- Origin `(x, y, z)`
- Size `(w, h, d)`
- Optional subset of `channels`

### 4.2. ROI API

```
read_region(x, y, z, w, h, d, channels=None) -> tensor
```

Returns tensor of shape:

- `(d, h, w, channels_full)` or  
- `(d, h, w, len(channels))`

### 4.3. ROI math

Using canonical `"zyxc"` layout — no ambiguity.

---

## 5. Integration with v0.5 metadata

Recommended block inside `meta/civd.json`:

```json
{
  "version": "v0.6",
  "dims": [256, 256, 64],
  "channels": 4,
  "dtype": "f32",
  "layout": "zyxc",
  "voxel_size": [0.1, 0.1, 0.1],
  "channels_meta": [
    {"index": 0, "name": "r", "semantic": "color_r"},
    {"index": 1, "name": "g", "semantic": "color_g"},
    {"index": 2, "name": "b", "semantic": "color_b"},
    {"index": 3, "name": "depth", "semantic": "sensor_depth"}
  ]
}
```

---

## 6. Example usage

ROI extraction from a decoded capsule is shown in `examples/v06/roi_demo.py`.

---

## 7. Non-goals in v0.6

- No sparse volumes  
- No compression  
- No encryption  
- No streaming  
- No multi-volume capsules  

---

## 8. Motivation & impact

CIVD v0.6 is:

- Robotics‑native  
- GPU‑optimized  
- AI‑tensor aligned  
- Backward compatible  
- Deterministic and architecture‑friendly  

---

## 9. Summary

v0.6 standardizes:

- `VolumeSpecV06`
- Canonical 3D tensor layout
- ROI slicing semantics
- Metadata integration

---

## 10. Status

**CIVD v0.6 — ROI & Volume Spec is approved and ready for implementation.**
