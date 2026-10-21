# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "manifold3d==3.3.2", "networkx==3.5", "rtree==1.4.1"]
# ///
"""Verify the integrated arm, added reel width and compatibility with the tested cap."""
import hashlib
import json
import re
import subprocess
from pathlib import Path
import numpy as np
import trimesh
from build import INTEGRATED_ARM, PARTS, PROTOTYPE_02_ARM, PROTOTYPE_03_ARM
from check_geometry import common, volume, bounds_box

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "generated"


def export(source, part, name):
    target = OUT / name
    subprocess.run(["openscad", "--backend", "Manifold", "--export-format", "binstl",
                    "-D", f'part="{part}"', "-o", str(target), str(HERE/source)],
                   check=True, capture_output=True)
    return trimesh.load_mesh(target)


def main():
    OUT.mkdir(exist_ok=True)
    p = {k:float(v) for k,v in re.findall(r"^(\w+)\s*=\s*(-?[\d.]+)\s*;",
                                         (HERE/"integrated-arm.scad").read_text(),re.M)}
    lift, back, old_face = p["spindle_extension"], p["arm_back_z"], p["arm_face_z"]
    extra = p["reinforcement_height"]
    face = old_face + extra
    shift = lift + extra
    seat = p["original_seat_z"] + shift
    print_mesh = trimesh.load_mesh(HERE/"stl"/INTEGRATED_ARM)
    assert print_mesh.is_volume and len(print_mesh.split()) == 1
    assert abs(print_mesh.bounds[0,2]) < 1e-5
    assert abs(print_mesh.bounds[1,2]-(seat-back)) < 1e-5
    n,c = print_mesh.face_normals,print_mesh.triangles_center
    down = (n[:,2]<-1e-5)&(c[:,2]>.02)
    flat_area = float(print_mesh.area_faces[down&(n[:,2]<-.99999)].sum())
    # Boolean intersections leave float32 sliver facets along the chamfer
    # and reinforcement edge. Record them; screen practical overhangs on faces whose
    # smallest altitude exceeds 0.00001 mm, with a strict total-area limit.
    longest_edge = np.linalg.norm(np.roll(print_mesh.triangles,1,axis=1)-
                                  print_mesh.triangles,axis=2).max(axis=1)
    significant = down & (2*print_mesh.area_faces/longest_edge > 1e-5)
    tiny_area = float(print_mesh.area_faces[down & ~significant].sum())
    assert tiny_area < .0001
    min_angle = float(np.degrees(np.arccos(np.clip(-n[significant,2],0,1))).min())
    assert flat_area < .01
    # The untouched source arm has a few chamfer facets at 44.505 degrees.
    assert min_angle > 44.4
    arm = print_mesh.copy(); arm.apply_translation([0,0,back])
    original = trimesh.load_mesh(HERE/"reference/spool-arm.stl")
    removed = volume(trimesh.boolean.difference([original,arm],engine="manifold"))
    assert removed < .001, "Existing arm/feeder attachment material was removed"
    additions = trimesh.boolean.difference([arm,original],engine="manifold")
    attachment = bounds_box([p["reinforcement_end"],-70,-5],[150,20,25])
    assert volume(common(additions,attachment)) < .001, "Feeder attachment changed"
    guard_region = bounds_box([100,-70,face+.0001],[150,20,25])
    assert volume(common(additions,guard_region)) < .001, "Raised tape guard changed"

    # Independently extrude the original low top-face triangles: every point
    # of that entire beam footprint, including the diagonal guard junction,
    # must contain the added thickness. This catches a narrow/tapered neck
    # that a few section samples could miss.
    flat = ((original.face_normals[:,2]>.99999) &
            (abs(original.triangles_center[:,2]-old_face)<.001))
    triangles = original.triangles[flat,:,:2]
    vertices, inverse = np.unique(triangles.reshape(-1,2),axis=0,return_inverse=True)
    required = trimesh.creation.extrude_triangulation(vertices,inverse.reshape(-1,3),extra)
    required.apply_translation([0,0,old_face])
    missing_reinforcement = volume(trimesh.boolean.difference([required,arm],engine="manifold"))
    assert missing_reinforcement < .001, "Thin spot before the tape guard"
    assert abs(face-back-4) < 1e-9

    thickness = []
    for x,y in [(20,-9),(50,-20),(80,-34),(100,-43),(108,-46.5),
                (111.5,-46.5),(114,-44),(115,-43.6)]:
        zs, original_zs = [] , []
        for mesh,values in [(arm,zs),(original,original_zs)]:
            hits,_,_ = mesh.ray.intersects_location([[x,y,-10]],[[0,0,1]])
            values.extend(hits[:,2])
        measured, prior = max(zs)-min(zs), max(original_zs)-min(original_zs)
        # The final ray crosses the original lower perimeter chamfer.
        # Even there, the new top must remain 4 mm above the bed datum,
        # with the full 1.5 mm reinforcement and no upper-face taper.
        assert abs(max(zs)-back-4) < .002, (x, y, zs)
        assert abs(measured-prior-extra) < .002, (x, y, measured, prior)
        if abs(prior-2.5) < .002:
            assert abs(measured-4) < .002
        thickness.append({"x_mm":x,"y_mm":y,"original_mm":float(prior),
                          "reinforced_mm":float(measured),
                          "top_above_bed_datum_mm":float(max(zs)-back),
                          "original_lower_edge_chamfer_mm":float(min(original_zs)-back)})

    # The socket must now be solid through the entire thickness of the arm.
    backing = trimesh.creation.cylinder(radius=8.4,height=face-back-.02,sections=128)
    backing.apply_translation([0,0,(face+back)/2])
    assert volume(trimesh.boolean.difference([backing,arm],engine="manifold")) < .001
    root = trimesh.creation.cylinder(radius=p["spindle_diameter"]/2-.01,
                                     height=.9,sections=128)
    root.apply_translation([0,0,face+.45])
    assert volume(trimesh.boolean.difference([root,arm],engine="manifold")) < .001

    # Verify the ENTIRE proven bore is translated, including its pilot collar.
    bore = export("integrated-arm.scad","bore","integrated-bore.stl")
    old_bore = export("thimble.scad","female","prototype-01-bore.stl")
    old_bore.apply_translation([0,0,shift])
    bore_diff = sum(volume(trimesh.boolean.difference(pair,engine="manifold"))
                    for pair in ([bore,old_bore],[old_bore,bore]))
    assert bore_diff < .001
    old_report = json.loads((HERE/"validation.json").read_text())
    cap_path = HERE/"stl"/PARTS["screw"]
    cap_hash = hashlib.sha256(cap_path.read_bytes()).hexdigest()
    assert cap_hash == old_report["parts"]["screw"]["sha256"], "Tested cap changed"
    cap = trimesh.load_mesh(cap_path)
    cap.apply_transform(trimesh.transformations.rotation_matrix(np.pi,[1,0,0]))
    cap.apply_translation([0,0,seat+3])
    previous = json.loads((HERE/"validation-prototype-02.json").read_text())
    assert hashlib.sha256((HERE/"stl"/PROTOTYPE_02_ARM).read_bytes()).hexdigest() == previous["arm_sha256"]
    assert abs((seat-face)-previous["revised_reel_space_mm"]+1) < 1e-9
    prototype_03 = json.loads((HERE/"validation-prototype-03.json").read_text())
    assert hashlib.sha256((HERE/"stl"/PROTOTYPE_03_ARM).read_bytes()).hexdigest() == prototype_03["arm_sha256"]
    assert abs((seat-face)-prototype_03["revised_reel_space_mm"]) < 1e-9

    motion = []
    for turn in np.linspace(0,1,17):
        moved = cap.copy()
        moved.apply_transform(trimesh.transformations.rotation_matrix(turn*2*np.pi,[0,0,1]))
        moved.apply_translation([0,0,turn*2])
        hit = common(arm,moved)
        allowed = common(hit,bounds_box([-6,-6,3+shift],[6,6,4.9+shift])) if len(hit.faces) else hit
        assert volume(hit)-volume(allowed) < .002
        motion.append({"turns_out":float(turn),"pilot_interference_mm3":volume(hit)})
    assert motion[0]["pilot_interference_mm3"] > .1
    assert motion[-1]["pilot_interference_mm3"] < .001

    # A 12 mm wide reel is 2 mm wider than the original CAD reference.
    reel = trimesh.creation.annulus(r_min=6.65,r_max=88.5,height=12,sections=256)
    for lower_face in [face,seat-12]:
        placed = reel.copy();placed.apply_translation([0,0,lower_face+6])
        assert volume(common(arm,placed)) < .001
        assert volume(common(cap,placed)) < .001

    report = {
        "prototype":"04", "parameters":p,
        "arm_file":INTEGRATED_ARM,
        "arm_sha256":hashlib.sha256((HERE/"stl"/INTEGRATED_ARM).read_bytes()).hexdigest(),
        "screw_file":PARTS["screw"], "screw_sha256":cap_hash, "screw_unchanged":True,
        "watertight":True,"connected_solids":1,"bounds_print_mm":print_mesh.bounds.tolist(),
        "volume_mm3":float(print_mesh.volume),
        "elevated_flat_underside_area_mm2":flat_area,
        "minimum_underside_angle_from_horizontal_deg":min_angle,
        "excluded_sub_micron_downward_sliver_area_mm2":tiny_area,
        "original_arm_material_removed_mm3":removed,
        "socket_solid_through_arm":True, "solid_spindle_root_diameter_mm":p["spindle_diameter"],
        "original_reel_space_mm":p["original_seat_z"]-old_face,
        "prototype_02_reel_space_mm":previous["revised_reel_space_mm"],
        "revised_reel_space_mm":seat-face, "added_reel_space_mm":lift,
        "reduction_from_prototype_02_mm":previous["revised_reel_space_mm"]-(seat-face),
        "reel_contact_face_native_z_mm":face,
        "screw_seat_native_z_mm":seat,
        "reinforced_sections":thickness,
        "continuous_beam_thickness_mm":face-back,
        "missing_reinforcement_over_entire_original_beam_mm3":missing_reinforcement,
        "original_low_beam_max_x_mm":float(triangles[:,:,0].max()),
        "raised_tape_guard_unchanged":True,
        "feeder_attachment_unchanged_beyond_x_mm":p["reinforcement_end"],
        "translated_bore_symmetric_difference_mm3":bore_diff,
        "screw_motion":motion,
        "reference_reel":{"diameter_mm":177,"hub_diameter_mm":13.3,"width_mm":12,
                          "remaining_axial_play_mm":seat-face-12},
        "limits":["The previous screw mechanism passed the user's physical test; its STL is unchanged.",
                  "Prototype 02 worked in the user's physical test, with excess reel play and arm flex under a full reel.",
                  "Prototype 04's continuous 4 mm arm has not been physically tested.",
                  "Beam thickness and solid continuity are checked; no mechanical load or fatigue test was performed.",
                  "Neighboring feeder spacing is outside this revision's validation scope, as requested."],
    }
    (OUT/"integrated-geometry-check.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))


if __name__ == "__main__":
    main()
