"""Export current arm and cap; --legacy rebuilds the old detachable thimble."""
import argparse
import struct
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PARTS = {
    "thimble": "threaded-thimble-prototype-01.stl",
    "screw": "reel-retaining-screw-30mm-prototype-01.stl",
}
INTEGRATED_ARM = "spool-arm-integrated-thimble-plus2mm-prototype-02.stl"


def discard_zero_area_triangles(path):
    """Remove only exactly collapsed facets from float32 STL export.

    Clipping the imported arm's bottom plane can create duplicate-vertex
    triangles after float32 rounding. No vertices or nonzero faces change.
    """
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    assert len(data) == 84 + count*50
    kept = []
    for index in range(count):
        record = data[84+50*index:84+50*(index+1)]
        v = struct.unpack("<12fH", record)[3:12]
        a = [v[i+3]-v[i] for i in range(3)]
        b = [v[i+6]-v[i] for i in range(3)]
        cross = (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])
        if cross != (0.,0.,0.):
            kept.append(record)
    if len(kept) != count:
        path.write_bytes(data[:80]+struct.pack("<I",len(kept))+b"".join(kept))
        print(f"{path.name}: removed {count-len(kept)} exactly zero-area export facets")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--legacy", action="store_true")
    args = parser.parse_args()
    (HERE / "stl").mkdir(exist_ok=True)
    exports = [(part, filename, "thimble.scad") for part, filename in PARTS.items()] if args.legacy else [
        ("arm", INTEGRATED_ARM, "integrated-arm.scad"),
        ("screw", PARTS["screw"], "thimble.scad"),
    ]
    for part, filename, source in exports:
        subprocess.run(["openscad", "--backend", "Manifold", "--export-format", "binstl",
                        "-D", f'part="{part}"', "-o", str(HERE / "stl" / filename),
                        str(HERE / source)], check=True)
        discard_zero_area_triangles(HERE / "stl" / filename)
