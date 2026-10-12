#!/usr/bin/env python3
"""Three REV12CD motherboards, 184 x 104 mm, full routing and six mouse-bite tabs per board.

Run with Python 3 and Shapely 2.x, then refill zones with KiCad CLI.
Source units retain all footprints/pads, traces, vias, mechanical holes.
Each circuit gets its own net namespace. Source reference labels are retained
as explicit silk text while CAD references become unique per circuit.
"""
import copy
import json
import math
import uuid
from pathlib import Path
from shapely.geometry import LineString, Polygon, Point, box
from shapely.ops import polygonize, unary_union
from shapely.affinity import translate
from sexpr import parse, emit, ch, one, Atom as A

ROOT = Path(__file__).resolve().parents[1]
NAME = "feeder-rev12cd-panel3"
NS = uuid.UUID("dc167c71-3e6f-47c9-acb7-fc4998478284")
OFFSETS = [(-92.7 + i*59, -22.3) for i in range(3)]
TABS = [(102.3,62,-1,0), (151.3,62,1,0), (101.3,96,-1,0), (151.3,96,1,0), (140.5,29.8,0,-1), (131.0,118.8,0,1)]
PORT_HALF = 3.8
HOLE_DIAMETER = .6
HOLE_PITCH = 1.0


def uid(s):
    return str(uuid.uuid5(NS, s))


def poly_node(points):
    return [A("polygon"), [A("pts")] + [[A("xy"), round(x,6), round(y,6)] for x,y in points]]


def arc_points(n):
    a, m, b = [tuple(map(float, one(n, k)[1:3])) for k in ("start","mid","end")]
    (ax,ay),(mx,my),(bx,by) = a,m,b
    d = 2*(ax*(my-by)+mx*(by-ay)+bx*(ay-my))
    cx = ((ax*ax+ay*ay)*(my-by)+(mx*mx+my*my)*(by-ay)+(bx*bx+by*by)*(ay-my))/d
    cy = ((ax*ax+ay*ay)*(bx-mx)+(mx*mx+my*my)*(ax-bx)+(bx*bx+by*by)*(mx-ax))/d
    radius = math.hypot(ax-cx, ay-cy)
    start,mid,end = [math.atan2(y-cy,x-cx) for x,y in (a,m,b)]
    turn = (end-start) % (2*math.pi)
    if (mid-start) % (2*math.pi) > turn:
        turn -= 2*math.pi
    steps = max(2, math.ceil(abs(turn)*radius/.04))
    return [a]+[(cx+radius*math.cos(start+turn*i/steps),cy+radius*math.sin(start+turn*i/steps)) for i in range(1,steps)]+[b]


def move_xy(n, dx, dy, keys=("at","start","end","mid","center","xy")):
    if isinstance(n,list):
        if n and n[0] in keys:
            n[1],n[2] = round(float(n[1])+dx,6),round(float(n[2])+dy,6)
        else:
            for v in n:
                move_xy(v,dx,dy,keys)


def namespace(n, label):
    if isinstance(n,list):
        if n and n[0] == "uuid":
            n[1] = uid(label+str(n[1]))
        elif n and n[0] == "net" and len(n) == 2 and n[1]:
            n[1] = label+"/"+str(n[1])
        for item in n:
            namespace(item,label)


