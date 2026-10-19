"""Read evaluated OpenSCAD dimensions so renders and checks share the CAD setup."""
import json
import re
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]


def parameters():
    (HERE / "generated").mkdir(exist_ok=True)
    result = subprocess.run([
        "openscad", "-D", 'render_part="parameters"', "-o",
        str(HERE / "generated/parameters.csg"), str(HERE / "holder.scad")
    ], check=True, capture_output=True, text=True)
    values = json.loads(re.search(r"ECHO: (\[[^\n]+\])", result.stderr).group(1))
    keys = ["slots", "slot_pitch", "length", "width", "height", "feeder_z",
            "floor_z", "rail_z", "reel_lift", "reel_diameter", "reel_width",
            "reel_axle_x", "reel_axle_y", "reel_axle_z", "reel_radial_clearance"]
    assert len(values) == len(keys)
    result = dict(zip(keys, values))
    result["lanes"] = [(i-(result["slots"]-1)/2)*result["slot_pitch"]
                       for i in range(result["slots"])]
    return result
