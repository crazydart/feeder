# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "networkx==3.5"]
# ///
"""Export the shared 16/24 mm print STL; discard collapsed triangles."""
from pathlib import Path
import subprocess
import numpy as np
import trimesh

HERE=Path(__file__).resolve().parents[1]
(HERE/"generated").mkdir(exist_ok=True)
(HERE/"stl").mkdir(exist_ok=True)
target=HERE/"generated/holder.stl"
subprocess.run(["openscad","--export-format","binstl",
                "-o",str(target),str(HERE/"holder.scad")],check=True)
mesh=trimesh.load_mesh(target)
# Coincident cut boundaries can export collapsed triangles. Removing only
# zero-area triangles leaves the CAD surface and all dimensions unchanged.
valid=mesh.nondegenerate_faces(height=1e-8)
removed=int((~valid).sum())
mesh.update_faces(valid)
mesh.remove_unreferenced_vertices()
assert mesh.is_volume and len(mesh.split())==1
assert np.allclose(mesh.extents,[209.5,167.5,85],atol=.001)
assert abs(mesh.bounds[0,2])<1e-6
data=mesh.export(file_type="stl")
target.write_bytes(data)
print_file=HERE/"stl/gridfinity-16-24mm-holder-4-slot-prototype-02.stl"
print_file.write_bytes(data)
print(f"{print_file.name}: {len(mesh.faces)} faces; removed {removed} collapsed triangles",flush=True)
