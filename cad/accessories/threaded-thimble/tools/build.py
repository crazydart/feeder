"""Export the two print-oriented STLs. Requires OpenSCAD with Manifold."""
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
PARTS = {
    "thimble": "threaded-thimble-prototype-01.stl",
    "screw": "reel-retaining-screw-30mm-prototype-01.stl",
}

if __name__ == "__main__":
    (HERE / "stl").mkdir(exist_ok=True)
    for part, filename in PARTS.items():
        subprocess.run(["openscad", "--backend", "Manifold", "--export-format", "binstl",
                        "-D", f'part="{part}"', "-o", str(HERE / "stl" / filename),
                        str(HERE / "thimble.scad")], check=True)
