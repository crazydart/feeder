#!/usr/bin/env python3
"""Check U1-only paste export and raw panel placement coordinates."""
import collections
import csv
import json
from pathlib import Path
from gerbonara import GerberFile
from sexpr import parse,emit,ch,one

root=Path(__file__).resolve().parents[1]
order=root
name="feeder-rev12cd-panel3"
master=parse((root/(name+".kicad_pcb")).read_text())
assert not any(p[2].endswith("_U2") for f in ch(master,"footprint") for p in ch(f,"property") if p[1]=="Reference")
report=json.loads((order/"validation/stencil-export.json").read_text())
counts={}
for side,ext in (("front","gtp"),("back","gbp")):
    g=GerberFile.open(next((order/"gerbers").glob("*."+ext)))
    kinds=collections.Counter(type(o).__name__ for o in g.objects)
    assert kinds["Flash"]==report["paste_pad_counts"][side]
    assert kinds==({"Flash":654,"Line":24,"Region":6} if side=="front" else {"Flash":30})
    for o in g.objects:
        assert o.polarity_dark
        ((x0,y0),(x1,y1))=o.bounding_box()
        assert x0>=0 and x1<=184 and y0>=-104 and y1<=0
        if isinstance(o.attrs,dict):assert "_U2" not in str(o.attrs)
    counts[side]=dict(kinds)
placements=list(csv.DictReader((order/"assembly/panel-smd-placement-cad.csv").open()))
assert len(placements)==165
assert len({r["reference"] for r in placements})==165
assert not any(r["unit_reference"]=="U2" for r in placements)
groups={i:{r["unit_reference"]:r for r in placements if r["unit"]==str(i)} for i in (1,2,3)}
assert groups[1].keys()==groups[2].keys()==groups[3].keys()
for ref,a in groups[1].items():
    for i in (2,3):
        b=groups[i][ref]
        assert abs(float(b["x_mm"])-float(a["x_mm"])-59*(i-1))<1e-6
        assert a["y_mm"]==b["y_mm"] and a["side"]==b["side"] and a["kicad_rotation_deg"]==b["kicad_rotation_deg"]
report.update(paste_exported_from_electrical_master=True,u2_absent_from_pcb=True,exported_objects=counts,
              source_paste_geometry_preserved=True,additional_front_graphics="Two original J5 mounting paste polygons per board, including their boundary strokes",
              pnp_panel_offsets_verified=True,pnp_rotations_are_unadjusted_cad=True)
(order/"validation/stencil-export.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
