# /// script
# requires-python = ">=3.11,<3.14"
# dependencies = ["trimesh==5.1.1", "manifold3d", "networkx==3.5", "rtree"]
# ///
"""Validate underside slopes, holder mesh and seated reference clearances.

This screening cannot validate non-volume source meshes, physical tolerances,
or motion. Those limits are retained in the JSON report.
"""
import json
import subprocess
import warnings
from pathlib import Path
import numpy as np
import trimesh
from model_parameters import parameters

HERE = Path(__file__).resolve().parents[1]
PARAMS = parameters()
FEEDER_Z = PARAMS["feeder_z"]
SLOT_PITCH = PARAMS["slot_pitch"]
LANES = PARAMS["lanes"]
holder = trimesh.load_mesh(HERE / "generated/holder.stl")
assert holder.is_volume, "Holder must be a closed, consistently oriented volume"
assert len(holder.split()) == 1, "Holder must be one connected part"
assert np.allclose(holder.extents, [PARAMS[k] for k in ["length", "width", "height"]], atol=0.02)
source = json.loads((HERE / "generated/reference/manifest.json").read_text())

# Entire feeder envelopes are disjoint at the tighter pitch, including source
# meshes that cannot participate in volume intersection screening.
all_bounds = np.array([part["bounds"] for part in source["parts"]])
feeder_width = float(all_bounds[:, 1, 1].max() - all_bounds[:, 0, 1].min())
adjacent_feeder_gap = SLOT_PITCH - feeder_width
assert adjacent_feeder_gap > 2.5
# Bound every source part reaching the low rail height
# in the central pocket; this also includes the non-volume frame and PCB art.
low_parts = [part for part in source["parts"]
             if part["bounds"][0][2] + FEEDER_Z <= PARAMS["rail_z"]
             and part["bounds"][0][0] < 14 and part["bounds"][1][0] > -78]
low_y_min = min(part["bounds"][0][1] for part in low_parts) + 7.5
low_y_max = max(part["bounds"][1][1] for part in low_parts) + 7.5
pocket_side_clearance = min(low_y_min + 11, 11 - low_y_max)
assert pocket_side_clearance >= 2

# In the feet-down print orientation, every horizontal underside must be on
# the bed. Check the exported triangles, including concealed pocket ceilings.
normals = holder.face_normals
centers = holder.triangles_center
above_bed = centers[:, 2] > 0.05
flat_underside = (normals[:, 2] < -0.999999) & above_bed
flat_area = float(holder.area_faces[flat_underside].sum())
assert flat_area < 0.001, f"Elevated flat underside: {flat_area:.3f} mm²"
downward = (normals[:, 2] < -1e-6) & above_bed
angles = np.degrees(np.arccos(np.clip(-normals[downward, 2], 0, 1)))
minimum_angle = float(angles.min())
assert minimum_angle >= 44.99, f"Underside slope is only {minimum_angle:.3f} degrees"

# The widest vaults occur where four rounded feet meet. Their crowns must
# leave at least 2 mm of material below the lowest cradle floor at Z = 9.
vault_xy = np.array([[x, y] for x in [-63, -21, 21, 63] for y in [-21, 21]])
vault_hits, vault_ids, _ = holder.ray.intersects_location(
    np.column_stack([vault_xy, np.full(len(vault_xy), -1)]),
    np.tile([0, 0, 1], (len(vault_xy), 1)), multiple_hits=True)
vault_samples = []
for i, pt in enumerate(vault_xy):
    assert i in vault_ids, "Vault crown ray misses the base"
    roof_z = float(vault_hits[vault_ids == i, 2].min())
    skin = PARAMS["floor_z"] - roof_z
    assert 2.0 <= skin < 3.0, f"Unexpected skin above vault crown: {skin:.3f} mm"
    vault_samples.append({"xy_mm": pt.tolist(), "roof_z_mm": roof_z,
                          "skin_below_lowest_floor_mm": skin})

# Check the new ledge against the actual frame surface. The inherited frame
# mesh is not closed, so use local surface rays rather than a volume boolean.
support_file = HERE / "generated/frame-support.stl"
subprocess.run(["openscad", "-D", 'render_part="support"', "-o",
                str(support_file), str(HERE / "holder.scad")],
               check=True, capture_output=True, text=True)
