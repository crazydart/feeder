# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "manifold3d", "networkx==3.5", "rtree"]
# ///
"""Check both saved 2u variants against the holder; no physical/motion validation."""
import json
from pathlib import Path
import warnings
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parents[1]
LANES = [-63,-21,21,63]
PLACEMENT = np.array([15.5,-13.25,69.0])

def first_hits(mesh, xy, z, direction):
    hits, ids, _ = mesh.ray.intersects_location(
        np.column_stack([xy,np.full(len(xy),z)]),
        np.tile([0,0,direction],(len(xy),1)),multiple_hits=True)
    out=[]
    for i in range(len(xy)):
        assert i in ids, f"Ray {i} misses a surface"
        out.append(float(hits[ids==i,2].min() if direction>0 else hits[ids==i,2].max()))
    return np.array(out)

for variant in [16,24]:
    holder = trimesh.load_mesh(HERE/"generated/holder.stl")
    assert holder.is_volume and len(holder.split())==1
    assert np.allclose(holder.extents,[209.5,167.5,85],atol=.001)
    assert abs(holder.bounds[0,2])<1e-6
    elevated=holder.triangles_center[:,2]>.05
    flat=(holder.face_normals[:,2]<-.999999)&elevated
    flat_area=float(holder.area_faces[flat].sum())
    down=(holder.face_normals[:,2]<-1e-6)&elevated
    angle=float(np.degrees(np.arccos(np.clip(-holder.face_normals[down,2],0,1))).min())
    assert flat_area<.001 and angle>=44.99
    ref=HERE/f"generated/reference-{variant}"
    manifest=json.loads((ref/"manifest.json").read_text())
    frame_part=next(p for p in manifest["parts"] if p["label"]==f"frame-{variant}")
    frame=trimesh.load_mesh(ref/frame_part["file"])
    frame.apply_translation(PLACEMENT+[0,-21,0])
    samples=[]
    for label,xs,ys in [("front",[-60,-55,-50],[6,15,25]),("rear",[44,52,63],[7,16,25])]:
        source_xy=np.array([[x,y] for x in xs for y in ys])
        xy=source_xy+PLACEMENT[:2]+[0,-21]
        frame_z=first_hits(frame,xy,-100,1)
        support_z=first_hits(holder,xy,150,-1)
        gaps=frame_z-support_z
        assert np.max(np.abs(gaps))<.02, (variant,label,gaps)
        samples.append({"seat":label,"samples":len(xy),"maximum_absolute_gap_mm":float(np.max(np.abs(gaps)))})
    # Centerline intersections have the widest roofs in the vaulted base.
    xy=np.array([[x,y] for x in [-63,-21,21,63] for y in [-42,0,42]])
    roof=first_hits(holder,xy,-1,1)
    skin=9-roof
    assert skin.min()>2
    checked=[];skipped=[];collisions=[]
    for p in manifest["parts"]:
        mesh=trimesh.load_mesh(ref/p["file"])
        mesh.update_faces(mesh.nondegenerate_faces());mesh.remove_unreferenced_vertices()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",RuntimeWarning)
            valid=mesh.is_volume
        if not valid:
            skipped.append({"label":p["label"],"part":p["part"]})
            continue
        checked.append({"label":p["label"],"part":p["part"]})
        for lane in LANES:
            placed=mesh.copy();placed.apply_translation(PLACEMENT+[0,lane,0])
            if (placed.bounds[0]>=holder.bounds[1]).any() or (placed.bounds[1]<=holder.bounds[0]).any():continue
            common=trimesh.boolean.intersection([holder,placed],engine="manifold")
            if len(common.faces) and common.volume>.01:
                collisions.append({"label":p["label"],"part":p["part"],"lane":lane,"volume_mm3":float(common.volume)})
    lever=next(p for p in manifest["parts"] if p["label"]=="release-lever-2u")
    rear_lever_x_gap=40-lever["bounds"][1][0]
    assert rear_lever_x_gap>5
    all_bounds=np.array([p["bounds"] for p in manifest["parts"]])
    envelope=all_bounds[:,1].max(axis=0)-all_bounds[:,0].min(axis=0)
    assert envelope[1]<36
    report={"variant_mm":variant,"dimensions_mm":holder.extents.tolist(),
            "watertight":bool(holder.is_watertight),"one_connected_solid":True,
            "flat_underside_above_bed_mm2":flat_area,"minimum_underside_slope_deg":angle,
            "minimum_sampled_vault_skin_mm":float(skin.min()),"contact_checks":samples,
            "rear_support_to_lever_x_gap_mm":rear_lever_x_gap,
            "reference_envelope_mm":envelope.tolist(),"checked_parts":checked,
            "skipped_non_volume_parts":skipped,"missing_assembly_links":manifest["skipped"],
            "resolved_assembly_links":manifest["resolved_links"],"collisions":collisions,
            "scope":"Saved static pose and partial reference geometry only. No physical fit, insertion, lever motion, wiring, motor or fastener clearance validation."}
    (HERE/f"generated/geometry-check-{variant}.json").write_text(json.dumps(report,indent=2)+"\n")
    print(f"{variant} mm: {holder.extents} mm; one closed solid; underside {angle:.2f}° minimum; {flat_area:.3f} mm² elevated flat area",flush=True)
    print(f"  18 contact samples; vault skin {skin.min():.2f} mm; lever separation {rear_lever_x_gap:.2f} mm",flush=True)
    print(f"  {len(checked)} closed parts in four lanes; {len(skipped)} skipped; {len(collisions)} collisions",flush=True)
    for collision in collisions:print(collision,flush=True)
    assert not collisions
