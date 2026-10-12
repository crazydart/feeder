#!/usr/bin/env python3
"""Package the validated REV12CD panel, refresh the BOM and record checksums."""
import collections
import csv
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "feeder-rev12cd-panel3"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n")


master_sha = sha(ROOT / (NAME + ".kicad_pcb"))
layout = json.loads((ROOT / "assembly/panel-layout-and-machine-handoff.json").read_text())
stencil = json.loads((ROOT / "validation/stencil-export.json").read_text())
assert layout["pcb_sha256"] == master_sha
assert stencil["electrical_master_sha256"] == master_sha
assert stencil["u2_absent_from_pcb"] and stencil["pnp_panel_offsets_verified"]
members = sorted((ROOT / "gerbers").iterdir())
assert collections.Counter(p.suffix for p in members) == collections.Counter(
    [".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1", ".gtp", ".gbp", ".drl", ".drl"]
)
archive = ROOT / (NAME + "-jlcpcb.zip")
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
    for path in members:
        z.write(path, path.name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert z.namelist() == [p.name for p in members]
    for path in members:
        assert z.read(path.name) == path.read_bytes()

comment_lengths = {}
for doc, output in (("ORDER-NOTES.md", "ORDER-COMMENT.txt"), ("STENCIL-AND-PNP.md", "STENCIL-COMMENT.txt")):
    remark = next(line[2:] for line in (ROOT / doc).read_text().splitlines() if line.startswith("> "))
    assert len(remark) <= 200
    (ROOT / output).write_text(remark + "\n")
    comment_lengths[output] = len(remark)

catalog = json.loads((ROOT / "assembly/component-catalog-cad.json").read_text())
parts = [p for p in catalog if p["unit"] == 1 and not p["unit_reference"].startswith(("TP", "FID", "G", "REF"))]
assert len(parts) == 56 and all(p["unit_reference"] != "U2" for p in parts)
groups = collections.defaultdict(list)
for part in parts:
    groups[part["value"], part["footprint"], part["assembly_note"]].append(part["unit_reference"])
natural = lambda ref: [int(x) if x.isdigit() else x for x in re.split(r"(\d+)", ref)]
bom = ROOT.parent / "mobo/bom/rev12cd-bom.csv"
bom.parent.mkdir(exist_ok=True)
with bom.open("w", newline="") as f:
    writer = csv.writer(f, lineterminator="\n")
    writer.writerow(["References", "Value", "Footprint", "Quantity per board", "Quantity per 3-board panel", "Assembly note"])
    for (value, footprint, note), refs in sorted(groups.items()):
        writer.writerow([", ".join(sorted(refs, key=natural)), value, footprint, len(refs), 3 * len(refs), note])

write_json(ROOT / "validation/package-checks.json", {
    "revision": "REV12CD", "electrical_master_sha256": master_sha,
    "upload_members": [p.name for p in members], "paste_in_same_zip": True,
    "zip_integrity_verified": True, "comment_lengths": comment_lengths,
    "bom_groups": len(groups), "bom_candidate_parts_per_unit": len(parts),
})
files = {
    str(p.relative_to(ROOT)): sha(p)
    for p in sorted(ROOT.rglob("*"))
    if p.is_file() and p.name != "MANIFEST.json" and "__pycache__" not in p.parts
    and p.suffix not in (".pyc", ".kicad_prl", ".xml", ".gbrjob")
}
for name in (
    "../mobo/mobo.kicad_pcb", "../mobo/mobo.kicad_sch", "../mobo/mobo.kicad_pro",
    "../mobo/README.md", "../mobo/bom/rev12cd-bom.csv",
    "../mobo/artwork/README.md", "../mobo/artwork/robot-cat-white.svg",
    "../mobo/back-silkscreen-preview.png", "../mobo/front-silkscreen-preview.png",
    "../../lib/kicad/index.pretty/MHS110FRGBCT.kicad_mod",
):
    files[name] = sha(ROOT / name)
write_json(ROOT / "MANIFEST.json", {"algorithm": "SHA256", "files": files})
print(json.dumps({"zip": archive.name, "members": len(members), "manifest_files": len(files), "comment_lengths": comment_lengths}, indent=2))
