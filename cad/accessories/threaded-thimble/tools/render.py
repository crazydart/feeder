"""Render the actual exported meshes with Blender, including an assembled section.

blender --background --python tools/render.py
"""
import math
import sys
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parents[1]
SELECT = set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name, color, roughness=.36):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color,1)
    bsdf.inputs["Roughness"].default_value = roughness
    return m


TEAL = material("Thimble / teal", (.018,.28,.31))
ORANGE = material("Retaining screw / orange", (.93,.25,.045))
GRAY = material("Original spool arm", (.075,.09,.11))
FLOOR = material("Background", (.79,.82,.84), .75)


def load(path, mat):
    bpy.ops.wm.stl_import(filepath=str(path))
    obj = bpy.context.object
    obj.data.materials.append(mat)
    return obj


def camera(location, target, scale):
    cam = bpy.context.scene.camera
    cam.location = location
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = scale
    cam.data.clip_end = 5000


def area(location, power, size):
    d = bpy.data.lights.new("Softbox", "AREA")
    d.energy = power; d.shape = "DISK"; d.size = size
    o = bpy.data.objects.new("Softbox", d)
    bpy.context.collection.objects.link(o)
    o.location = location
    o.rotation_euler = (Vector((0,0,7))-o.location).to_track_quat("-Z","Y").to_euler()


def cut(obj, location, dimensions, operation="DIFFERENCE"):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    cutter = bpy.context.object; cutter.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    bpy.context.view_layer.objects.active = obj
    modifier = obj.modifiers.new("Inspection section", "BOOLEAN")
    modifier.operation = operation; modifier.solver = "EXACT"; modifier.object = cutter
    bpy.ops.object.modifier_apply(modifier=modifier.name)
    bpy.data.objects.remove(cutter, do_unlink=True)


def render(name):
    if SELECT and name[:2] not in SELECT:
        return
    scene.render.filepath = str(HERE / "renders" / name)
    bpy.ops.render.render(write_still=True)


scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.samples = 64
scene.cycles.use_denoising = True
scene.render.resolution_x = 1800
scene.render.resolution_y = 1200
scene.render.resolution_percentage = 100
scene.world.use_nodes = True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.8,.85,.9,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.55
scene.view_settings.view_transform = "AgX"
bpy.ops.object.camera_add()
scene.camera = bpy.context.object
area((10,-70,100), 110000, 75)
area((-65,10,60), 65000, 60)
area((60,50,80), 95000, 65)
bpy.ops.mesh.primitive_plane_add(size=1000, location=(0,0,-.06))
floor = bpy.context.object; floor.data.materials.append(FLOOR)

body = load(HERE / "stl/threaded-thimble-prototype-01.stl", TEAL)
screw = load(HERE / "stl/reel-retaining-screw-30mm-prototype-01.stl", ORANGE)
# Show the thimble upright for inspection, with its threaded mouth visible.
# Its STL itself prints in the opposite orientation, mouth against the bed.
body.rotation_euler.x = math.pi
body.location = (-18,0,14)
screw.location.x = 9
camera((35,-75,60), (-3,0,5), 65)
render("01-two-printable-parts.png")

# The same STLs, restored to their native mating coordinates. Only the
# display section is cut; the downloadable meshes remain whole parts.
body.location = (0,0,11.5)
screw.location = (0,0,14.5)
screw.rotation_euler.x = math.pi
body.rotation_euler.z = math.radians(22.5)
screw.rotation_euler.z = math.radians(22.5)
cut(body, (0,-25,10), (80,50,80))
cut(screw, (0,-25,10), (80,50,80))
floor.location.z = -2.56
camera((15,-60,30), (0,0,7), 47)
render("02-assembled-section.png")

# Exploded mounting detail uses the repository's actual spool arm.
body.hide_render = True; screw.hide_render = True
body = load(HERE / "stl/threaded-thimble-prototype-01.stl", TEAL)
body.rotation_euler.x = math.pi
body.location.z = 11.5
screw = load(HERE / "stl/reel-retaining-screw-30mm-prototype-01.stl", ORANGE)
screw.location.z = 34.5
screw.rotation_euler.x = math.pi
arm = load(HERE / "generated/spool-arm.stl", GRAY)
cut(arm, (6,0,2), (48,36,25), "INTERSECT")
floor.location.z = -2.6
camera((32,-70,34), (4,0,15), 80)
render("03-exploded-mount.png")
