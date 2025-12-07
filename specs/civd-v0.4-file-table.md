# CIVD v0.4 — Embedded File Table & Multi-File Capsules

Version: **0.4**  
Status: **Draft / Implementation Target**  
Depends on: **CIVD v0.3 – Dynamic Dimensions & Channels**

---

## 1. Purpose

CIVD v0.4 extends CIVD from a *single opaque payload* into a **multi-file container** that can hold:

- multiple binary files  
- metadata per file  
- optional semantic tags  
- aligned 3D+channel volumetric representation  

This enables robots, digital twins, and operators to transmit **entire datasets** in one CIVD capsule.

---

## 2. File Table Overview

A CIVD v0.4 file contains:

1. **Header (v0.3)**  
2. **File Table Block (new)**  
3. **Concatenated File Payload Block**  
4. **Dense 3D Volume Block (same as v0.3)**  
5. **Footer (CRC)**

---

## 3. File Table Structure

### Binary Layout (little-endian)

| Field | Type | Description |
|-------|------|-------------|
| file_count | uint32 | Number of embedded files |
| table_reserved | uint32 | Reserved for future use |
| entries[...] | repeated struct | File entries |

### File Entry Struct

Each entry:

| Field | Type | Description |
|-------|------|-------------|
| name_len | uint16 | Length of file name |
| name | bytes[name_len] | UTF‑8 file name |
| mime | uint16 | MIME code (see section 4) |
| offset | uint32 | Byte offset into payload block |
| size | uint32 | Byte length of the file |
| flags | uint16 | Compression, encryption, semantic tags |
| checksum | uint32 | Per-file CRC32 |

---

## 4. MIME Type Codes (initial set)

| Code | Meaning |
|------|---------|
| 1 | binary/unknown |
| 10 | text/plain |
| 20 | image/jpeg |
| 21 | image/png |
| 30 | audio/mp3 |
| 40 | video/mp4 |
| 50 | application/json |
| 60 | application/cad |
| 70 | application/robot-config |

---

## 5. Flags

`flags` bitmask:

| Bit | Meaning |
|-----|---------|
| 0x01 | file compressed (LZ4) |
| 0x02 | file encrypted |
| 0x04 | semantic label present |
| 0x08 | high‑priority tag |

---

## 6. Payload Block

After the file table, all files are concatenated in raw binary order.

The `offset` points into this block.

---

## 7. 3D Volume Block

Same as CIVD v0.3:

- dims (X,Y,Z)
- channels (payload, semantic, integrity, aux)

Payload channel (0) is filled with serialized bytes of entire multi-file payload.

Higher channels can store:

- semantic maps  
- priority fields  
- integrity distributions  

---

## 8. Example

Suppose we embed:

- map.png (32 KB)  
- robot_state.json (2 KB)  
- audio_alert.mp3 (120 KB)

The file table records:

- file_count = 3  
- offsets: 0, 32768, 34816  
- sizes: 32768, 2048, 122880  
- checksums computed individually  

These get packed into the CIVD volume as one unified volumetric data capsule.

---

## 9. Benefits

- Multi-file capsule  
- Instant robot integration  
- Operator-friendly file browsing  
- Eliminates ZIP/tar wrappers  
- Cleaner metadata layer for robotics AI systems  

---

## 10. v0.4 Implementation Roadmap

1. Build encoder for file-table construction  
2. Build decoder that reconstructs the file list  
3. Add MIME registry + flags logic  
4. Integrate into visualization UI  
5. Add semantic-channel support (v0.4b)  

---

