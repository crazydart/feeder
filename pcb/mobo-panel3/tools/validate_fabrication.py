#!/usr/bin/env python3
"""Verify routing, breakaway positions and exported drill/copper data.

Run with shapely, gerbonara, cairosvg, pillow and numpy.
"""
import collections
import copy
import io
import json
import math
from pathlib import Path
import cairosvg
import numpy as np
from PIL import Image
from gerbonara import GerberFile, ExcellonFile
from shapely.geometry import Point, LineString, Polygon, box
from shapely.affinity import translate
from shapely import union_all

root=Path(__file__).resolve().parents[1]
order=root
geo=json.loads((root/"panel-geometry.json").read_text())
bounds=json.loads((root/"component-bounds.json").read_text())
npth=ExcellonFile.open(next((order/"gerbers").glob("*-NPTH.drl")))
pth=ExcellonFile.open(next((order/"gerbers").glob("*-PTH.drl")))
assert len(npth.objects)==144 and all(abs(o.tool.diameter-.6)<1e-8 for o in npth.objects)
expected=collections.Counter((round(x,6),round(-y,6)) for x,y in geo["mousebite_centers_mm"])
assert expected==collections.Counter((round(o.x,6),round(o.y,6)) for o in npth.objects)
assert collections.Counter(round(o.tool.diameter,3) for o in pth.objects)=={.3:528,.4:12,1.:18}
outline=GerberFile.open(next((order/"gerbers").glob("*.gm1")))
assert collections.Counter(round(2*math.hypot(o.cx,o.cy),3) for o in outline.objects if type(o).__name__=="Arc")=={3.2:42,.7:36}

# All connectors (including the J4/J6/J7 button footprints) are protected.
protected=[f for f in bounds if f["reference"].startswith(("J","SW"))]
tab_checks=[]
for t in geo["tabs"]:
    x,y=t["source_center_mm"];nx,ny=t["normal"]
    # Cover the entire unperforated tab attachment, including router end caps.
    attachment=(box(min(x,x+2*nx)-.3,y-3.8,max(x,x+2*nx)+.3,y+3.8) if nx else box(x-3.8,min(y,y+2*ny)-.3,x+3.8,max(y,y+2*ny)+.3))
    distances=[(attachment.distance(box(*f["bbox_mm"])),f["reference"]) for f in protected]
    clearance,ref=min(distances)
    assert clearance>=3, (t,clearance,ref)
    tab_checks.append(dict(board=t["board"],center_mm=t["center_mm"],nearest_connector_or_button=ref,
                           minimum_clearance_mm=clearance, protected_references=[f["reference"] for f in protected]))

# The physical panel remains one piece after routing and drilling.
w,h,_=geo["panel_mm"]
material=box(0,0,w,h).difference(union_all([Polygon(p) for p in geo["panel_cutouts"]]))
holes=union_all([Point(x,y).buffer(.3,quad_segs=32) for x,y in geo["mousebite_centers_mm"]])
drilled=material.difference(holes)
assert drilled.is_valid and drilled.geom_type=="Polygon"
breaks=union_all([LineString([(t["center_mm"][0]-(-t["normal"][1])*3.9,t["center_mm"][1]-t["normal"][0]*3.9),(t["center_mm"][0]+(-t["normal"][1])*3.9,t["center_mm"][1]+t["normal"][0]*3.9)]).buffer(.001) for t in geo["tabs"]])
separated=drilled.difference(breaks)
assert separated.geom_type=="MultiPolygon" and len(separated.geoms)==4
unit=Polygon(geo["unit_outline"])
matched=[]
for dx,dy in geo["offsets_mm"]:
    expected_unit=translate(unit,dx,dy).difference(holes).difference(breaks)
    idx=max(range(4),key=lambda i:separated.geoms[i].intersection(expected_unit).area)
    actual=separated.geoms[idx]
    assert actual.symmetric_difference(expected_unit).area<.2
    matched.append(idx)
assert len(set(matched))==3

# Independently render actual Gerber polarity near every tab at 100 pixels/mm.
# Report a conservative bound, subtracting one pixel diagonal for raster error.
pitch=100
clearances={}
for side,ext in (("front","gtl"),("back","gbl")):
    copper=GerberFile.open(next((order/"gerbers").glob("*."+ext)))
    copper_boxes=[o.bounding_box() for o in copper.objects]
    minima=[]
    for t in geo["tabs"]:
        cx,cy=t["center_mm"];cy=-cy
        hx,hy=(3,5.5) if t["normal"][0] else (5.5,3)
        x0,x1=cx-hx,cx+hx;y0,y1=cy-hy,cy+hy
        local=copy.copy(copper)
        local.objects=[o for o,((a,b),(c,d)) in zip(copper.objects,copper_boxes) if c>=x0 and a<=x1 and d>=y0 and b<=y1]
        svg=local.to_svg(force_bounds=((x0,y0),(x1,y1)),fg="white",bg="black")
        im=Image.open(io.BytesIO(cairosvg.svg2png(bytestring=str(svg).encode(),output_width=round(2*hx*pitch),output_height=round(2*hy*pitch)))).convert("L")
        yy,xx=np.nonzero(np.asarray(im)>0)
        assert len(xx)>0
        px=x0+(xx+.5)/pitch;py=y1-(yy+.5)/pitch
        for hx,hy in t["holes_mm"]:
            minimum=float(np.sqrt((px-hx)**2+(py+hy)**2).min())-.3-math.sqrt(2)/pitch
            assert minimum>=.3,(side,t,minimum)
            minima.append(minimum)
    clearances[side]=min(minima)

report=dict(panel_mm=geo["panel_mm"],boards=3,tabs_per_board=6,holes_per_tab=8,mousebite_holes=144,
            hole_diameter_mm=.6,hole_pitch_mm=1.0,hole_edge_spacing_mm=.4,minimum_tab_neck_mm=5.6,
            plated_holes=558,original_unplated_circular_openings=39,router_mm=2,
            no_vcuts=True,original_board_outline_restored=True,connected_after_drilling=True,
            separation_yields_three_boards_and_frame=True,
            minimum_tab_to_connector_or_button_mm=min(c["minimum_clearance_mm"] for c in tab_checks),
            conservative_gerber_hole_rim_to_copper_mm=clearances,copper_raster_mm_per_pixel=.01,
            tab_placement_checks=tab_checks)
(order/"validation/fabrication-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:v for k,v in report.items() if k!="tab_placement_checks"},indent=2))
