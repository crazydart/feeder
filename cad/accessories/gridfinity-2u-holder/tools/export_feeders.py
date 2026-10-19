# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["cadquery-ocp==7.9.3.1.1", "trimesh==5.1.1", "networkx==3.5"]
# ///
"""Export pinned upstream 2u CAD as placed reference meshes, without recomputing.

Usage: uv run --python 3.11 tools/export_feeders.py /path/to/opulo-feeder-repo
The source repository must contain COMMIT. No checkout or source files change.
"""
from io import BytesIO
import json
from pathlib import Path
import posixpath
import subprocess
import sys
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import numpy as np
import trimesh
from OCP.BRep import BRep_Builder
from OCP.BRepTools import BRepTools
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.TopoDS import TopoDS_Shape
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_FACE

HERE = Path(__file__).resolve().parents[1]
COMMIT = "e96d03cb3d28bcb62ed9e09e28752d2cbe735102"
REPO = Path(sys.argv[1]).resolve()
CACHE = {}
ALIASES = {
    "cad/FDM/peel-gear-bottom-2u.FCStd": "cad/FDM/peel-gear-2u-bottom.FCStd",
    "cad/FDM/peel-gear-top-2u.FCStd": "cad/FDM/peel-gear-2u-top.FCStd",
}
repairs = []

def document(path):
    if path not in CACHE:
        p = subprocess.run(["git", "show", COMMIT+":"+path], cwd=REPO, capture_output=True)
        if p.returncode: raise FileNotFoundError(path)
        z = ZipFile(BytesIO(p.stdout))
        root = ET.fromstring(z.read("Document.xml"))
        CACHE[path] = z, {o.get("name"):o for o in root.findall("./ObjectData/Object")}
    return CACHE[path]

def prop(obj, name): return obj.find(f'./Properties/Property[@name="{name}"]')

def placement(obj):
    p = prop(obj, "Placement")
    m = np.eye(4)
    if p is not None:
        a = p.find("PropertyPlacement").attrib
        m = trimesh.transformations.quaternion_matrix([float(a[k]) for k in ["Q3","Q0","Q1","Q2"]])
        m[:3,3] = [float(a[k]) for k in ["Px","Py","Pz"]]
    return m

def resolve(path, name, parent=np.eye(4)):
    z, objects = document(path)
    obj = objects[name]
    label = prop(obj,"Label").find("String").get("value")
    # FreeCAD origins contain infinite axes/planes, not physical part geometry.
    if name.startswith(("Origin", "X_Axis", "Y_Axis", "Z_Axis", "XY_Plane", "XZ_Plane", "YZ_Plane")):
        return []
    link = prop(obj,"LinkedObject")
    if link is not None:
        link = link.find("XLink")
        if not link.get("name"): return []
        target = posixpath.normpath(posixpath.join(posixpath.dirname(path),link.get("file"))) if link.get("file") else path
        if target in ALIASES:
            repairs.append({"old":target,"resolved":ALIASES[target],"reason":"Assembly references obsolete gear filename; retain saved assembly placement."})
            target = ALIASES[target]
        _, targets = document(target)
        matrix = parent @ placement(obj) @ np.linalg.inv(placement(targets[link.get("name")]))
        return resolve(target,link.get("name"),matrix)
    shape = prop(obj,"Shape")
    if shape is not None: return [(path,label,name,shape.find("Part").get("file"),parent)]
    group = prop(obj,"Group")
    out = []
    if group is not None:
        for child in group.findall("./LinkList/Link"):
            out += resolve(path,child.get("value"),parent @ placement(obj))
    return out

def material(path, child):
    if "/pcb/" in "/"+path or "/PCA/" in path:
        if "Pads" in child: return "gold"
        if "Tracks" in child or "Zones" in child: return "pcb_dark"
        if "Pcb" in child or "PCB" in child or "board" in child.lower(): return "pcb"
        return "component"
    if "release-lever" in path: return "yellow"
    if "worm" in path or "peel-gear" in path: return "ivory"
    if "/OTS/" in path: return "metal"
    return "black"

def main():
    for width in [16,24]:
        repairs.clear()
        out = HERE / f"generated/reference-{width}"
        out.mkdir(parents=True,exist_ok=True)
        assembly = f"cad/asm-{width}mm.FCStd"
        _, objects = document(assembly)
        parts, skipped = [], []
        for link in prop(objects["Assembly"],"Group").findall("./LinkList/Link"):
            name = link.get("value")
            if name == "Joints": continue
            try: sources = resolve(assembly,name)
            except FileNotFoundError as e:
                skipped.append({"object":name,"missing_source":str(e)})
                continue
            for path,label,child,member,matrix in sources:
                z,_ = document(path)
                shape = TopoDS_Shape()
                BRepTools.Read_s(shape,BytesIO(z.read(member)),BRep_Builder())
                if shape.IsNull() or not TopExp_Explorer(shape,TopAbs_FACE).More(): continue
                BRepMesh_IncrementalMesh(shape,0.10,False,0.15,True)
                target = out / f"{len(parts):03d}.stl"
                writer = StlAPI_Writer(); writer.ASCIIMode = False
                if not writer.Write(shape,str(target)): continue
                mesh = trimesh.load_mesh(target)
                mesh.apply_transform(matrix)
                assert np.abs(mesh.bounds).max() < 1000, f"Non-physical geometry: {path}:{child}"
                target.write_bytes(mesh.export(file_type="stl"))
                parts.append({"file":target.name,"label":Path(path).stem if "/pcb/" not in "/"+path else "controller-pcb",
                              "part":label,"object":name,"material":material(path,label),
                              "bounds":mesh.bounds.tolist(),"source":path,"member":member})
            b = np.array([p["bounds"] for p in parts if p["object"]==name])
            if len(b): print(width,name,parts[-1]["source"],np.round([b[:,0].min(axis=0),b[:,1].max(axis=0)],2).tolist(),flush=True)
        report = {"upstream":"https://github.com/opulo-inc/feeder","commit":COMMIT,
                  "assembly":assembly,"parts":parts,"skipped":skipped,"resolved_links":list(repairs),
                  "scope":"Saved geometry only. Obsolete duplicate frame/cover links omitted. Motors, fasteners, wiring and motion are not fully represented."}
        (out/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
        print(width,"exported",len(parts),"meshes; omitted",skipped,flush=True)

if __name__ == "__main__": main()
