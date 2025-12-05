# CIVD v0.3 — Channel Semantics Specification

This document defines the **meaning, purpose, and behavior** of each channel in the CIVD v0.3 volumetric container.

CIVD is a multi–channel 3D data format. Each voxel contains **C channels**, and each channel holds a single byte (0–255). Channels allow CIVD to represent far richer structure than a flat 1‑D byte stream.

---

# 1. Channel Model

For v0.3, we define **4 canonical channels**, but the format supports *any* number of channels (C ≥ 1).  
Applications may choose to use more, fewer, or extend beyond these.

| Channel | Name           | Type        | Purpose |
|---------|----------------|-------------|---------|
| 0       | PAYLOAD        | Byte data   | Primary user payload (file bytes, message, sensor blob) |
| 1       | INTEGRITY      | Metric 0–255 | Per-voxel quality / anomaly / confidence indicator |
| 2       | SEMANTIC       | Label 0–255 | Class, modality, block-type, or robot/AI annotation |
| 3       | AUX            | Utility     | Reserved for future use / experimental fields |

Additional channels (4, 5, 6…) may be defined by applications.

---

# 2. Channel 0 — PAYLOAD (Required)

This channel is the **data-bearing channel**:

- Contains sequential encoded bytes.
- Unused voxels are zero‑filled.
- Maximum payload = X × Y × Z bytes (if channel count = 1).
- When multi-channel is used, only channel[0] is required for backward compatibility.

Extraction rule:

```
payload = volume[:,:,:,0].flatten()[:orig_length]
```

---

# 3. Channel 1 — INTEGRITY (Optional but recommended)

The INTEGRITY channel is designed for:

- anomaly detection  
- quality scoring  
- robotics mapping confidence  
- AI memory decay or weighting  
- voxel-level diagnostics  

**Interpretation (0–255):**

| Value Range | Meaning |
|-------------|---------|
| 0–15        | Corrupt / invalid |
| 16–63       | Low confidence |
| 64–191      | Normal / expected |
| 192–255     | High reliability / pristine |

In v0.3:
- All integrity bytes default to **255** (max quality).
- Later versions may introduce **parity planes**, **checksums**, or **predictive integrity maps**.

---

# 4. Channel 2 — SEMANTIC (Optional)

SEMANTIC provides a primitive, byte-scale taxonomy.  
Used for robotics, simulation, AI, and multi-modal datasets.

Examples:

| Semantic Byte | Meaning |
|---------------|---------|
| 0             | Unlabeled / default |
| 1             | Spatial metadata |
| 2             | Vision frame index |
| 3             | Depth/point-cloud block |
| 10–50         | Object classes |
| 200–255       | Custom application-defined |

Future versions will include:
- Lookup tables
- Embedding maps
- Region-level grouping

---

# 5. Channel 3 — AUX (Reserved)

AUX is explicitly left open to experimentation:

- time index  
- multi-view linking  
- block parity  
- cross-volume references  
- hashing  
- physics or simulation metadata  

No constraints in v0.3.

---

# 6. Application-Specific Channels

CIVD’s channel system is extensible.

You may define:

- Channel 4 = **Thermal band**  
- Channel 5 = **Robot joint states**  
- Channel 6 = **Simulation layer masks**  
- Channel 7 = **Sensor fusion weights**

These are **self-declared** in the application metadata (not inside the CIVD file header).

---

# 7. Default Initialization Rules

If channels > 1:

```
channel[0] = payload
channel[1] = 255 (max integrity)
channel[2] = 0   (semantic unknown)
channel[3] = 0   (aux unused)
channel[n>3] = 0
```

---

# 8. Visualization Behaviors (Recommended)

Tools should visualize channels as:

- PAYLOAD → grayscale intensity  
- INTEGRITY → red–green heatmap  
- SEMANTIC → categorical colors  
- AUX → grayscale or disabled  

---

# 9. Backward Compatibility

A v0.3 decoder must:

- Accept v0.1 1‑channel corpora  
- Treat missing channels as zero-filled  
- Ignore extra channels beyond expected  

---

# 10. Forward Compatibility

Future versions may include:

- Float channels (fp16/fp32)
- Sparse channel groups
- Hyperchannels (> 256)
- Learnable channel transforms

v0.3 is intentionally conservative and byte-only.

---

**End of Document**
