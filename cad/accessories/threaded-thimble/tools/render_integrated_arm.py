"""Render prototype 02 from the actual print STL and unchanged cap STL."""
import math
import json
import subprocess
from pathlib import Path
import bpy
from mathutils import Vector

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / "renders/prototype-02"
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)


def material(name,color):
    m=bpy.data.materials.new(name);m.use_nodes=True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value=(*color,1)
    m.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value=.4
    return m


TEAL=material("Integrated arm and thimble",(.018,.28,.31))
ORANGE=material("Unchanged retaining screw",(.93,.25,.045))
FLOOR=material("Background",(.79,.82,.84))


def load_path(path,mat):
    bpy.ops.wm.stl_import(filepath=str(path))
    obj=bpy.context.object;obj.data.materials.append(mat)
    return obj


def load(name,mat):
    return load_path(HERE/"stl"/name,mat)


def camera(location,target,scale):
    cam=scene.camera;cam.location=location
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.type="ORTHO";cam.data.ortho_scale=scale;cam.data.clip_end=5000


def area(location,target,power,size):
    d=bpy.data.lights.new("Softbox","AREA");d.energy=power;d.shape="DISK";d.size=size
    o=bpy.data.objects.new("Softbox",d);bpy.context.collection.objects.link(o);o.location=location
    o.rotation_euler=(Vector(target)-o.location).to_track_quat("-Z","Y").to_euler()


def section(name,transform):
    # Section the actual STL with the same Manifold kernel used for export.
    # Keep these display-only meshes separate from the printable parts.
    folder=HERE/"generated";folder.mkdir(exist_ok=True)
    source=folder/(name+"-render-section.scad")
    target=source.with_suffix(".stl")
    imported=json.dumps(str(HERE/"stl"/name))
    source.write_text("intersection() {\n"+
        f"rotate([0,0,22.5]) {transform} import({imported});\n"+
        "translate([-15,0,-5]) cube([38,15,40]);\n}\n")
    subprocess.run(["openscad","--backend","Manifold","--export-format","binstl",
                    "-o",str(target),str(source)],check=True)
    return target


def render(name):
    scene.render.filepath=str(OUT/name)
    bpy.ops.render.render(write_still=True)


scene=bpy.context.scene;scene.render.engine="CYCLES"
scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1200
scene.render.resolution_percentage=100
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs["Color"].default_value=(.8,.85,.9,1)
scene.world.node_tree.nodes["Background"].inputs["Strength"].default_value=.55
scene.view_settings.view_transform="AgX"
bpy.ops.object.camera_add();scene.camera=bpy.context.object
area((20,-120,180),(55,-20,5),370000,130)
area((-80,50,140),(50,-20,5),220000,110)
area((160,80,180),(50,-20,5),280000,100)
bpy.ops.mesh.primitive_plane_add(size=1000,location=(0,0,-.06))
floor=bpy.context.object;floor.data.materials.append(FLOOR)
arm=load("spool-arm-integrated-thimble-plus2mm-prototype-02.stl",TEAL)
cap=load("reel-retaining-screw-30mm-prototype-01.stl",ORANGE)
cap.location=(0,-32,0)
camera((100,-180,175),(60,-22,2),190)
render("01-integrated-arm.png")

# A close view of the actual junction, with the existing screw seated.
cap.rotation_euler.x=math.pi;cap.location=(0,0,18.9)
camera((32,-58,36),(3,0,9),55)
render("02-hub-and-cap.png")

# Crop only the display copy of the arm and cut a section through its hub.
# Rotate both parts equally to keep the section away from the pilot slots.
arm.hide_render=True;cap.hide_render=True
load_path(section("spool-arm-integrated-thimble-plus2mm-prototype-02.stl",""),TEAL)
load_path(section("reel-retaining-screw-30mm-prototype-01.stl",
                  "translate([0,0,18.9]) rotate([180,0,0])"),ORANGE)
camera((15,-60,36),(1,0,8),52)
render("03-integrated-section.png")
