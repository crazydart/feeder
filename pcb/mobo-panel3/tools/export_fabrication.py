#!/usr/bin/env python3
"""Export this routed panel after KiCad DRC/refill. No V-cut layer."""
import subprocess
import shutil
import sys
from pathlib import Path

root = Path(__file__).resolve().parents[1]
order = root
cli = shutil.which("kicad-cli") or "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
board = root / "feeder-rev12cd-panel3.kicad_pcb"
gerbers = order / "gerbers"
gerbers.mkdir(exist_ok=True)


def run(*args):
    subprocess.run([cli, "pcb", "export", *map(str,args)],check=True)


run("gerbers", "--output", gerbers, "--layers", "F.Cu,B.Cu,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts",
    "--precision", "6", "--check-zones", "--subtract-soldermask", board)
run("drill", "--output", gerbers, "--format", "excellon", "--drill-origin", "absolute", "--excellon-units", "mm",
    "--excellon-zeros-format", "decimal", "--excellon-separate-th", "--generate-report", "--report-path", order / "validation/drill-report.txt", board)
for p in gerbers.glob("*.gbrjob"):
    p.unlink()
subprocess.run([sys.executable, str(root / "tools/export_stencil_and_pnp.py")], check=True)
print("Exported nine Gerbers (including both paste layers), PTH and NPTH drill files to",gerbers)