support = trimesh.load_mesh(support_file)
assert support.is_volume
frame_part = next(p for p in source["parts"] if p["label"] == "frame-8")
frame = trimesh.load_mesh(HERE / "generated/reference" / frame_part["file"])
frame.apply_translation([0,7.5,FEEDER_Z])
b = support.bounds
xy = np.array([[b[0,0]+fx*(b[1,0]-b[0,0]), b[0,1]+fy*(b[1,1]-b[0,1])]
               for fx in [0.2,0.5,0.8] for fy in [0.2,0.5,0.8]])
origins_below = np.column_stack([xy,np.full(len(xy),-100)])
origins_above = np.column_stack([xy,np.full(len(xy),150)])
frame_hits, frame_ids, _ = frame.ray.intersects_location(
    origins_below,np.tile([0,0,1],(len(xy),1)),multiple_hits=True)
support_hits, support_ids, _ = support.ray.intersects_location(
    origins_above,np.tile([0,0,-1],(len(xy),1)),multiple_hits=True)
contact_samples = []
for i, pt in enumerate(xy):
    assert i in frame_ids and i in support_ids, "Support sample misses a contact surface"
    frame_z = frame_hits[frame_ids==i,2].min()
    support_z = support_hits[support_ids==i,2].max()
    gap = float(frame_z-support_z)
    assert abs(gap)<0.02, f"New support does not seat against the frame: gap {gap} mm"
    contact_samples.append({"xy_mm": pt.tolist(),"frame_z_mm":float(frame_z),
                            "support_z_mm":float(support_z),"gap_mm":gap})
lever = next(p for p in source["parts"] if p["label"] == "release-lever")
pcb = next(p for p in source["parts"] if p["part"] == "Pcb_270f")
lever_x_gap = float(lever["bounds"][0][0]-b[1,0])
pcb_y_gap = float(pcb["bounds"][0][1]+7.5-b[1,1])
assert lever_x_gap>3 and pcb_y_gap>0.9

# The new rear scallop must leave the forward arm seat usable.
arm_part = next(p for p in source["parts"] if p["source"] == "FDM/spool-holder.FCStd")
arm = trimesh.load_mesh(HERE / "generated/reference" / arm_part["file"])
arm.apply_translation([0, 7.5, FEEDER_Z])
arm_xy = np.array([[x, y] for x in [-94, -87, -80] for y in [3.7, 4.3, 5]])
def first_ray_hits(mesh, xy, z, direction):
    hits, ids, _ = mesh.ray.intersects_location(
        np.column_stack([xy, np.full(len(xy), z)]),
        np.tile([0, 0, direction], (len(xy), 1)), multiple_hits=True)
    assert all(i in ids for i in range(len(xy))), "Seat sample misses surface"
    return np.array([(hits[ids == i, 2].min() if direction > 0 else hits[ids == i, 2].max())
                     for i in range(len(xy))])
arm_gaps = first_ray_hits(arm, arm_xy, -1, 1) - first_ray_hits(holder, arm_xy, 150, -1)
assert (arm_gaps > -.02).all() and (arm_gaps < .25).all(), arm_gaps

# Reel OD/width are explicit assumptions, distinct from the observed +10 mm
# improvement. Screen the annular envelope at every axle and over a nominal
# baseplate top 4.75 mm above the foot-bottom datum.
reel = trimesh.load_mesh(HERE / "generated/reel-reference.stl")
assert reel.is_volume
reel_collisions = []
for lane in LANES:
    placed = reel.copy(); placed.apply_translation([0, lane, 0])
    common = trimesh.boolean.intersection([holder, placed], engine="manifold")
    if len(common.faces) and common.volume > .01:
        reel_collisions.append({"lane": lane, "volume_mm3": float(common.volume)})
assert not reel_collisions, reel_collisions
nominal_baseplate_top_z = 4.75
reel_bottom_z = PARAMS["reel_axle_z"] - PARAMS["reel_diameter"]/2
assert reel_bottom_z > nominal_baseplate_top_z
assert SLOT_PITCH > PARAMS["reel_width"]

checked, skipped, collisions = [], [], []
for part in source["parts"]:
    mesh = trimesh.load_mesh(HERE / "generated/reference" / part["file"])
    mesh.update_faces(mesh.nondegenerate_faces())
    mesh.remove_unreferenced_vertices()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        valid = mesh.is_volume
    if not valid:
        skipped.append({"label": part["label"], "part": part["part"],
                        "reason": "Reference mesh is not a closed positive volume"})
        continue
    checked.append({"label": part["label"], "part": part["part"]})
    for lane in LANES:
        placed = mesh.copy()
        placed.apply_translation([0, lane+7.5, FEEDER_Z])
        if (placed.bounds[0] >= holder.bounds[1]).any() or (placed.bounds[1] <= holder.bounds[0]).any():
            continue
        common = trimesh.boolean.intersection([holder, placed], engine="manifold")
        if len(common.faces) and common.volume > 0.01:
            collisions.append({"label": part["label"], "part": part["part"],
                               "lane_center_mm": lane, "intersection_mm3": float(common.volume)})

