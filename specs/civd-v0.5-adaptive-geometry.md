# CIVD v0.5 — Adaptive Geometry & Capsule Metadata (Enhanced Full Specification)

CIVD v0.5 introduces two major behavioral upgrades that transform the CIVD container format from a static 3D volume encoder into a **self-describing, adaptive, robotics-ready capsule system**:

1. **Adaptive Geometry** — Automatic 3D layout selection based on payload size.  
2. **Capsule Metadata (`meta/civd.json`)** — Machine-readable semantic descriptors embedded inside the capsule.

This release preserves 100% compatibility with CIVD v0.3 and v0.4 while adding capabilities required for real-world robotics, simulation, digital twins, autonomous systems, and IoT micro-agents.

---

## 1. Versioning Model

CIVD defines two kinds of version identifiers:

### 1.1. Container Version  
Stored in the binary header (`version` field).  
For v0.5, the container header format **does not change** from v0.3/v0.4.

### 1.2. Feature Level  
The specification version (v0.1 → v0.5), which describes how the codec *behaves*.

v0.5 is a **behavioral upgrade** rather than a structural one:
- Geometry computation algorithm updated.
- Metadata conventions introduced.
- File table remains the v0.4 structure.
- Old decoders work without modification.

---

## 2. Adaptive Geometry Behavior

### 2.1. Capacity Formula

```
capacity_bytes = dim_x * dim_y * dim_z * channels
```

### 2.2. v0.5 Geometry Selection Algorithm

Given:
- Payload size: `N` bytes  
- Channels: `C` (default = 4)

Steps:

1. Compute voxel count required:
   ```
   voxels_needed = ceil(N / C)
   ```

2. Compute cubic dimension:
   ```
   d = ceil(voxels_needed ** (1/3))
   ```

3. Geometry becomes:
   ```
   dims = (d, d, d)
   ```

### 2.3. Rationale for Cubic Geometry

Cubes provide:
- Uniform GPU tensor mapping  
- Perfect alignment for CUDA warp/block layouts  
- Simple linear indexing for microcontrollers  
- Predictable DMA transfer patterns  
- Fast zero-copy memory regions in robotics stacks  
- Clean integration into 3D simulation engines (Isaac Sim, Gazebo, Webots)

This makes CIVD feasible for:
- Real-time robotics  
- Lightweight IoT firmware  
- Multi-sensor fusion  
- Autonomous vehicle mission capsules  

---

## 3. Capsule Metadata (`meta/civd.json`)

Metadata is an **internal virtual file** inside the CIVD file table, located at:

```
meta/civd.json
```

### 3.1. Purpose of Metadata

Metadata describes the **semantic meaning** of the capsule:

- **mission** – why this capsule exists  
- **tags** – domain categories (nav/map/vision/etc.)  
- **group** – logical grouping across robots, shifts, or mission sets  
- **requires** – firmware/hardware compatibility  
- **created** – ISO timestamp  
- **schema** – version of metadata schema  

### 3.2. Metadata Schema (v1)

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

### 3.3. Why Use JSON?

- Universal  
- Human-readable  
- Fully machine-readable  
- Supported by all robotics ecosystems  
- Can be validated externally or internally  

---

## 4. v0.5 Interoperability

### 4.1. Backward Compatibility (v0.3 / v0.4)

Older decoders:
- Read header normally  
- Parse file table normally  
- Ignore extra “unknown files” like `meta/civd.json`  

### 4.2. Forward Compatibility (v0.6+)

v0.6+ will support:
- Multi-geometry  
- Delta capsules  
- Real-time streaming capsules  
- Physical-world metadata (IMU, LiDAR descriptors)  
- Cryptographically sealed capsules  

No breaking changes are expected.

---

## 5. Example Encoding with v0.5

### 5.1. Input Payload

```python
payloads = {
    "nav/map.pcd": map_bytes,
    "nav/waypoints.json": waypoints_json_bytes,
    "vision/front.jpg": camera_jpeg,
    "meta/civd.json": metadata_json_bytes
}
```

### 5.2. v0.5 Encoder Invocation

```python
blob, info = encode_folder_to_civd_v05(payloads)
```

Output:
- Encoded CIVD binary  
- Geometry info  
- File table details  

### 5.3. v0.5 Decoder Invocation

```python
table, files, meta = decode_civd_v05(blob)
print(meta["mission"])
```

---

## 6. Example Capsule Layout

```
ROOT
│
├── meta/
│   └── civd.json
│
├── nav/
│   ├── map.pcd
│   └── waypoints.json
│
├── vision/
│   └── front.jpg
│
└── voxel_volume.bin
```

- The **voxel volume** remains opaque until decoded.
- File table stores structured content.

---

## 7. Why v0.5 Matters for Robotics & AI

### 7.1. Predictable Ingestion

Robots can pre-allocate:
- Memory  
- GPU tensors  
- Compute slot assignments  

### 7.2. Domain-Aware Capsules

Metadata lets robots immediately classify capsules:
- Navigation  
- Perception  
- Diagnostics  
- Logs  
- Training data  
- Mission updates  

### 7.3. Digital Twin Integration

Containers can be:
- Paired with simulation scenes  
- Timestamped for replay  
- Compared across mission deltas  

### 7.4. Multi-Sensor Fusion Pipelines

CIVD v0.5 capsules can store:
- LiDAR  
- Radar  
- Stereo images  
- IMU patches  
- Segmentation masks  
- Robot-local maps  
- Temporal deltas  

---

## 8. Specification Summary (v0.5)

| Feature | Description |
|--------|-------------|
| Geometry | Auto-selected cubic volume |
| Metadata | JSON at `meta/civd.json` |
| File Table | Same as v0.4 |
| Header | Same as v0.3/v0.4 |
| Channels | 1–8 recommended |
| Applications | AI, robotics, IoT, digital twins |
| Breaking changes | None |
| Backward compatible | 100% |

---

## 9. Future Roadmap (v0.6 → v1.0)

### v0.6 (Next)
- Multi-geometry volumes  
- Channel-level typing  
- Physics metadata blocks  
- Multi-capsule packaging  

### v0.7
- Streaming (continuous CIVD)  
- Real-time robotics telemetry capsules  

### v0.8  
- ML training capsules (differentiable CIVD)  

### v1.0  
- Cryptographically sealed CIVD capsules (“CIVD‑Secure”)  
- Provenance metadata  
- Tamper-evident voxel regions  

---

## 10. Status

**CIVD v0.5 is approved and ready for implementation.**  
It introduces:
- Zero breaking changes  
- Significant new capabilities  
- Robotics-ready metadata  
- Automatic geometry selection  

This version is now stable and should be implemented in `civd_v05_codec.py` and future CLI tools.

---

**End of Full Specification**