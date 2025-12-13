import tempfile
import numpy as np

from corpus_informaticus.snapshot_v08 import write_snapshot_v08, read_snapshot_v08, read_roi_from_snapshot_v08
from corpus_informaticus.roi_v06 import VolumeSpecV06

def test_snapshot_v08_roundtrip():
    dims = (16, 12, 8)  # (x,y,z)
    channels = 3
    spec = VolumeSpecV06(dims=dims, channels=channels, dtype="uint8", order="C", signature="C_CONTIG")

    vol = np.zeros((dims[2], dims[1], dims[0], channels), dtype=np.uint8)
    vol[..., 0] = 11
    vol[..., 1] = 22
    vol[..., 2] = 33
    buf = vol.tobytes(order="C")

    with tempfile.TemporaryDirectory() as td:
        path = f"{td}/snap_v08.civd"
        write_snapshot_v08(path, buf, spec, meta={"mission": "v08_test"}, schema_version="0.8")

        header, spec2, payload = read_snapshot_v08(path)
        assert header.schema_version == "0.8"
        assert spec2.dims == dims
        assert payload == buf

        roi = read_roi_from_snapshot_v08(path, x=2, y=3, z=1, w=4, h=5, d=2)
        assert roi.shape == (2, 5, 4, channels)
        assert int(roi[..., 0].mean()) == 11

if __name__ == "__main__":
    test_snapshot_v08_roundtrip()
    print("test_snapshot_v08_roundtrip: OK")
