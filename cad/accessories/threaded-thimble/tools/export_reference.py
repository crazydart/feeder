# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["cadquery-ocp==7.9.3.1.1", "trimesh==5.1.1", "networkx==3.5"]
# ///
"""Export saved upstream geometry without changing or recomputing FreeCAD files."""
from io import BytesIO
from pathlib import Path
import sys
import numpy as np
import trimesh
from OCP.BRep import BRep_Builder
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Shape
from OCP.gp import gp_Pnt

HERE = Path(__file__).resolve().parents[1]
CAD = HERE.parents[1]
sys.path.insert(0, str(HERE.parent / "gridfinity-8mm-holder/tools"))
from export_feeder import document, resolve, placement


def shape(path, member):
    z, _ = document(path)
    s = TopoDS_Shape()
    BRepTools.Read_s(s, BytesIO(z.read(member)), BRep_Builder())
    return s


def write(s, path, transform=np.eye(4)):
    BRepMesh_IncrementalMesh(s, 0.015, False, 0.06, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    assert writer.Write(s, str(path))
    m = trimesh.load_mesh(path)
    m.apply_transform(transform)
    path.write_bytes(m.export(file_type="stl"))
    print(path.name, "bounds", m.bounds.round(4).tolist(), "watertight", m.is_watertight)


def main():
    out = HERE / "generated"
    out.mkdir(exist_ok=True)
    original = shape(CAD / "FDM/thimble.FCStd", "Body.Shape.brp")
    write(original, out / "original-thimble.stl")
    # Exact key AND the upper shoulder that captures the spool arm.
    box = BRepPrimAPI_MakeBox(gp_Pnt(-15, -15, -3), 30, 30, 3.6).Shape()
    key = BRepAlgoAPI_Common(original, box).Shape()
    write(key, HERE / "reference/quarter-turn-mount.stl")
    assembly = CAD / "assembly-8.FCStd"
    _, objects = document(assembly)
    inverse_thimble = np.linalg.inv(placement(objects["Body012"]))
    for obj in objects:
        if obj == "Assembly":
            continue
        for path, label, member, matrix in resolve(assembly, obj):
            if path.name == "spool-holder.FCStd":
                write(shape(path, member), out / "spool-arm.stl", inverse_thimble @ matrix)
                (HERE / "reference/spool-arm.stl").write_bytes((out / "spool-arm.stl").read_bytes())
                return
    raise RuntimeError("Spool arm missing from assembly")


if __name__ == "__main__":
    main()
