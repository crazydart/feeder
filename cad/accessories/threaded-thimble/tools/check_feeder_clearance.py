# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "manifold3d==3.3.2", "networkx==3.5"]
# ///
"""Check added arm material against the saved 8 mm feeder assembly meshes.

Generate the reference manifest with gridfinity-8mm-holder/tools/export_feeder.py.
The original attachment geometry is separately verified by check_integrated_arm.py.
"""
import hashlib
import json
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile
import numpy as np
import trimesh
from build import INTEGRATED_ARM
from check_geometry import common, volume

HERE = Path(__file__).resolve().parents[1]


def main():
    reference = HERE.parent / "gridfinity-8mm-holder/generated/reference"
    manifest = reference / "manifest.json"
    if not manifest.exists():
        raise RuntimeError("Run uv run ../gridfinity-8mm-holder/tools/export_feeder.py first")
    assembly = HERE.parents[1] / "assembly-8.FCStd"
    with ZipFile(assembly) as archive:
        xml = ET.fromstring(archive.read("Document.xml"))
        p = xml.find("./ObjectData/Object[@name='Body012']/Properties/"
                     "Property[@name='Placement']/PropertyPlacement").attrib
    transform = trimesh.transformations.quaternion_matrix(
        [float(p[k]) for k in ["Q3","Q0","Q1","Q2"]])
    transform[:3,3] = [float(p[k]) for k in ["Px","Py","Pz"]]
    inverse = np.linalg.inv(transform)
    geometry = json.loads((HERE/"generated/integrated-geometry-check.json").read_text())
    assert geometry["prototype"] == "04"
    arm_path = HERE/"stl"/INTEGRATED_ARM
    assert hashlib.sha256(arm_path.read_bytes()).hexdigest() == geometry["arm_sha256"]
    arm = trimesh.load_mesh(arm_path)
    arm.apply_translation([0,0,geometry["parameters"]["arm_back_z"]])
    original = trimesh.load_mesh(HERE/"reference/spool-arm.stl")
    added = trimesh.boolean.difference([arm,original],engine="manifold")
    results = []
    for entry in json.loads(manifest.read_text())["parts"]:
        if entry["source"] in ["FDM/thimble.FCStd","FDM/spool-holder.FCStd","REF/spool.FCStd"]:
            continue
        mesh = trimesh.load_mesh(reference/entry["file"])
        mesh.apply_transform(inverse)
        separated = bool(np.any(mesh.bounds[0] >= added.bounds[1]) or
                         np.any(added.bounds[0] >= mesh.bounds[1]))
        if separated:
            overlap, method = 0., "separated bounding boxes"
        else:
            assert mesh.is_volume, f"Need closed reference mesh: {entry['label']}"
            overlap, method = volume(common(added,mesh)), "solid intersection"
            assert overlap < .001, (entry["label"],overlap)
        results.append({"label":entry["label"],"source":entry["source"],
                        "method":method,"added_material_overlap_mm3":overlap})
    report = {"assembly":"cad/assembly-8.FCStd",
              "assembly_sha256":hashlib.sha256(assembly.read_bytes()).hexdigest(),
              "arm_sha256":geometry["arm_sha256"], "parts_checked":len(results),
              "parts":results,
              "scope":"Saved assembly position; added material only. Does not test moving parts over their full travel or loaded deflection."}
    (HERE/"generated/feeder-clearance-prototype-04.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"No added-material collisions across {len(results)} feeder assembly meshes.")
    print(f"{sum(r['method']=='solid intersection' for r in results)} nearby meshes checked by solid intersection.")


if __name__ == "__main__":
    main()
