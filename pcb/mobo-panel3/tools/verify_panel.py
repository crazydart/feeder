#!/usr/bin/env python3
"""Run with KiCad's bundled Python after filling zones and running DRC."""
import collections
import json
import uuid
from pathlib import Path
import pcbnew as k
import wx

app = wx.App(False)
root = Path(__file__).resolve().parents[1]
order = root
src = k.LoadBoard(str(root.parent / "mobo/mobo.kicad_pcb"))
panel = k.LoadBoard(str(root / "feeder-rev12cd-panel3.kicad_pcb"))
geo = json.loads((root / "panel-geometry.json").read_text())
ns = uuid.UUID("dc167c71-3e6f-47c9-acb7-fc4998478284")


def translated(p, offset):
    return tuple(int(a)+int(round(b*1000000)) for a,b in zip(p, offset))


def new_id(obj, prefix):
    return str(uuid.uuid5(ns, prefix + obj.m_Uuid.AsString()))


def net(name, prefix):
    return prefix + "/" + name if name else ""


tracks = {t.m_Uuid.AsString(): t for t in panel.GetTracks()}
footprints = {f.m_Uuid.AsString(): f for f in panel.GetFootprints() if f.GetReference() != "MB1"}
mousebites = next(f for f in panel.GetFootprints() if f.GetReference() == "MB1")
assert len(list(mousebites.Pads())) == 144
assert all(p.GetAttribute() == k.PAD_ATTRIB_NPTH and tuple(p.GetDrillSize()) == (600000,600000) for p in mousebites.Pads())
assert len(tracks) == len(list(src.GetTracks())) * 3
assert len(footprints) == len(list(src.GetFootprints())) * 3
pad_count = 0
for i, offset in enumerate(geo["offsets_mm"], 1):
    prefix = f"P{i}"
    for t in src.GetTracks():
        q = tracks[new_id(t, prefix)]
        assert tuple(q.GetStart()) == translated(t.GetStart(), offset)
        assert tuple(q.GetEnd()) == translated(t.GetEnd(), offset)
        assert q.GetNetname() == net(t.GetNetname(), prefix)
        assert tuple(q.GetLayerSet().Seq()) == tuple(t.GetLayerSet().Seq())
        if isinstance(t, k.PCB_VIA):
            assert isinstance(q, k.PCB_VIA)
            assert (q.GetWidth(k.F_Cu), q.GetDrillValue(), q.GetViaType()) == (t.GetWidth(k.F_Cu), t.GetDrillValue(), t.GetViaType())
        else:
            assert q.GetWidth() == t.GetWidth()
    for f in src.GetFootprints():
        q = footprints[new_id(f, prefix)]
        assert q.GetReference() == prefix + "_" + f.GetReference()
        assert q.GetValue() == f.GetValue()
        assert tuple(q.GetPosition()) == translated(f.GetPosition(), offset)
        assert q.GetOrientationDegrees() == f.GetOrientationDegrees()
        assert q.GetAttributes() == f.GetAttributes()
        pads = {p.m_Uuid.AsString(): p for p in q.Pads()}
        assert len(pads) == len(list(f.Pads()))
        for p in f.Pads():
            v = pads[new_id(p, prefix)]
            assert tuple(v.GetPosition()) == translated(p.GetPosition(), offset)
            assert v.GetNetname() == net(p.GetNetname(), prefix)
            assert v.GetNumber() == p.GetNumber()
            assert v.GetShape() == p.GetShape()
            assert v.GetAttribute() == p.GetAttribute()
            assert tuple(v.GetLayerSet().Seq()) == tuple(p.GetLayerSet().Seq())
            assert tuple(v.GetSize()) == tuple(p.GetSize())
            assert tuple(v.GetDrillSize()) == tuple(p.GetDrillSize())
            assert v.GetOrientationDegrees() == p.GetOrientationDegrees()
            pad_count += 1
drc = json.loads((order / "validation/drc.json").read_text())
counts = collections.Counter(v["type"] for v in drc["violations"])
assert not drc["unconnected_items"]
assert {v["type"] for v in drc["violations"] if v["severity"] == "error"} == {"starved_thermal", "courtyards_overlap"}
assert counts["starved_thermal"] == 9 and counts["courtyards_overlap"] == 3
for issue in ("shorting_items", "clearance", "hole_clearance", "solder_mask_bridge", "invalid_outline"):
    assert counts[issue] == 0
report = dict(source="REV12CD: U2 and its dangling traces removed from upstream REV12",
              units=3, footprints=len(footprints), routing_items=len(tracks), pads=pad_count,
              component_positions_pad_geometry_tracks_vias_nets_unchanged=True,
              changes="Panel translations, unique CAD references and net namespaces, copper-pour setbacks at routed edges and tabs, original unit outline with tab routing, 144 NPTH breakaway holes and rail labeling",
              mousebite_holes=144, unconnected_items=0, drc_counts=dict(counts),
              inherited_errors={"starved_thermal":9,"courtyards_overlap":3})
(order / "validation/source-comparison.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))
