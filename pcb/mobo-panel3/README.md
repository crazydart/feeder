# REV12CD — three-board routed panel

Open **[feeder-rev12cd-panel3.kicad_pro](feeder-rev12cd-panel3.kicad_pro)** in KiCad 10, then open its PCB. This is a real editable KiCad panel with three copies of the [single-board REV12CD source](../mobo/mobo.kicad_pro). U2 is removed from every copy. Each board's silkscreen reads **REV12CD**.

![Panel back in installed orientation](back-installed-preview.png)

All three copies include the AI Herding Cats vector logo, website, repository URL, 20 × 6 mm serial-number box and **Original design: Opulo / Open-source hardware** credit. Back artwork reads upright in the installed feeder. Each logo and caption remains an editable KiCad group. [Panel front](top-gerber-preview.png).

The panel is **184 × 104 × 1.6 mm**, three columns at **59 mm pitch**, with six drilled tabs per board. The four side tabs and requested top/bottom tabs are retained. It uses 18 tabs, 144 × 0.6 mm NPTH holes at 1 mm pitch, and 2 mm routed channels. There are no V-cuts. [Annotated tab placement](tab-placement-preview.png).

## Files to use

- **[feeder-rev12cd-panel3-jlcpcb.zip](feeder-rev12cd-panel3-jlcpcb.zip):** the PCB upload, including both paste layers in the same ZIP. Nine Gerbers and two Excellon files.
- **[ORDER-NOTES.md](ORDER-NOTES.md):** fabrication settings, counts and short PCB order comment.
- **[STENCIL-AND-PNP.md](STENCIL-AND-PNP.md):** 0.10 mm top-stencil recommendation and machine setup data.
- **[assembly/](assembly):** full component catalog, 165 candidate SMD placements, fiducials, panel offsets and stencil settings.
- **[validation/](validation):** PCB/schematic comparison, DRC/ERC, routing, drill, paste and placement checks.
- **[MANIFEST.json](MANIFEST.json):** checksums for fabrication, source, assembly and validation files.

The panel has its own PCB project for layout and manufacturing. Edit the circuit in the single-board schematic; regenerate the panel afterward. Do not update the three-copy panel directly from the single-board schematic.

## Reproduction

Dependencies: KiCad **10.0.3**, its bundled Python (`pcbnew` and `wx`), and Python 3.11 with **Shapely 2.0.7**, Gerbonara, CairoSVG, Pillow and NumPy. The scripts use `kicad-cli` on PATH, with a macOS application fallback. The preview renderer uses Cairo; on macOS its library path may need to include KiCad's Frameworks directory.

From the repository root:

1. Edit `pcb/mobo/mobo.kicad_sch` / `.kicad_pcb`. Refill the unit with `kicad-cli pcb drc --refill-zones --save-board --schematic-parity --format json --output pcb/mobo-panel3/validation/unit-drc.json pcb/mobo/mobo.kicad_pcb`.
2. Run `pcb/mobo-panel3/tools/export_component_bounds.py` with KiCad's Python, then `build_panel.py` with the geometry Python environment.
3. Refill the panel with `kicad-cli pcb drc --refill-zones --save-board --format json --output pcb/mobo-panel3/validation/drc.json pcb/mobo-panel3/feeder-rev12cd-panel3.kicad_pcb`.
4. Run `export_fabrication.py` using standard Python. It includes the paste and PnP export.
5. Run `validate_unit.py` with standard Python and `verify_panel.py` with KiCad's Python. The former requires the recorded upstream commit in Git history.
6. Run `validate_fabrication.py` and `validate_stencil.py` with the geometry/Gerber dependencies. Run `kicad-cli sch erc --format json --output pcb/mobo-panel3/validation/unit-erc.json pcb/mobo/mobo.kicad_sch` for the schematic report.
7. Run `render_gerbers.py pcb/mobo-panel3`, then `render_tab_preview.py`.
8. Run `package_order.py` to rebuild the upload ZIP, BOM and checksums. Inspect changes before publishing a new revision.

The scripts assert expected board counts, footprint/pad correspondence, clearance and the known inherited DRC findings. An assertion failure requires investigation; it should not be bypassed to generate an order.

## Validation result

The panel has 204 non-tab footprints, 741 original pads and 2,526 tracks/vias matching three translated unit boards. Silkscreen checks verify all copied text, all 21 logo polygons, three serial-number boxes and three editable logo groups against the single board. The 144 additional pads are exclusively NPTH breakaway holes. Minimum tab-to-connector/button footprint clearance is **3.15 mm**; a raster check of exported copper gives a conservative **0.69 mm** minimum clearance from the tab-hole rims. Separating all perforation rows yields exactly three boards and the frame.

No shorts, electrical clearance errors, dangling tracks or unconnected items were found. The panel retains nine source thermal-relief findings, three TP3/J3 courtyard overlaps and 264 library/silkscreen warnings. The separate unit schematic retains upstream ERC findings documented in [../mobo/README.md](../mobo/README.md). This panel has not been physically prototyped.

Artwork panel regenerated 2026-10-12 from single-board commit `5a49448`. Modified by crazydart; derived from Opulo REV12. Hardware attribution and CERN-OHL-W v2 licensing remain in [LICENSE](../../LICENSE). The modified boards use AI Herding Cats branding and credit the original Opulo design.
