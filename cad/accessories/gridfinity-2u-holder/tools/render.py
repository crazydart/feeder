"""Blender render driver. Run after export_feeders.py and the OpenSCAD export.

blender --background --python tools/render.py -- 16 final
blender --background --python tools/render.py -- 24 final
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parents[1]

ARGS = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["16", "final"]
VARIANT = int(ARGS[0])
MODE = ARGS[1] if len(ARGS)>1 else "final"
SELECT = set(ARGS[2:])
REF = HERE / f"generated/reference-{VARIANT}"
RENDER_DIR = f"renders/prototype-02/{VARIANT}mm"
FEEDER_Z = 69
X_SHIFT = 15.5
Y_SHIFT = -13.25
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, metal=0, rough=0.4):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    return m


MATS = {
    "black": material("Feeder • charcoal", (0.026,0.032,0.036), rough=0.48),
    "pcb": material("PCB • green", (0.018,0.22,0.11), rough=0.35),
    "pcb_dark": material("PCB traces", (0.015,0.12,0.06), rough=0.4),
    "gold": material("Exposed pads", (0.64,0.47,0.15), metal=0.75),
    "metal": material("Steel", (0.46,0.49,0.53), metal=0.85, rough=0.28),
    "component": material("Components", (0.035,0.04,0.045), metal=0.18),
    "yellow": material("Release latch", (0.95,0.57,0.025), rough=0.42),
    "ivory": material("Gear nylon", (0.80,0.78,0.67), rough=0.43),
    "holder": material("Holder • teal", (0.018,0.30,0.34), rough=0.38),
    "floor": material("Backdrop", (0.69,0.73,0.75), rough=0.78),
}


def load_stl(path, mat):
    bpy.ops.wm.stl_import(filepath=str(path))
    o = bpy.context.object
    o.data.materials.clear()
    o.data.materials.append(mat)
    return o


feeders = []
manifest = json.loads((REF / "manifest.json").read_text())
for item in manifest["parts"]:
    o = load_stl(REF / item["file"], MATS[item["material"]])
    o.name = item["label"] + " / " + item["part"]
    feeders.append(o)


def camera(location, target, scale):
    c = bpy.context.scene.camera
    c.location = location
    c.rotation_euler = (Vector(target) - c.location).to_track_quat("-Z", "Y").to_euler()
    c.data.type = "ORTHO"
    c.data.ortho_scale = scale
    c.data.clip_end = 4000


def area(name, location, target, power, size):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = power
    d.shape = "DISK"
    d.size = size
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = location
    o.rotation_euler = (Vector(target)-o.location).to_track_quat("-Z", "Y").to_euler()


scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 32 if MODE == "reference" else 48
scene.cycles.use_denoising = True
scene.render.resolution_x = 1800
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.world.color = (0.55,0.55,0.55)
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(0.75,0.80,0.84,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=0.55
scene.view_settings.view_transform = "AgX"
bpy.ops.object.camera_add()
scene.camera = bpy.context.object
area("Key", (80,-220,350), (0,0,25), 2500000, 260)
area("Fill", (-240,150,180), (0,0,20), 1800000, 200)
area("Rim", (150,170,300), (0,0,25), 2000000, 160)


def render(filename):
    if SELECT and Path(filename).name[:2] not in SELECT:
        return
    scene.render.filepath = str(HERE / filename)
    bpy.ops.render.render(write_still=True)


if MODE == "reference":
    scene.render.resolution_x=1600
    scene.render.resolution_y=900
    camera((-150,-320,190),(-15,15,-5),240)
    render(f"generated/reference-{VARIANT}-iso.png")
    camera((-15,-400,-5),(-15,15,-5),230)
    render(f"generated/reference-{VARIANT}-side.png")
else:
    holder=load_stl(HERE / "generated/holder.stl",MATS["holder"])
    holder.name="Gridfinity 16/24 mm holder • prototype 02"
    bevel=holder.modifiers.new("Render edge highlights","BEVEL")
    bevel.width=0.25
    bevel.segments=2
    bevel.limit_method="ANGLE"
    # Put the near lane at Y=-63; keep it empty to reveal the cradle.
    originals=list(feeders)
    for o in originals: o.location=(X_SHIFT,-21+Y_SHIFT,FEEDER_Z)
    for lane in [21,63]:
        for original in originals:
            o=original.copy()
            o.data=original.data
            bpy.context.collection.objects.link(o)
            o.location=(X_SHIFT,lane+Y_SHIFT,FEEDER_Z)
            feeders.append(o)
    bpy.ops.mesh.primitive_plane_add(size=10000,location=(0,0,-0.12))
    floor=bpy.context.object
    floor.data.materials.append(MATS["floor"])
    camera((-260,-350,290),(0,0,56),355)
    render(f"{RENDER_DIR}/01-loaded.png")
    for o in feeders:o.hide_render=True
    camera((-240,-320,300),(0,0,30),305)
    render(f"{RENDER_DIR}/02-empty.png")
    section=holder.copy();section.data=holder.data.copy()
    bpy.context.collection.objects.link(section)
    section.modifiers.clear()
    # Rear half of the second lane, revealing latch pocket and support pads.
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-10.5,70))
    cutter=bpy.context.object
    cutter.dimensions=(240,21,150)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.context.view_layer.objects.active=section
    modifier=section.modifiers.new("Lane cutaway","BOOLEAN")
    modifier.operation="INTERSECT";modifier.solver="EXACT";modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    holder.hide_render=True
    for o in originals:o.hide_render=False
    scene.render.resolution_x=1800;scene.render.resolution_y=1000
    camera((0,-420,100),(0,-21,58),245)
    render(f"{RENDER_DIR}/03-side-section.png")
    section.hide_render=True
    for o in feeders:o.hide_render=True
    holder.hide_render=False;floor.hide_render=True
    scene.render.resolution_x=1800;scene.render.resolution_y=1200
    camera((-230,-320,-270),(0,0,25),310)
    render(f"{RENDER_DIR}/04-underside.png")
    for o in feeders:o.hide_render=False
    floor.hide_render=False
    camera((-260,-350,290),(0,0,56),355)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE/f"generated/prototype-02-{VARIANT}.blend"))