def main():
    src = parse((ROOT.parent/"mobo/mobo.kicad_pcb").read_text())
    edge_shapes = [n for n in src if isinstance(n,list) and n[0] in ("gr_line","gr_arc") and one(n,"layer")[1] == "Edge.Cuts"]
    lines = []
    for n in edge_shapes:
        points = arc_points(n) if n[0]=="gr_arc" else [list(map(float,one(n,k)[1:3])) for k in ("start","end")]
        lines.append(LineString(points))
    outlines = list(polygonize(unary_union(lines)))
    assert len(outlines)==1 and outlines[0].is_valid
    unit = outlines[0]
    route_paths=[]
    hole_points=[]
    tabs=[]
    for board_index,(dx,dy) in enumerate(OFFSETS,1):
        shape=translate(unit,dx,dy)
        path=shape.buffer(1,quad_segs=32).exterior
        for x,y,nx,ny in TABS:
            # Interrupt the 2 mm router centerline. Rounded tool ends leave
            # a 5.6 mm minimum neck and 7.6 mm at the original board edge.
            cx,cy=x+nx+dx,y+ny+dy
            tx,ty=-ny,nx
            path=path.difference(box(cx-abs(tx)*PORT_HALF-abs(nx)*.001,cy-abs(ty)*PORT_HALF-abs(ny)*.001,cx+abs(tx)*PORT_HALF+abs(nx)*.001,cy+abs(ty)*PORT_HALF+abs(ny)*.001))
            row=[[round(x+dx+(j-3.5)*HOLE_PITCH*tx,6),round(y+dy+(j-3.5)*HOLE_PITCH*ty,6)] for j in range(8)]
            hole_points.extend(row)
            tabs.append(dict(board=board_index,source_center_mm=[x,y],normal=[nx,ny],center_mm=[x+dx,y+dy],holes_mm=row))
        route_paths.append(path)
    routed=unary_union([p.buffer(1,quad_segs=32) for p in route_paths]).simplify(.002,preserve_topology=True)
    outer=box(0,0,184,104)
    material=outer.difference(routed)
    assert material.is_valid and material.geom_type=="Polygon", "Disconnected panel material"
    drilled=material.difference(unary_union([Point(x,y).buffer(.3,quad_segs=32) for x,y in hole_points]))
    assert drilled.is_valid and drilled.geom_type=="Polygon", "Panel must stay connected after drilling"
    for dx,dy in OFFSETS:
        assert translate(unit,dx,dy).difference(material).area < .1

    out=[A("kicad_pcb")]
    for key in ("version","generator","generator_version","general","paper","layers","setup"):
        out.append(copy.deepcopy(one(src,key)))
    setup=one(out,"setup")
    one(one(setup,"stackup"),"copper_finish")[1]="ENIG"
    one(one(setup,"pcbplotparams"),"outputdirectory")[1]=""
    out.append(parse('(title_block (title "Feeder REV12CD - three-board routed panel") (rev "REV12CD") (comment 1 "184 x 104 x 1.6 mm; 18 tabs, 144 x 0.6 mm NPTH") (comment 2 "Side tabs plus top and bottom tabs at requested positions; original unit outline"))'))
    items={"footprint","segment","via","gr_line","gr_arc","gr_circle","gr_rect","gr_text","gr_poly","zone"}
    unit_items=[]
    for index,(dx,dy) in enumerate(OFFSETS,1):
        label=f"P{index}"
        for original in src:
            if not isinstance(original,list) or original[0] not in items:
                continue
            if original in edge_shapes:
                continue
            n=copy.deepcopy(original)
            if n[0]=="footprint":
                at=one(n,"at")
                at[1],at[2]=round(float(at[1])+dx,6),round(float(at[2])+dy,6)
                ref=next(p for p in ch(n,"property") if p[1]=="Reference")
                old_ref=ref[2]
                if not one(ref,"hide"):
                    # Preserve exact plotted reference text while keeping unique CAD refs.
                    text=[A("fp_text"),A("user"),old_ref]+copy.deepcopy(ref[3:])
                    one(text,"uuid")[1]=uid(label+"reftext"+old_ref+str(one(n,"uuid")[1]))
                    n.append(text)
                    ref.append([A("hide"),A("yes")])
                ref[2]=label+"_"+old_ref
            elif n[0]=="zone":
                # Limit pours to the original unit silhouette when the frame is refilled.
                # Keep poured copper 0.2 mm off routed edges and 1 mm back at tabs.
                n=[v for v in n if not (isinstance(v,list) and v[0] in ("polygon","filled_polygon"))]
                clipped=unit.buffer(-.2,quad_segs=32)
                for tx,ty,nx,ny in TABS:
                    hx,hy=(1,4.5) if nx else (4.5,1)
                    clipped=clipped.difference(box(tx-hx,ty-hy,tx+hx,ty+hy))
                assert clipped.geom_type=="Polygon"
                n.append(poly_node(list(clipped.exterior.coords)[:-1]))
                move_xy(n,dx,dy)
            else:
                move_xy(n,dx,dy)
            namespace(n,label)
            out.append(n)
            unit_items.append(n)

    def edge(a,b,name):
        out.append(parse(f'(gr_line (start {a[0]:.6f} {a[1]:.6f}) (end {b[0]:.6f} {b[1]:.6f}) (stroke (width 0.05) (type solid)) (layer "Edge.Cuts") (uuid "{uid(name)}"))'))

    for label,loop in [("outer",list(material.exterior.coords))]+[(f"route{i}",list(p.coords)) for i,p in enumerate(material.interiors)]:
        for j,(a,b) in enumerate(zip(loop,loop[1:])):
            edge(a,b,label+str(j))
    holes=parse(f'(footprint "PanelMouseBites" (layer "F.Cu") (at 0 0) (uuid "{uid("mousebites")}") (property "Reference" "MB1" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness .15)))) (property "Value" "144 x 0.6 mm NPTH" (at 0 0) (layer "F.Fab") (hide yes) (effects (font (size 1 1) (thickness .15)))) (attr board_only exclude_from_pos_files exclude_from_bom))')
    for i,(x,y) in enumerate(hole_points):
        holes.append(parse(f'(pad "" np_thru_hole circle (at {x:.6f} {y:.6f}) (size .6 .6) (drill .6) (layers "*.Cu" "*.Mask") (uuid "{uid("hole"+str(i))}"))'))
    out.append(holes)
    for label,y in [("FEEDER REV12CD / 3 x 1 / SIX TABS EACH / U1 ONLY",2.5),("184 x 104 mm / 1.6 mm / 144 x 0.6 mm NPTH",101.5)]:
        out.append(parse(f'(gr_text "{label}" (at 92 {y}) (layer "F.SilkS") (uuid "{uid(label)}") (effects (font (size 1 1) (thickness .15))))'))
    (ROOT/f"{NAME}.kicad_pcb").write_text(emit(out)+"\n")
    project=json.loads((ROOT.parent/"mobo/mobo.kicad_pro").read_text())
    project["board"]["design_settings"]["drc_exclusions"]=[]
    project["board"]["design_settings"]["rules"]["min_copper_edge_clearance"]=.2
    (ROOT/f"{NAME}.kicad_pro").write_text(json.dumps(project,indent=2)+"\n")
    geo=dict(panel_mm=[184,104,1.6],columns=3,rows=1,offsets_mm=OFFSETS,unit_outline=list(unit.exterior.coords),
             panel_cutouts=[list(p.coords) for p in material.interiors],mousebite_centers_mm=hole_points,tabs=tabs,
             router_diameter_mm=2,mousebite_count=len(hole_points),hole_diameter_mm=.6,hole_pitch_mm=1.0,
             tab_minimum_neck_mm=5.6,tab_width_at_board_edge_mm=7.6,tab_count=18,
             vcut_y_mm=[],vcut_x_mm=[],zone_setback_at_tab_mm=1.0,zone_setback_at_route_mm=.2,
             original_unit_outline=True,minimum_outer_rail_mm=5.0,connected_before_breaking=True)
    (ROOT/"panel-geometry.json").write_text(json.dumps(geo,indent=2)+"\n")
    print(f"Built {NAME}: 184 x 104 mm, {len(material.interiors)} routing cutouts, 18 tabs, {len(hole_points)} mouse-bite holes")



if __name__=="__main__":
    main()
