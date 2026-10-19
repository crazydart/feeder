# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["cadquery-ocp==7.9.3.1.1", "trimesh==5.1.1", "networkx==3.5"]
# ///
"""Read saved FreeCAD BReps and assembly placements for reference rendering.

Does not recompute or change the source CAD. Run with `uv run`.
"""
from io import BytesIO
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile

import numpy as np
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Shape
import trimesh

HERE = Path(__file__).resolve().parents[1]
CAD = HERE.parents[1]
OUT = HERE / "generated/reference"
CACHE = {}


def document(path):
    path = path.resolve()
    if path not in CACHE:
        z = ZipFile(path)
        root = ET.fromstring(z.read("Document.xml"))
        CACHE[path] = (z, {o.get("name"): o for o in root.findall("./ObjectData/Object")})
    return CACHE[path]


def prop(obj, name):
    return obj.find(f'./Properties/Property[@name="{name}"]')


def placement(obj):
    p = prop(obj, "Placement")
    m = np.eye(4)
    if p is not None:
        a = p.find("PropertyPlacement").attrib
        # FreeCAD saves quaternion xyzw; trimesh expects wxyz.
        m = trimesh.transformations.quaternion_matrix([float(a[k]) for k in ["Q3", "Q0", "Q1", "Q2"]])
        m[:3, 3] = [float(a[k]) for k in ["Px", "Py", "Pz"]]
    return m


def resolve(path, name, parent=np.eye(4)):
    z, objects = document(path)
    obj = objects[name]
    label = prop(obj, "Label").find("String").get("value")
    link = prop(obj, "LinkedObject")
    if link is not None:
        link = link.find("XLink")
        if not link.get("name"):
            return []
        target = path.parent / link.get("file") if link.get("file") else path
        _, targets = document(target)
        p = placement(obj) @ np.linalg.inv(placement(targets[link.get("name")]))
        return resolve(target, link.get("name"), parent @ p)
    shape = prop(obj, "Shape")
    if shape is not None:
        shape = shape.find("Part")
        return [(path, label, shape.get("file"), parent)]
    group = prop(obj, "Group")
    if group is not None:
        result = []
        for child in group.findall("./LinkList/Link"):
            result += resolve(path, child.get("value"), parent @ placement(obj))
        return result
    return []


def material(top, child):
    if "mobo" in top or "Board" in top or "diffusion" in top:
        if "Pads" in child: return "gold"
        if "Tracks" in child or "Zones" in child: return "pcb_dark"
        if "Pcb" in child or "PCB" in child or "board" in child.lower(): return "pcb"
        if "diffus" in top: return "ivory"
        return "component"
    if "release-lever" in top: return "yellow"
    if "worm" in top or "peel-gear" in top and "frame" not in top: return "ivory"
    if any(x in top.lower() for x in ["screw", "spring", "collar", "wheel"]): return "metal"
    if "motor" in top and not any(x in top for x in ["cover", "bracket"]): return "metal"
    if "n20" in top: return "metal"
    return "black"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    assembly = CAD / "assembly-8.FCStd"
    _, objects = document(assembly)
    members = prop(objects["Assembly"], "Group").findall("./LinkList/Link")
    manifest, skipped = [], []
    for member in members:
        name = member.get("value")
        if name == "Joints": continue
        label = prop(objects[name], "Label").find("String").get("value")
        sources = resolve(assembly, name)
        if not sources:
            skipped.append({"object": name, "label": label, "reason": "no saved resolvable geometry"})
        for path, child, member, matrix in sources:
            z, _ = document(path)
            shape = TopoDS_Shape()
            BRepTools.Read_s(shape, BytesIO(z.read(member)), BRep_Builder())
            if shape.IsNull(): continue
            BRepMesh_IncrementalMesh(shape, 0.10, False, 0.15, True)
            target = OUT / f"{len(manifest):03d}.stl"
            writer = StlAPI_Writer()
            writer.ASCIIMode = False
            if not writer.Write(shape, str(target)):
                continue  # Construction wires and coordinate systems have no faces.
            mesh = trimesh.load_mesh(target)
            mesh.apply_transform(matrix)
            target.write_bytes(mesh.export(file_type="stl"))
            manifest.append({"file": target.name, "label": label, "part": child,
                             "material": material(label, child), "bounds": mesh.bounds.tolist(),
                             "source": str(path.relative_to(CAD)), "member": member})
        group_bounds = [x["bounds"] for x in manifest if x["label"] == label]
        if group_bounds:
            b = np.array(group_bounds)
            print(label, np.round([b[:,0].min(axis=0), b[:,1].max(axis=0)],2).tolist(), flush=True)
    (OUT / "manifest.json").write_text(json.dumps({"parts": manifest, "skipped": skipped}, indent=2) + "\n")
    print(f"Exported {len(manifest)} meshes; skipped: {skipped}")


if __name__ == "__main__": main()
