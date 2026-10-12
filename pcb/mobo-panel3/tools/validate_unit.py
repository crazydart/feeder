#!/usr/bin/env python3
"""Compare REV12CD against the recorded upstream PCB and schematic netlist.

Run from a Git checkout. Uses standard Python and kicad-cli.
"""
import collections
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path
from sexpr import parse, ch, one

root = Path(__file__).resolve().parents[1]
repo = root.parents[1]
report_path = root / "validation/u2-removal.json"
report = json.loads(report_path.read_text())
baseline = report["upstream_commit"]
cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"


def original(path):
    return subprocess.check_output(["git", "show", f"{baseline}:{path}"], cwd=repo, text=True)


def uid(n):
    return str(one(n, "uuid")[1])


def reference(f):
    return next(p[2] for p in ch(f, "property") if p[1] == "Reference")


def canonical(n, nets):
    if isinstance(n, list):
        if n and n[0] == "net":
            name = str(n[-1])
            return ["net", nets.get(name, name)]
        return [canonical(x, nets) for x in n]
    if isinstance(n, str):
        try:
            return float(n)
        except ValueError:
            return str(n)
    return n


old = parse(original("pcb/mobo/mobo.kicad_pcb"))
new = parse((root.parent / "mobo/mobo.kicad_pcb").read_text())
old_nets = {str(n[1]): str(n[2]) for n in ch(old, "net")}
removed = {x["uuid"] for x in report["removed_footprints"]}
a = {uid(f): f for f in ch(old, "footprint") if uid(f) not in removed}
b = {uid(f): f for f in ch(new, "footprint")}
assert a.keys() == b.keys()
assert "U2" not in [reference(f) for f in b.values()]
pad_count = 0
for key, f in a.items():
    g = b[key]
    assert f[1] == g[1]
    assert canonical(one(f, "at"), {}) == canonical(one(g, "at"), {})
    assert reference(f) == reference(g) or (reference(f) == "REF**" and reference(g) == "GFX1")
    ap = {uid(p): p for p in ch(f, "pad")}
    bp = {uid(p): p for p in ch(g, "pad")}
    assert ap.keys() == bp.keys()
    for key, p in ap.items():
        q = bp[key]
        assert p[:4] == q[:4]
        for field in ("at", "size", "drill", "layers", "net", "roundrect_rratio", "thermal_bridge_angle", "chamfer_ratio", "chamfer"):
            assert canonical(one(p, field), old_nets) == canonical(one(q, field), {}), (reference(f), p[1], field)
        pad_count += 1
before = {uid(n): n for n in old if isinstance(n, list) and n[0] in ("segment", "via")}
after = {uid(n): n for n in new if isinstance(n, list) and n[0] in ("segment", "via")}
assert before.keys() - after.keys() == {x["uuid"] for x in report["removed_dangling_track_segments"]}
for key, n in after.items():
    previous = before[key]
    assert previous[0] == n[0]
    for field in ("start", "end", "at", "width", "size", "drill", "layer", "layers", "net", "remove_unused_layers", "keep_end_layers", "free"):
        assert canonical(one(previous, field), old_nets) == canonical(one(n, field), {}), (key, field, "remaining routing changed")
    # KiCad 10 explicitly serializes the previously implicit unfilled-via defaults.
    for field in ("capping", "filling"):
        setting = one(n, field)
        assert setting is None or setting[1] == "no"


def connections(netlist, exclude):
    result = {}
    for n in netlist.findall("nets/net"):
        pins = sorted((p.attrib["ref"], p.attrib["pin"]) for p in n.findall("node") if p.attrib["ref"] not in exclude)
        if pins:
            result[n.attrib["name"]] = pins
    return result


def components(netlist):
    return {c.attrib["ref"]: (c.findtext("value"), c.findtext("footprint")) for c in netlist.findall("components/comp")}


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)
    old_sch = tmp / "upstream.kicad_sch"
    old_sch.write_text(original("pcb/mobo/mobo.kicad_sch"))
    paths = []
    for label, sch in (("before", old_sch), ("after", root.parent / "mobo/mobo.kicad_sch")):
        path = tmp / (label + ".xml")
        subprocess.run([cli, "sch", "export", "netlist", "--format", "kicadxml", "--output", str(path), str(sch)], check=True)
        paths.append(ET.parse(path).getroot())
    old_schematic, new_schematic = paths
    expected_components = components(old_schematic)
    expected_components.pop("U2")
    assert expected_components == components(new_schematic)
    assert connections(old_schematic, {"U2"}) == connections(new_schematic, set())

drc = json.loads((root / "validation/unit-drc.json").read_text())
assert not drc["unconnected_items"] and not drc.get("schematic_parity", [])
counts = collections.Counter(v["type"] for v in drc["violations"])
assert counts["starved_thermal"] == 3 and counts["courtyards_overlap"] == 1
assert {v["type"] for v in drc["violations"] if v["severity"] == "error"} == {"starved_thermal", "courtyards_overlap"}
assert not counts["track_dangling"]
report.update(remaining_schematic_components_unchanged=True, remaining_schematic_pin_net_mapping_unchanged=True,
              remaining_pcb_pads_unchanged=True, remaining_pcb_footprint_locations_unchanged=True,
              remaining_tracks_and_vias_unchanged=True, remaining_footprints=len(b), remaining_pads=pad_count,
              remaining_tracks_and_vias=len(after), schematic_parity_issues=0, drc_counts=dict(counts))
report_path.write_text(json.dumps(report, indent=2) + "\n")
print(f"Unit comparison PASS: {len(b)} footprints, {pad_count} pads, {len(after)} remaining tracks/vias unchanged; schematic parity clean")
