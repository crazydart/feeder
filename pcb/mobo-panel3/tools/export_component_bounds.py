#!/usr/bin/env python3
"""Refresh footprint bounds with KiCad's Python before building the panel."""
import json
from pathlib import Path
import pcbnew as k
import wx

app = wx.App(False)
root = Path(__file__).resolve().parents[1]
board = k.LoadBoard(str(root.parent / "mobo/mobo.kicad_pcb"))
rows = []
for f in board.GetFootprints():
    r = f.GetBoundingBox(False, False)
    rows.append(dict(reference=f.GetReference(), value=f.GetValue(),
                     bbox_mm=[k.ToMM(r.GetX()), k.ToMM(r.GetY()), k.ToMM(r.GetRight()), k.ToMM(r.GetBottom())]))
(root / "component-bounds.json").write_text(json.dumps(rows, indent=2) + "\n")
print(f"Saved bounds for {len(rows)} source footprints")
