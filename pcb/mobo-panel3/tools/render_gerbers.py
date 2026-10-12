#!/usr/bin/env python3
"""Render fabrication Gerbers, including clear polarity, mask, drills and routing.

Run with: uv run --with gerbonara --with cairosvg --with pillow python render_gerbers.py ORDER_DIR
"""
import io
import math
import sys
from pathlib import Path
import cairosvg
from gerbonara import LayerStack
from PIL import Image, ImageChops, ImageDraw, ImageFont

root = Path(sys.argv[1])
s = LayerStack.open(root / "gerbers")
bounds = s.board_bounds()
(x0, y0), (x1, y1) = bounds
w, h = x1-x0, y1-y0
scale = 24
size = round(w*scale), round(h*scale)


def raster(svg):
    return Image.open(io.BytesIO(cairosvg.svg2png(bytestring=str(svg).encode(), output_width=size[0], output_height=size[1]))).convert("RGB").convert("L")


def layer(file):
    return raster(file.to_svg(force_bounds=bounds, fg="white", bg="black"))


# Gerbonara's outline stitcher repeats the first arc when closing two-arc
# circles. Under even-odd fill that cancels half the hole. Render those paired
# semicircles explicitly, using only geometry from the actual Gerber.
circle_groups = {}
for o in s.outline.objects:
    if type(o).__name__ == "Arc":
        cx, cy = o.x1 + o.cx, o.y1 + o.cy
        radius = math.hypot(o.cx, o.cy)
        if math.hypot(o.x2 - (2*cx-o.x1), o.y2 - (2*cy-o.y1)) < 1e-5:
            circle_groups.setdefault((round(cx, 5), round(cy, 5), round(radius, 5)), []).append(o)
circles = {key: group for key, group in circle_groups.items() if len(group) == 2}
original_objects = s.outline.objects
circle_ids = {id(o) for group in circles.values() for o in group}
s.outline.objects = [o for o in original_objects if id(o) not in circle_ids]
path = s.outline_svg_d()
s.outline.objects = original_objects
for (cx, cy, radius) in circles:
    path += f" M {cx+radius} {cy} A {radius} {radius} 0 1 1 {cx-radius} {cy} A {radius} {radius} 0 1 1 {cx+radius} {cy} Z"
outline_svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}mm" height="{h}mm" viewBox="{x0} {y0} {w} {h}"><rect x="{x0}" y="{y0}" width="{w}" height="{h}" fill="black"/><g transform="translate(0 {y0+y1}) scale(1 -1)"><path fill="white" fill-rule="evenodd" d="{path}"/></g></svg>'
material = raster(outline_svg)
drill = Image.new("L", size, 0)
for f in s.drill_layers:
    drill = ImageChops.lighter(drill, layer(f))
material = ImageChops.subtract(material, drill)
views = []
for side in ("top", "bottom"):
    copper, openings, silk = [layer(s[(side, use)]) for use in ("copper", "mask", "silk")]
    image = Image.new("RGB", size, "#f0f2f4")
    image.paste("#25292b", (0, 0), material)
    image.paste("#313537", (0, 0), ImageChops.multiply(copper, material))
    image.paste("#a29775", (0, 0), ImageChops.multiply(openings, material))
    exposed = ImageChops.multiply(ImageChops.multiply(copper, openings), material)
    image.paste("#d8b760", (0, 0), exposed)
    image.paste("#fafaf2", (0, 0), ImageChops.multiply(silk, material))
    if side == "bottom":
        image = image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
    image.save(root / f"{side}-gerber-preview.png")
    views.append(image)
# Display-only orientation for the assembled feeder; fabrication coordinates
# and the CAD-oriented images used by the tab/stencil overlays remain intact.
views[1].transpose(Image.Transpose.ROTATE_180).save(root / "back-installed-preview.png")
margin = 36
canvas = Image.new("RGB", (2*size[0]+3*margin, size[1]+100), "#f0f2f4")
draw = ImageDraw.Draw(canvas)
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 26)
except OSError:
    font = ImageFont.load_default()
for n, (view, label) in enumerate(zip(views, ["FRONT", "BACK (viewed from back)"])):
    xx = margin+(size[0]+margin)*n
    draw.text((xx, 15), label, fill="#293238", font=font)
    canvas.paste(view, (xx, 60))
canvas.save(root / "gerber-preview.png")
print(root, "bounds", bounds, "PTH", len(s.drill_pth.objects) if s.drill_pth else 0, "NPTH", len(s.drill_npth.objects) if s.drill_npth else 0)
