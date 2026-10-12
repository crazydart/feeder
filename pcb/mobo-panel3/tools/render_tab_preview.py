#!/usr/bin/env python3
"""Annotate the actual Gerber preview; render paste aligned with PCB copper.

Run render_gerbers.py ORDER_DIR first. Requires Pillow, Gerbonara and CairoSVG.
"""
import io
import json
from pathlib import Path
import cairosvg
from gerbonara import GerberFile, LayerStack
from PIL import Image, ImageDraw, ImageFont

root = Path(__file__).resolve().parents[1]
order = root
geometry = json.loads((root / "panel-geometry.json").read_text())
bounds = json.loads((root / "component-bounds.json").read_text())
stack = LayerStack.open(order / "gerbers")
board_bounds = stack.board_bounds()
(x0, y0), (x1, y1) = board_bounds
base = Image.open(order / "top-gerber-preview.png").convert("RGB")
sx, sy = base.width / (x1 - x0), base.height / (y1 - y0)
crop_width = round(65.5 * sx)
header = 180


def font(size):
    return ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", size)


def pixel(x, y):
    return (x - x0) * sx, (y + y1) * sy + header


def canvas(title, subtitle, image):
    result = Image.new("RGB", (crop_width, base.height + header), "#24282b")
    result.paste(image.crop((0, 0, crop_width, base.height)), (0, header))
    d = ImageDraw.Draw(result)
    d.text((32, 24), title, font=font(48), fill="white")
    d.text((32, 94), subtitle, font=font(31), fill="#d9e0e4")
    return result, d


image, draw = canvas("REV12CD panel — six tabs per board", "Green: drilled tabs     Orange: edge connectors and buttons", base)
green, orange = "#25d59c", "#ffb347"
dx, dy = geometry["offsets_mm"][0]
for fp in bounds:
    if fp["reference"] not in ("J3", "J4", "J5", "J6", "J7", "J8"):
        continue
    left, top, right, bottom = fp["bbox_mm"]
    draw.rectangle((*pixel(left+dx-.3, top+dy-.3), *pixel(right+dx+.3, bottom+dy+.3)), outline=orange, width=4)
    draw.text(pixel(left+dx, top+dy-1.9), fp["reference"], font=font(29), fill=orange, stroke_width=1, stroke_fill="#24282b")
for i, tab in enumerate(geometry["tabs"][:6], 1):
    x, y = tab["center_mm"]
    a, b = (2.5, 4.2) if tab["normal"][0] else (4.2, 2.5)
    draw.rectangle((*pixel(x-a,y-b), *pixel(x+a,y+b)), outline=green, width=6)
    text = f"T{i}" + (" NEW" if i > 4 else "")
    label_x = x-a if i != 4 else x-a-.4
    label_y = y-b-2.0 if i != 5 else y+b+.25
    draw.text(pixel(label_x, label_y), text, font=font(31), fill=green, stroke_width=1, stroke_fill="#24282b")
image.save(order / "tab-placement-preview.png")

paste = GerberFile.open(next((order / "gerbers").glob("*.gtp")))
svg = paste.to_svg(force_bounds=board_bounds, fg="white", bg="black")
mask = Image.open(io.BytesIO(cairosvg.svg2png(bytestring=str(svg).encode(), output_width=base.width, output_height=base.height))).convert("L")
overlay = base.copy()
overlay.paste("#29e8ef", (0,0), mask)
image, draw = canvas("Top stencil — aligned with PCB copper", "Cyan: actual paste apertures; U2 removed. Same layout on all 3 boards.", overlay)
image.save(order / "stencil-alignment-preview.png")
print("Saved tab-placement-preview.png and stencil-alignment-preview.png")