report = {
    "prototype": "06",
    "parameters": PARAMS,
    "slot_count": len(LANES),
    "slot_pitch_mm": SLOT_PITCH,
    "adjacent_feeder_envelope_gap_mm": adjacent_feeder_gap,
    "low_electronics_pocket_minimum_side_clearance_mm": pocket_side_clearance,
    "holder_dimensions_mm": holder.extents.tolist(),
    "holder_watertight": bool(holder.is_watertight),
    "holder_consistent_winding": bool(holder.is_winding_consistent),
    "holder_connected_components": 1,
    "holder_enclosed_volume_mm3": float(holder.volume),
    "feet_down_print_geometry": {
        "flat_downward_area_above_bed_mm2": flat_area,
        "minimum_underside_angle_from_horizontal_deg": minimum_angle,
        "vault_crown_samples": vault_samples,
        "scope": "Triangle slopes and sampled vault thickness; not a physical print validation.",
    },
    "new_frame_support": {
        "contact_samples": contact_samples,
        "lever_x_envelope_separation_mm": lever_x_gap,
        "pcb_y_envelope_separation_mm": pcb_y_gap,
        "scope": "Nine sampled frame contact points and static envelope separation; not a motion check.",
    },
    "retained_arm_seat": {
        "sample_xy_mm": arm_xy.tolist(), "gap_mm": arm_gaps.tolist(),
    },
    "reel_clearance": {
        "assumed_diameter_mm": PARAMS["reel_diameter"],
        "assumed_width_mm": PARAMS["reel_width"],
        "extra_lift_vs_prototype_04_mm": PARAMS["reel_lift"],
        "modeled_bottom_above_foot_datum_mm": reel_bottom_z,
        "nominal_baseplate_top_above_foot_datum_mm": nominal_baseplate_top_z,
        "modeled_clearance_above_nominal_baseplate_mm": reel_bottom_z-nominal_baseplate_top_z,
        "radial_relief_allowance_mm": PARAMS["reel_radial_clearance"],
        "holder_collisions": reel_collisions,
        "scope": "Assumed reel envelope on saved CAD axle; not a measurement of the photographed reel or loaded arm deflection.",
    },
    "checked_reference_parts": checked,
    "skipped_reference_parts": skipped,
    "skipped_assembly_links": source["skipped"],
    "intersections_above_0_01_mm3": collisions,
    "scope": "Partial seated-position and assumed reel-envelope screening only; no physical fit, insertion, latch-motion, arm-deflection or stability validation.",
}
(HERE / "generated/geometry-check.json").write_text(json.dumps(report, indent=2)+"\n")
print(f"Holder: {holder.extents.round(2)} mm; one closed volume")
print(f"Underside: {flat_area:.3f} mm² elevated flat area; minimum slope {minimum_angle:.2f} degrees")
print(f"Minimum sampled skin above vaults: {min(p['skin_below_lowest_floor_mm'] for p in vault_samples):.2f} mm")
print(f"Frame support: {len(contact_samples)} seated samples; lever X separation {lever_x_gap:.2f} mm; PCB Y separation {pcb_y_gap:.2f} mm")
print(f"Five lanes at {SLOT_PITCH} mm pitch; adjacent feeder envelope gap {adjacent_feeder_gap:.2f} mm; low pocket side clearance {pocket_side_clearance:.2f} mm")
print(f"Checked {len(checked)} reference parts in {len(LANES)} lanes; skipped {len(skipped)} non-volume reference meshes")
print(f"Reel: {PARAMS['reel_diameter']} mm OD x {PARAMS['reel_width']} mm; no holder collisions; nominal baseplate gap {reel_bottom_z-nominal_baseplate_top_z:.2f} mm")
print(f"Retained arm seat: {len(arm_gaps)} samples; gaps {arm_gaps.min():.3f}..{arm_gaps.max():.3f} mm")
print(f"Intersections above 0.01 mm³: {len(collisions)}")
for collision in collisions: print(collision)
assert not collisions, "Interference found; see generated/geometry-check.json"
