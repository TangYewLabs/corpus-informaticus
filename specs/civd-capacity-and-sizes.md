\# CIVD Capacity, Sizes, and Compression Strategy



This document defines the practical and theoretical limits for CIVD corpus files, and clarifies why the core format is intentionally \*\*uncompressed\*\* in v0.3–v1.0.



---



\## 1. Hard Capacity Limits (Spec-Level)



CIVD uses a 32-bit unsigned integer field (`orig\_length`) to record the original payload length in bytes.



\- Type: `uint32`

\- Maximum value: 4,294,967,295 (≈ 4 GiB)



Therefore:



\- \*\*Theoretical hard maximum payload per `.civd` file:\*\* ~4 GiB

\- Actual file size on disk: header + payload + footer, which for large corpora is effectively ~payload size.



This matches many common container formats (e.g., legacy file types that cap at 4 GiB due to 32-bit length fields).



The spec does \*\*not\*\* enforce a smaller limit; it defines \*\*4 GiB\*\* as the absolute maximum.



---



\## 2. Recommended Operational Sizes (Real-World Usage)



Although the format can represent up to ~4 GiB of payload, real robotics / AI / simulation systems should stay well below that for performance, latency, and reliability.



CIVD defines \*\*non-binding size profiles\*\* for guidance:



\### 2.1 CIVD-S (Small)



\- Target: \*\*≤ 1 MiB\*\*

\- Use cases:

&nbsp; - Embedded robots

&nbsp; - Tiny sensor fusion snapshots

&nbsp; - Micro-maps and local occupancy grids

&nbsp; - Quick diagnostic corpora



\### 2.2 CIVD-M (Medium)



\- Target: \*\*1–16 MiB\*\*

\- Use cases:

&nbsp; - Typical robot state snapshots

&nbsp; - Single-frame perception + occupancy + basic semantic overlays

&nbsp; - Normal simulation frames with moderate resolution



This is expected to be the \*\*most common profile\*\* for real-time robotics and AI pipelines.



\### 2.3 CIVD-L (Large)



\- Target: \*\*16–64 MiB\*\*

\- Use cases:

&nbsp; - Dense 3D environment chunks

&nbsp; - Warehouse / factory floor segments

&nbsp; - High-resolution slices for training datasets

&nbsp; - Volumetric snapshots for analysis and replay



\### 2.4 CIVD-XL (Extra Large)



\- Target: \*\*64–512 MiB\*\*

\- Use cases:

&nbsp; - Offline processing

&nbsp; - Archival corpora

&nbsp; - Heavy research scenes

&nbsp; - Non-real-time systems with relaxed latency / bandwidth constraints



Anything beyond ~64 MiB should be treated as \*\*exceptional\*\* and carefully justified. For very large scenes, users are encouraged to \*\*tile or sequence\*\* multiple corpora rather than creating one extremely large file.



---



\## 3. Tiling and Sequencing (Scaling Beyond Single-File Limits)



To represent very large spaces or long sequences, CIVD is designed to work with:



\- \*\*Spatial tiling\*\*:

&nbsp; - Break the world into multiple volumes (e.g., grid of chunks).

&nbsp; - Example: `world\_x0\_y0\_z0.civd`, `world\_x1\_y0\_z0.civd`, etc.

\- \*\*Temporal sequencing\*\*:

&nbsp; - Sequence files over time (e.g., one corpus per timestep or keyframe).

&nbsp; - Example: `scene\_t0001.civd`, `scene\_t0002.civd`, etc.



These strategies:



\- Keep individual files within the S/M/L profiles.

\- Enable efficient loading / streaming.

\- Avoid huge monolithic corpora that are hard to transfer, inspect, and debug.



Future CIVD specs (v0.4+) may formalize tiling and linking conventions, but even in v0.3, these patterns are recommended.



---



\## 4. Compression Strategy (v0.3–v1.0)



\### 4.1 Intentional Design: Core CIVD Is Uncompressed



In CIVD v0.3–v1.0, the \*\*core format is intentionally uncompressed\*\*:



\- The payload is a \*\*contiguous voxel buffer\*\*:

&nbsp; - easy to map to NumPy / PyTorch tensors

&nbsp; - friendly to `memmap` and zero-copy workflows

&nbsp; - straightforward to debug and inspect

\- No per-block or internal compression is specified in the base format.



This preserves the key properties that motivated CIVD:



\- Fast, predictable access to voxel data

\- Simple implementations in multiple languages

\- Direct alignment with tensor-based AI frameworks

\- Clarity and reliability for robotics and simulation pipelines



\### 4.2 External Compression Is Allowed and Encouraged



While CIVD does not define internal compression, \*\*external compression\*\* is fully compatible and often desirable:



Examples:



\- `snapshot.civd.gz`   (gzip)

\- `scene.civd.zst`     (zstd)

\- `world\_chunk.civd.lz4` (lz4)



Consumers may:



1\. Decompress using standard tools.

2\. Then parse the resulting `.civd` file as usual.



This approach:



\- Reuses mature, battle-tested compression libraries.

\- Avoids complicating the CIVD spec.

\- Keeps the core format clean and implementation-friendly.



\### 4.3 Future Direction: CIVD-C (Compressed Profiles)



If practical deployments reveal that storage and bandwidth are dominant constraints, future versions may introduce optional \*\*CIVD-C\*\* profiles, such as:



\- Block-wise compression (e.g., per Z-slice or tile)

\- Sparse voxel compression schemes

\- Learned / model-based compression for specific domains



These would be defined as \*\*extensions or sibling profiles\*\*, not as a breaking change to the base CIVD format. For v0.3–v1.0, the official stance remains:



> CIVD is uncompressed by design. Compress the container externally if needed.



---



\## 5. Summary



\- \*\*Hard maximum payload per `.civd` file:\*\* ~4 GiB (uint32 `orig\_length`).

\- \*\*Recommended operational sizes for real-time systems:\*\* aim for \*\*≤ 16–64 MiB\*\*, with \*\*1–16 MiB\*\* as the primary target band.

\- For very large scenes or long sequences:

&nbsp; - Use \*\*tiling\*\* (multiple CIVD corpora for spatial regions).

&nbsp; - Use \*\*sequencing\*\* (multiple corpora over time).

\- CIVD v0.3–v1.0 is \*\*intentionally uncompressed\*\* to preserve simplicity, tensor-friendliness, and robustness.

\- External compression (`.civd.gz`, `.civd.zst`, etc.) is supported and recommended when needed.

\- Internal compression is reserved for potential future CIVD-C profiles, based on real-world demand.



