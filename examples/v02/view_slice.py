# examples/v02/view_slice.py

import os
import sys
import numpy as np

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))
SRC_ROOT = os.path.join(PROJECT_ROOT, "src")
if SRC_ROOT not in sys.path:
    sys.path.insert(0, SRC_ROOT)

from corpus_informaticus.ci3_codec import decode_ci3_v02_file


def main():
    path = os.path.join(CURRENT_DIR, "hello_v02.ci3")
    if not os.path.exists(path):
        print("Run encode_v02.py first.")
        return

    payload, hdr = decode_ci3_v02_file(path)

    dim_x, dim_y, dim_z = hdr.dim_x, hdr.dim_y, hdr.dim_z
    channels = hdr.channels

    volume_size = dim_x * dim_y * dim_z * channels

    # Read raw bytes again (decode gives only payload)
    with open(path, "rb") as f:
        raw = f.read()

    header_size = 24
    footer_size = 4
    volume_bytes = raw[header_size:header_size + volume_size]

    # Interpret as 4-channel voxel grid
    vol = np.frombuffer(volume_bytes, dtype=np.uint8)
    vol = vol.reshape((dim_z, dim_y, dim_x, channels))

    # Show a single Z-slice (z = 0)
    z = 0
    slice_payload = vol[z, :, :, 0]
    slice_integrity = vol[z, :, :, 1]
    slice_semantic = vol[z, :, :, 2]
    slice_aux = vol[z, :, :, 3]

    print("\n=== Z = 0 PAYLOAD CHANNEL ===")
    print(slice_payload)

    print("\n=== Z = 0 INTEGRITY CHANNEL ===")
    print(slice_integrity)

    print("\n=== Z = 0 SEMANTIC CHANNEL ===")
    print(slice_semantic)

    print("\n=== Z = 0 AUX CHANNEL ===")
    print(slice_aux)


if __name__ == "__main__":
    main()
