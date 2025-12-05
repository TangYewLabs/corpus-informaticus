# CIVD v0.3 — Encoding and Decoding Rules

This document defines the encoding and decoding process for CIVD v0.3.

## 1. Overview
CIVD v0.3 supports dynamic volume dimensions and multiple channels. This document describes how raw user payloads are transformed into CIVD volumetric tensors and serialized into `.civd` files.

## 2. Terminology
- **Volume**: 3D grid defined by (X, Y, Z).
- **Voxel**: Single cell in the 3D grid.
- **Channels**: Independent byte streams per voxel.
- **Corpus**: The entire CIVD file structure.

## 3. File Layout Summary
HEADER (static-size metadata)
VOLUME PAYLOAD (X * Y * Z * C bytes)
CRC32 FOOTER (4 bytes)

## 4. Encoding Steps
1. Validate payload size against capacity.
2. Initialize a zero-filled volume.
3. Write payload data into channel[0] sequentially.
4. Initialize other channels to zero unless user opts to fill them.
5. Compute CRC32 over the raw volume.
6. Serialize header + volume + crc.

## 5. Decoding Steps
1. Parse header and validate version & geometry.
2. Read volume bytes.
3. Verify CRC32.
4. Extract payload bytes from channel[0].
5. Return payload and volume metadata.

## 6. Error Conditions
- Payload exceeds capacity.
- Mismatched CRC32.
- Invalid header magic or version.
- Unexpected EOF during reading.

## 7. Reference Implementation
Will be maintained inside `src/corpus_informaticus/codec_v03.py` in a later update.

