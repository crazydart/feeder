"""Blender render driver. Run after export_feeder.py and the OpenSCAD export.

blender --background --python tools/render.py -- [reference|final]
"""
import json
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE / "tools"))
from model_parameters import parameters
PARAMS = parameters()
REF = HERE / "generated/reference"
ARGS = sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else ["final"]
MODE = ARGS[0]
SELECT = set(ARGS[1:])
RENDER_DIR = "renders/prototype-06"
FEEDER_Z = PARAMS["feeder_z"]
LANES = PARAMS["lanes"]
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
scene.cycles.samples = 32 if MODE == "reference" else 64
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
    scene.render.resolution_x = 1600
    scene.render.resolution_y = 800
    camera((-70, -500, 5), (-70, -7, 5), 380)
    render("generated/reference-side.png")
    camera((220, -350, 230), (-70, -7, 0), 390)
    render("generated/reference-iso.png")
else:
    holder = load_stl(HERE / "generated/holder.stl", MATS["holder"])
    holder.name = "Gridfinity 8 mm holder • reel-clearance prototype 06"
    # Small rendered edge bevels improve legibility; source CAD remains sharp.
    bevel = holder.modifiers.new("Render edge highlights", "BEVEL")
    bevel.width = 0.35
    bevel.segments = 3
    bevel.limit_method = "ANGLE"
    # Reference CAD has its frame centered at Y=-7.5, with the latch down.
    for o in feeders:
        o.location = (0, LANES[0]+7.5, FEEDER_Z)
    originals = list(feeders)
    for lane in LANES[1:]:
        for original in originals:
            o = original.copy()
            o.data = original.data
            bpy.context.collection.objects.link(o)
            o.location = (0,lane+7.5,FEEDER_Z)
            feeders.append(o)
    reels = []
    for lane in LANES:
        reel = load_stl(HERE / "generated/reel-reference.stl", MATS["ivory"])
        reel.name = f"Assumed {PARAMS['reel_diameter']} mm reel envelope / lane {lane}"
        reel.location.y = lane
        bevel = reel.modifiers.new("Reference reel edge highlight", "BEVEL")
        bevel.width = .35; bevel.segments = 2
        reels.append(reel)
    # Show all five seated feeders and reference reels.
    bpy.ops.mesh.primitive_plane_add(size=10000, location=(0,0,-0.12))
    floor = bpy.context.object
    floor.name = "Studio floor"
    floor.data.materials.append(MATS["floor"])
    camera((255,430,330), (-80,0,85), 485)
    render(f"{RENDER_DIR}/01-loaded.png")
    for o in feeders: o.hide_render=True
    for o in reels: o.hide_render=True
    camera((245,320,315), (0,0,42), 330)
    render(f"{RENDER_DIR}/02-empty.png")
    # Section through the center slot, showing a single feeder and half cradle.
    section = holder.copy()
    section.data = holder.data.copy()
    bpy.context.collection.objects.link(section)
    section.name = "Side section • one lane"
    section.modifiers.clear()
    bpy.ops.mesh.primitive_cube_add(size=1,location=(0,-6,65))
    cutter = bpy.context.object
    cutter.dimensions=(420,12,140)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.context.view_layer.objects.active=section
    modifier=section.modifiers.new("Half of one channel", "BOOLEAN")
    modifier.operation="INTERSECT"
    modifier.solver="EXACT"
    modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    holder.hide_render=True
    for o in originals:
        o.hide_render=False
        o.location.y=7.5
    scene.render.resolution_x=2000
    scene.render.resolution_y=1000
    camera((-30,400,100),(-35,0,57),340)
    render(f"{RENDER_DIR}/03-side-section.png")
    section.hide_render=True
    for o in feeders: o.hide_render=True
    holder.hide_render=False
    floor.hide_render=True
    scene.render.resolution_x=1800
    scene.render.resolution_y=1200
    camera((240,320,-300),(0,0,30),330)
    render(f"{RENDER_DIR}/04-underside.png")
    # Actual base section through the magnet centers in two adjacent feet.
    # Show the conical ceilings and the pointed joint with all upper material
    # removed for inspection. This crop is a view, not an additional part.
    base_section = holder.copy()
    base_section.data = holder.data.copy()
    bpy.context.collection.objects.link(base_section)
    base_section.modifiers.clear()
    base_section.name = "Base cutaway • magnet roofs and foot joint"
    bpy.ops.mesh.primitive_cube_add(size=1,location=(21,-4,4.5))
    cutter = bpy.context.object
    cutter.dimensions=(84,34,9)
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.context.view_layer.objects.active=base_section
    modifier=base_section.modifiers.new("Cut at magnet centers", "BOOLEAN")
    modifier.operation="INTERSECT"
    modifier.solver="EXACT"
    modifier.object=cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter,do_unlink=True)
    holder.hide_render=True
    floor.hide_render=False
    scene.render.resolution_x=2000
    scene.render.resolution_y=750
    camera((64,160,48),(21,-2,4.5),110)
    render(f"{RENDER_DIR}/05-base-section.png")
    base_section.hide_render=True
    holder.hide_render=False
    # Side view: one feeder/reel and a datum strip representing the nominal
    # baseplate top (4.75 mm above the holder foot bottom), not a baseplate model.
    for o in originals:
        o.location.y=7.5
        o.hide_render=False
    reels[2].hide_render=False
    bpy.ops.mesh.primitive_cube_add(size=1,location=(-195,0,2.375))
    datum=bpy.context.object
    datum.name="Nominal baseplate-top datum strip • Z 4.75 mm"
    datum.dimensions=(180,140,4.75)
    datum.data.materials.append(MATS["floor"])
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    scene.render.resolution_x=2000
    scene.render.resolution_y=1100
    camera((-82,500,100),(-82,0,100),420)
    render(f"{RENDER_DIR}/06-reel-clearance.png")
    datum.hide_render=True
    scene.render.resolution_x=1800
    scene.render.resolution_y=1200
    # Save an editable scene in the default hero composition.
    for o in originals: o.location.y=LANES[0]+7.5
    for o in feeders: o.hide_render=False
    for o in reels: o.hide_render=False
    floor.hide_render=False
    camera((255,430,330),(-80,0,85),485)
    bpy.ops.wm.save_as_mainfile(filepath=str(HERE / "generated/prototype-06.blend"))
