# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "networkx==3.5"]
# ///
"""Export the five-slot print STL and verify its mesh and dimensions."""
from pathlib import Path
import subprocess
import numpy as np
import trimesh
from model_parameters import parameters

HERE = Path(__file__).resolve().parents[1]
PARAMS = parameters()
(HERE / "generated").mkdir(exist_ok=True)
(HERE / "stl").mkdir(exist_ok=True)
target = HERE / "generated/holder.stl"
subprocess.run(["openscad", "--export-format", "binstl", "-o", str(target),
                str(HERE / "holder.scad")], check=True)
mesh = trimesh.load_mesh(target)
# Remove only collapsed triangles created at coincident cut boundaries.
valid = mesh.nondegenerate_faces(height=1e-8)
removed = int((~valid).sum())
mesh.update_faces(valid)
mesh.remove_unreferenced_vertices()
assert mesh.is_volume and len(mesh.split()) == 1
assert np.allclose(mesh.extents, [PARAMS[k] for k in ["length", "width", "height"]], atol=.001)
assert abs(mesh.bounds[0, 2]) < 1e-6
data = mesh.export(file_type="stl")
target.write_bytes(data)
print_file = HERE / "stl/gridfinity-8mm-holder-5-slot-reel-clearance-prototype-06.stl"
print_file.write_bytes(data)
print(f"{print_file.name}: {len(mesh.faces)} faces; removed {removed} collapsed triangles")
subprocess.run(["openscad", "-D", 'render_part="reel_reference"',
                "--export-format", "binstl", "-o",
                str(HERE / "generated/reel-reference.stl"),
                str(HERE / "holder.scad")], check=True)
