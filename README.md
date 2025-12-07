# CIVD v0.4 — Corpus Informaticus 3D Data Capsule
### Unified 3D-Native File Capsules for Robotics, IoT, Edge, and Autonomous Systems

CIVD (Corpus Informaticus Volume Descriptor) is a **3D-native data capsule format** that stores any number of files inside a single volumetric container represented as a `(X × Y × Z × C)` dense tensor.

Unlike archives such as `.zip` or `.tar`, CIVD is **natively volumetric** and designed for robotics, autonomous navigation, multi-sensor fusion, drones/UAVs, digital twins, AI/ML pipelines, and embedded/edge devices.

## 1. What Makes CIVD Different

### 1.1 Not an Archive — a Data Capsule
CIVD does not compress or pack like traditional archives. It maps files directly into a 3D tensor, enabling:
- instant metadata access without unpacking  
- fast preview and partial reads  
- robot-grade reproducibility  
- direct GPU/ML ingestion  
- zero-dependency restores

### 1.2 Three-Layer Capsule Design
1. **3D Tensor Volume (v0.3)**  
2. **File Table (v0.4)**  
3. **Header/Footer Integrity Block**

## 2. Capsule Structure (v0.4)
```
[Header]
[File Table]
[Payload Volume]
[CRC Footer]
```

Each embedded file includes:
- name  
- mime  
- offset  
- size  
- flags  
- checksum  

## 3. Usage

### 3.1 Encode Folder → CIVD
```python
from corpus_informaticus.civd_v04_codec import encode_folder_to_civd_v04
blob, info = encode_folder_to_civd_v04("folder")
open("folder.civd", "wb").write(blob)
```

### 3.2 Decode CIVD
```python
table, files, meta = decode_civd_v04(blob)
```

### 3.3 Preview
```bash
python examples/v04/preview.py capsule.civd
```

### 3.4 Unpack
```bash
python examples/v04/unpack.py capsule.civd
```

## 4. Implemented Features in v0.4
- Multi-file capsules  
- UTF-8 filenames  
- File table with checksums  
- Full preview & selective access  
- 3D volumetric storage  
- v0.3 backend compatible  

## 5. Roadmap to v0.5
- Sparse tensor format  
- LZ4/FastPFor compression  
- MIME registry  
- Partial tensor reads  
- Capsule signing  

## 6. Installation
```bash
pip install -e .
```

## 7. Repo Structure
```
corpus-informaticus/
  specs/
  src/corpus_informaticus/
  examples/v04/
```

## 8. Status
CIVD v0.4 is fully operational and validated end-to-end.

