import math
import sys
from pathlib import Path

from corpus_informaticus.codec_v03 import encode_v03


def choose_cube_dims(length: int) -> int:
    """
    Choose a simple cubic dimension n such that n^3 >= length.
    Minimum n is 4 to avoid degenerate tiny volumes.
    """
    if length <= 0:
        return 4
    n = int(math.ceil(length ** (1.0 / 3.0)))
    return max(n, 4)


def main():
    if len(sys.argv) < 2:
        print("Usage: python file_to_civd_v03.py <input_file> [channels]")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.is_file():
        print(f"Input file not found: {input_path}")
        sys.exit(1)

    channels = 4
    if len(sys.argv) >= 3:
        try:
            channels = int(sys.argv[2])
        except ValueError:
            print(f"Invalid channels value: {sys.argv[2]}")
            sys.exit(1)

    data = input_path.read_bytes()
    length = len(data)

    # Choose a simple cube so that X=Y=Z
    n = choose_cube_dims(length)
    dims = (n, n, n)

    print(f"Encoding '{input_path}' ({length} bytes)")
    print(f"Chosen dims: {dims}, channels: {channels}")
    capacity = dims[0] * dims[1] * dims[2]
    print(f"Channel 0 capacity: {capacity} bytes")

    blob = encode_v03(data, dims, channels)

    output_path = input_path.with_suffix(input_path.suffix + ".civd")
    output_path.write_bytes(blob)

    print("Encoded into CIVD v0.3 corpus:")
    print(f"  {output_path}")


if __name__ == "__main__":
    main()
