#!/usr/bin/env python3
"""Export paste Gerbers from the U1-only master and retain raw CAD PnP data."""
import csv
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from sexpr import parse,emit,ch,one

root=Path(__file__).resolve().parents[1]
order=root
name="feeder-rev12cd-panel3"
board=root/(name+".kicad_pcb")
source=parse(board.read_text())
assembly=order/"assembly"
assembly.mkdir(exist_ok=True)


def ref(f):
    return next(p[2] for p in ch(f,"property") if p[1]=="Reference")


def prop(f,key):
    return next((str(p[2]) for p in ch(f,"property") if p[1]==key),"")


def dnp(f):
    return "dnp" in (one(f,"attr") or [])


removed=[ref(f) for f in ch(source,"footprint") if dnp(f)]
assert not removed, "The U1-only design should have no alternate DNP MCU"
assert not any(ref(f).endswith("_U2") for f in ch(source,"footprint"))
cli=shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
subprocess.run([cli,"pcb","export","gerbers","--output",str(order/"gerbers"),"--layers","F.Paste,B.Paste","--precision","6",str(board)],check=True)
for p in (order/"gerbers").glob("*.gbrjob"):
    p.unlink()

catalog=[]
fiducials=[]
paste_counts={"front":0,"back":0}
for f in ch(source,"footprint"):
    reference=ref(f)
    if reference=="MB1":continue
    local=reference.split("_",1)[1]
    index=int(reference[1])
    at=one(f,"at");x,y=float(at[1]),float(at[2]);rotation=float(at[3]) if len(at)>3 else 0
    side="top" if one(f,"layer")[1]=="F.Cu" else "bottom"
    attrs=one(f,"attr") or []
    row=dict(reference=reference,unit=index,unit_reference=local,value=prop(f,"Value"),footprint=str(f[1]),
             x_mm=x,y_mm=y,kicad_rotation_deg=rotation,side=side,dnp=dnp(f),
             smd="smd" in attrs,datasheet=prop(f,"Datasheet"),
             assembly_note=("Choose D1 or D3 LED option before programming" if local in ("D1","D3") else "Optional SWD programming header; confirm population" if local in ("J1","J9") else ""))
    catalog.append(row)
    if local.startswith("FID"):
        fiducials.append(dict(reference=reference,unit=index,x_mm=x,y_mm=y,side=side))
    if not row["dnp"]:
        for pad in ch(f,"pad"):
            layers=one(pad,"layers") or []
            paste_counts["front"] += "F.Paste" in layers
            paste_counts["back"] += "B.Paste" in layers

(assembly/"component-catalog-cad.json").write_text(json.dumps(catalog,indent=2)+"\n")
placements=[r for r in catalog if r["smd"] and not r["dnp"] and not r["unit_reference"].startswith(("FID","TP","G","REF"))]
columns=["reference","unit","unit_reference","value","footprint","x_mm","y_mm","kicad_rotation_deg","side","assembly_note"]
with (assembly/"panel-smd-placement-cad.csv").open("w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=columns,extrasaction="ignore",lineterminator="\n");w.writeheader();w.writerows(sorted(placements,key=lambda r:r["reference"]))

geometry=json.loads((root/"panel-geometry.json").read_text())
unit_bounds=[min(p[0] for p in geometry["unit_outline"]),min(p[1] for p in geometry["unit_outline"])]
layout=dict(panel_mm=geometry["panel_mm"],columns=3,rows=1,pitch_x_mm=59.0,panel_origin="top-left outer panel corner",
            cad_coordinates="Millimeters; X right, Y down; stored rotation is KiCad footprint rotation, not calibrated machine rotation",
            gerber_coordinates="Same physical origin; Gerber Y is negative CAD Y; no manual bottom mirroring applied",
            units=[dict(unit=i,reference_prefix=f"P{i}_",source_translation_mm=offset,
                        outline_bounding_box_top_left_mm=[unit_bounds[0]+offset[0],unit_bounds[1]+offset[1]],rotation_deg=0) for i,offset in enumerate(geometry["offsets_mm"],1)],
            existing_board_fiducials=fiducials,frame_tooling_holes=False,frame_fiducials=False,
            dnp_references=removed,assembly_choices_pending=["D1 versus D3 LED footprint", "Populate J1/J9 SWD headers or leave as programming contacts"],
            machine_setup_pending=["Package/nozzle and feeder assignments", "Camera/board alignment", "Top/bottom orientation mapping", "Per-package rotation and pickup corrections", "Part heights", "Dry run and first-board verification"],
            pcb_sha256=hashlib.sha256(board.read_bytes()).hexdigest())
(assembly/"panel-layout-and-machine-handoff.json").write_text(json.dumps(layout,indent=2)+"\n")
stencil_info=dict(panel_mm=geometry["panel_mm"],alignment="1:1 panel coordinates shared with copper, mask and drill files",
                  included_in_pcb_upload_zip=True,front_file=name+"-F_Paste.gtp",back_file=name+"-B_Paste.gbp",
                  omitted_dnp=removed,front_paste_pad_count=paste_counts["front"],back_paste_pad_count=paste_counts["back"],
                  preserved_optional_footprints=["D1","D3","J1","J9"],
                  recommended_manual_stencil=dict(side="Top",type="Frameless",thickness_mm=.10,custom_sheet_mm=[244,164],
                  panel_margin_each_side_mm=30,model_example="380 x 280 mm model with 290 x 190 mm valid area",fiducials="None",quantity=1),
                  bottom_note="Bottom paste is only the three J1 programming headers, 30 apertures total. Order Bottom separately only if needed.",
                  aperture_policy="Use supplied paste layers; do not recreate apertures from solder mask. Retain original pad aperture geometry; no production-file confirmation requested.")
(assembly/"stencil-settings.json").write_text(json.dumps(stencil_info,indent=2)+"\n")

(order/"validation/stencil-export.json").write_text(json.dumps(dict(omitted_dnp=removed,paste_pad_counts=paste_counts,placement_candidates=len(placements),electrical_master_sha256=layout["pcb_sha256"]),indent=2)+"\n")
print(json.dumps(dict(paste_pads=paste_counts,omitted_dnp=removed,placement_candidates=len(placements)),indent=2))
