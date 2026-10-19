# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "manifold3d==3.3.2", "networkx==3.5", "rtree==1.4.1"]
# ///
"""Check exported parts against the existing mount, each other and reel envelope.

Geometric screening only: it does not predict printed fit, spring life or
release torque. The intentional interference is confined to the smooth pilot.
"""
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import trimesh
from build import PARTS

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "generated"
PARAMS = {k: float(v) for k, v in re.findall(
    r"^(\w+)\s*=\s*([\d.]+)\s*;", (HERE / "thimble.scad").read_text(), re.M)}


def common(a, b):
    return trimesh.boolean.intersection([a, b], engine="manifold")


def volume(mesh):
    return abs(float(mesh.volume)) if len(mesh.faces) else 0.0


def bounds_box(lo, hi):
    lo, hi = np.array(lo), np.array(hi)
    return trimesh.creation.box(extents=hi-lo,
                                transform=trimesh.transformations.translation_matrix((lo+hi)/2))


def main():
    p = PARAMS
    report = {"prototype": "01", "parameters": p, "parts": {}}
    meshes = {}
    for part, filename in PARTS.items():
        m = trimesh.load_mesh(HERE / "stl" / filename)
        assert m.is_volume, f"{part}: must be a closed, consistently wound positive solid"
        assert len(m.split()) == 1, f"{part}: disconnected shells"
        assert abs(m.bounds[0, 2]) < 1e-5
        normals, centers = m.face_normals, m.triangles_center
        downward = (normals[:, 2] < -1e-5) & (centers[:, 2] > .02)
        flat_area = float(m.area_faces[downward & (normals[:, 2] < -.99999)].sum())
        angles = np.degrees(np.arccos(np.clip(-normals[downward, 2], 0, 1)))
        report["parts"][part] = {
            "file": filename, "watertight": True, "connected_solids": 1,
            "sha256": hashlib.sha256((HERE / "stl" / filename).read_bytes()).hexdigest(),
            "bounds_mm": m.bounds.tolist(), "volume_mm3": float(m.volume),
            "elevated_flat_underside_area_mm2": flat_area,
            "minimum_downward_face_angle_from_horizontal_deg": float(angles.min()),
        }
        assert flat_area < .01, (part, "flat underside", flat_area)
        # Faceted helical flanks and small seam triangles can be slightly off
        # the analytic angle. Report the actual worst mesh face.
        assert angles.min() > 44.99, (part, "overhang", angles.min())
        meshes[part] = m

    body, screw = meshes["thimble"].copy(), meshes["screw"].copy()
    body.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    body.apply_translation([0, 0, p["seat_z"]])
    screw.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))
    screw.apply_translation([0, 0, p["seat_z"]+p["head_thickness"]])
    assert np.allclose(screw.extents, [30, 30, 11], atol=.002)
    head = common(screw, bounds_box([-20,-20,p["seat_z"]], [20,20,20]))
    assert abs(head.extents[2]-p["head_thickness"]) < .001
    assert abs(body.bounds[1,2]-p["seat_z"]) < .001

    key = trimesh.load_mesh(HERE / "reference/quarter-turn-mount.stl")
    key_region = bounds_box([-15,-15,-3], [15,15,.1])
    preserved = common(body, key_region)
    expected = common(key, key_region)
    assert abs(volume(preserved)-volume(expected)) < .001
    assert volume(trimesh.boolean.difference([preserved, expected], engine="manifold")) < .001
    arm = trimesh.load_mesh(OUT / "spool-arm.stl")
    original = trimesh.load_mesh(OUT / "original-thimble.stl")
    original_overlap = volume(common(original, arm))
    new_overlap = volume(common(body, arm))
    assert abs(new_overlap-original_overlap) < .01
    assert volume(common(screw, arm)) < .001
    report["arm_mount"] = {
        "original_mount_preserved_below_z_mm": .1,
        "original_overlap_mm3": original_overlap, "new_overlap_mm3": new_overlap,
        "screw_arm_overlap_mm3": 0,
        "note": "Retains original quarter-turn mounting interface; not a new latch.",
    }

    # Actual rigid overlap must be exclusively in the compliant pilot. Trace
    # one complete turn outward, following the real right-hand helical path.
    motion = []
    for turn in np.linspace(0, 1, 17):
        moving = screw.copy()
        moving.apply_transform(trimesh.transformations.rotation_matrix(turn*2*np.pi, [0,0,1]))
        moving.apply_translation([0,0,turn*p["thread_pitch"]])
        hit = common(body, moving)
        pilot_bounds = bounds_box([-6,-6,3.0], [6,6,4.90])
        allowed = common(hit, pilot_bounds) if len(hit.faces) else hit
        illegal = volume(hit)-volume(allowed)
        assert illegal < .002, ("Thread or head collision", turn, illegal)
        motion.append({"turns_out": float(turn), "pilot_interference_mm3": volume(hit)})
    assert motion[0]["pilot_interference_mm3"] > .1
    assert motion[-1]["pilot_interference_mm3"] < .001
    report["screw_motion"] = motion
    report["thread_and_pilot"] = {
        "major_diameter_mm": p["thread_diameter"], "pitch_mm": p["thread_pitch"],
        "normal_radial_clearance_mm": p["radial_clearance"],
        "minimum_body_wall_at_thread_mm": (p["shaft_diameter"]-p["thread_diameter"])/2-p["radial_clearance"],
        "pilot_diameter_mm": p["thread_diameter"]-2*p["thread_depth"],
        "locking_collar_diameter_mm": p["thread_diameter"]-2*p["thread_depth"]-2*p["locking_interference"],
        "pilot_nose_to_cone_axial_clearance_mm": p["seat_z"]-p["stem_length"]-p["bore_cone_tip_z"]-(p["thread_diameter"]/2-p["thread_depth"]-.3),
    }

    # Repo reel reference is an annulus: 177 mm OD, 13.3 mm ID, 10 mm wide.
    # Test its full axial travel between the original arm plane and new cap.
    reel = trimesh.creation.annulus(r_min=6.65, r_max=88.5, height=10, sections=256)
    for base in [0.1, 0.8, 1.5]:
        placed = reel.copy(); placed.apply_translation([0,0,base+5])
        assert volume(common(body, placed)) < .001
        assert volume(common(screw, placed)) < .001
    report["reference_reel"] = {
        "hub_diameter_mm": 13.3, "width_mm": 10,
        "radial_hub_clearance_mm": (13.3-p["shaft_diameter"])/2,
        "retainer_radial_overlap_mm": (p["head_diameter"]-13.3)/2,
        "scope": "Reference reel only; other reel hubs and widths require fit testing.",
    }

    for pitch in [24, 42]:
        # Heads are transverse disks at different axial stations; comparing
        # their diameter to holder slot pitch would be the wrong orientation.
        for distance in [-pitch, pitch]:
            for mesh in [arm, body, screw]:
                shifted = mesh.copy(); shifted.apply_translation([0,0,distance])
                assert volume(common(screw, shifted)) < .001
        report[f"neighbor_{pitch}mm_pitch"] = "No rigid overlap with adjacent arm, thimble or screw"
    report["limits"] = [
        "No physical print, retention torque, wear, creep or transport test has been performed.",
        "Spring behavior depends on filament and printer calibration; PETG is the intended material.",
        "Original arm mount geometry is retained; hold the thimble against turning when undoing the cap.",
    ]
    (OUT / "geometry-check.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
