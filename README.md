# Corpus Informaticus (CIVD)
A multi‑dimensional volumetric data container for robotics, AI, and simulation systems.

---

# Overview

**Corpus Informaticus (CIVD)** is an experimental data container that stores information as a **3D voxel volume** instead of a traditional linear byte stream.

It is designed for:

- Robotics  
- Simulation engines  
- Multi‑modal AI memory  
- Sensor fusion systems  
- Digital twins  
- Scientific or geometric pipelines  

The project explores how **3D + multi‑channel data capsules** may become a next‑generation format for machine perception and high‑integrity data transfer.

---

# File Format Evolution

## v0.1 — Single‑Channel Corpus (Fixed Geometry)

- 16 × 16 × 16 grid (4096 voxels)  
- 1 payload byte per voxel (4 KB capacity)  
- Lossless round‑trip for any file ≤ 4096 bytes  
- CRC32 integrity  
- Tools:  
  - Hello Corpus  
  - `.ci3` roundtrip  
  - 2D slice visualization  

Example:

```
python examples/hello_corpus/encode_hello.py
python examples/hello_corpus/decode_hello.py
python examples/file_roundtrip/file_to_ci3.py <file>
```

---

## v0.2 — Multi‑Channel (Anatomy v1)

- Same 16 × 16 × 16 geometry  
- **4 channels per voxel**:
  - `payload`
  - `integrity`
  - `semantic`
  - `aux`
- CRC32 across all channels  
- NumPy‑based slice visualization  

Example:

```
python examples/v02/encode_v02.py
python examples/v02/view_slice.py
```

---

# CIVD v0.3 — Dynamic Volumes (Experimental)

CIVD v0.3 introduces the **first real breakthrough**:  
**Arbitrary 3D volumes + configurable channel count.**

## v0.3 Features

- Dynamic dimensions `(X, Y, Z)`  
- Dynamic channels `(C ≥ 1)`  
- Backward‑compatible layout  
- Suitable for robotics & AI tensor workflows  
- `.civd` is the new official file extension

## Where the Codec Lives

```
src/corpus_informaticus/codec_v03.py
```

## Core Usage

```python
from corpus_informaticus.codec_v03 import encode_v03, decode_v03

payload_bytes = b"HELLO V03"
blob = encode_v03(payload_bytes, dims=(32,32,32), channels=4)
info = decode_v03(blob)

print(info["payload"] == payload_bytes)  # True
print(info["header"].dim_x, info["header"].channels)
```

Explanation:

- **payload_bytes** — original 1D byte stream  
- **dims** — volume size (X, Y, Z)  
- **channels** — number of per‑voxel channels  
  - e.g., 4 = payload + integrity + semantic + aux  

---

# CIVD v0.3 – File Roundtrip Example

Encode:

```
python examples/v03/file_to_civd_v03.py examples/file_roundtrip/sample.txt
```

Decode:

```
python examples/v03/civd_to_file_v03.py examples/file_roundtrip/sample.txt.civd
```

Verify:

```
type examples/file_roundtrip/sample.txt
type examples/file_roundtrip/sample.restored.txt
```

If both match → v0.3 roundtrip is successful.

---

# Purpose of CIVD v0.3

CIVD v0.3 represents a shift from flat data → geometric data.

A `.civd` file can hold:

- Raw payload bytes (channel 0)  
- Integrity/quality map (channel 1)  
- Semantic tags or class labels (channel 2)  
- Auxiliary metadata (channel 3)  
- Additional custom channels (thermal, depth, simulation masks, etc.)

This makes CIVD a **3D data capsule**, aligned with how machines sense the world.

---

# Specs

All format specifications live under:

```
specs/
```

- `civd-v0.3-dynamic-dims.md`  
- `civd-v0.3-encoding.md`  
- `civd-v0.3-channel-semantics.md`

These define:

- Header layout  
- Volume rules  
- Channel semantics  
- CRC32 model  
- Encoding/decoding pipeline  

---

# Examples

Everything demonstrative lives under:

```
examples/
```

Folders:

- `hello_corpus/`
- `file_roundtrip/`
- `v02/`
- `v03/` ← New dynamic volume examples

Use these to test or build your own pipeline.

---

# Roadmap

## v0.3 → v0.4
- Integrity parity maps  
- Semantic region labeling  
- Optional compression strategies  

## v0.4 → v1.0
- Stable file spec  
- PyPI release (`pip install corpus-informaticus`)  
- Viewer app (slices, heatmaps, tensor views)  
- Bindings for:
  - ROS2  
  - Isaac Sim  
  - Unity / ML‑Agents  
  - Web visualization  

---

# Status

CIVD is experimental and evolving.  
You are free to inspect, test, break, and expand it.

Issues, ideas, and contributions are welcome.

---

# License

MIT License — free for research, commercial, or personal use.
