# CIVD v0.3 — Dynamic Dimensions and Channels

This document defines CIVD v0.3, which extends the original fixed-geometry corpus into a **dynamic volumetric container** with configurable dimensions and channel count.

The goals of v0.3 are:

- Remove the hard-coded 16×16×16, 1-channel limitation.
- Allow arbitrary (but bounded) volume sizes and channels.
- Maintain backward compatibility with existing files and tools.
- Keep the layout simple and tensor-friendly.

CIVD v0.3 — Dynamic Dimensions and Channels

This document defines CIVD v0.3, which extends the original fixed-geometry corpus into a dynamic volumetric container with configurable dimensions and channel count.

The goals of v0.3 are:

Remove the hard-coded 16×16×16, 1-channel limitation.

Allow arbitrary (but bounded) volume sizes and channels.

Maintain backward compatibility with existing files and tools.

Keep the layout simple and tensor-friendly.

1. v0.3 Header Specification

CIVD v0.3 replaces the fixed-size header with a dimension-aware structure.

All integers are little-endian.

Offset	Size	Field	Description
0	4	Magic (CIVD)	File signature
4	2	Version	0x0003
6	2	Header size	Bytes in the header (for forward compatibility)
8	4	X dimension	Width
12	4	Y dimension	Height
16	4	Z dimension	Depth
20	4	Channels	Number of channels per voxel
24	8	Payload bytes	Exact number of payload bytes stored
32	8	Reserved A	Future index / timecode / slices
40	8	Reserved B	Future integrity block pointer
48	4	CRC32	Integrity over entire voxel block
52	…	START OF VOXELS	Raw channel-major volume data
Header size = 52 bytes

The spec allows future versions to append extended metadata past byte 52.

2. Volume Layout (v0.3)

The payload volume is stored as:

[channel][z][y][x]


This is channel-major, making it compatible with:

PyTorch

NumPy

ROS message arrays

TensorRT / ONNX

NVIDIA Omniverse tensor ingestion

Why channel-major?

Because robotics and vision pipelines expect:

C × D × H × W


And CIVD is designed to be “AI-native, robotics-native, tensor-native.”

3. Capacity Rules

The maximum payload is:

capacity = X * Y * Z * Channels


Examples:

Geometry	Channels	Capacity
16×16×16	1	4096 bytes
32×32×32	4	131,072 bytes
128×128×128	8	16,777,216 bytes (16 MB)
256×256×256	16	268 MB
v0.3 Recommended practical cap for now: 128³ × 4 channels (8 MB)

This balances performance with capability during early adoption.

4. Backward Compatibility (v0.1 and v0.2)

v0.3 can decode older files:

v0.1 signature:
MAGIC = "CI3\x00"
VERSION = 0x0001
CHANNELS = 1
DIMS = 16×16×16

v0.2 signature:
MAGIC = "CI3\x00"
VERSION = 0x0002
CHANNELS = 4
DIMS = 16×16×16

How v0.3 handles them:

If magic = CI3\x00 → treat as legacy CI formats

Auto-upgrade to CIVD internal structure

Preserve byte-for-byte payload

Expose v0.3-style numpy tensors to the user

This keeps older files readable forever.

5. Future Extension Points

These are reserved fields that will be defined in the next versions:

Reserved A – Timecode / Volume Arrays

Multi-volume sequences

4D and 5D corpus (spatial + temporal + channels)

Reserved B – Integrity Mesh

Per-voxel anomaly scores

Per-slice health maps

Geometry-aware checksums

Extended Metadata Block

Semantic dictionaries

Object masks

Sensor descriptors

Provenance / lineage (for AI pipelines)

6. Summary

CIVD v0.3 introduces:

Dynamic volume geometry (X/Y/Z)

Dynamic channel count

AI-native tensor ordering (C × Z × Y × X)

Larger payloads (MB-scale instead of 4KB)

Forward-compatible header

Full backward compatibility

It is the first step toward a volumetric data standard for robotics, AI memory systems, and 3D-aware simulation pipelines.