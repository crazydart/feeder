# JLCPCB order — REV12CD

Upload **feeder-rev12cd-panel3-jlcpcb.zip**. This supersedes the earlier REV12 FAB1/TABS3/R2 motherboard uploads. U2 is physically removed; each PCB is labeled REV12CD. Both paste layers are in the same PCB ZIP.

| Setting | Value |
|---|---|
| Material / layers | FR-4 TG135 / 2 |
| Delivery format | Panel by Customer |
| Different designs / array | 1 / 3 columns × 1 row |
| Panel size | 184 × 104 mm |
| Thickness / copper | 1.6 mm / 1 oz |
| Finish | ENIG; standard 1 µin option |
| Mask / silk | Blue / white (preview colors are illustrative) |
| Quantity | Count of panels: 10 panels = 30 boards; 30 panels = 90 boards |
| Min via hole | 0.3 mm option |
| Via covering | Tented; no filling/capping |
| Outline tolerance | Regular ±0.2 mm |
| Electrical test | Flying probe |
| Order mark | Remove |
| Special edge processes | No gold fingers, castellations, edge plating or blind slots |
| Separation | Routed mouse-bite tabs; no V-cuts |
| Production-file confirmation | No, per ordering preference |
| Stencil | Order together with PCB; see STENCIL-AND-PNP.md |

Do not add another array or rails: the supplied files already contain the complete panel. Mounting holes are straight holes; countersinking is not specified. No order has been placed by this repository's tooling.

## PCB remark — under 200 characters

> 3 identical PCBs, 184x104x1.6mm customer panel. Route GM1 slots; retain 18 breakaway tabs with 144x0.6mm NPTH holes. No V-cuts. Keep tabs clear of connectors/buttons as drawn. Ship intact panels.

## Manufacturing contents

Nine Gerbers: front/back copper, mask, silkscreen and paste, plus GM1 outline/routing. Two Excellon files: PTH and NPTH. The panel contains 558 plated holes (528 × 0.3 mm, 12 × 0.4 mm, 18 × 1 mm), plus 144 × 0.6 mm NPTH breakaway holes.

The original 39 unplated circular openings are represented in GM1: 21 × 3.2 mm mounting holes and 18 × 0.7 mm connector-locating holes. Preserve these in CAM; the 0.7 mm openings may be drilled. GM1 also contains the outer panel and 18 routed cutouts.

Every tab has eight holes at 1 mm pitch, leaving 0.4 mm between hole edges. The routed channel uses a 2 mm cutter. The minimum tab neck is 5.6 mm; outer rails are at least 5 mm. The top/bottom tabs are in the requested positions, away from the edge connectors and buttons. Tabs require breaking/clipping and dressing the residual nubs before installing the PCB.

See [README.md](README.md) and [validation/](validation) for the inherited DRC/ERC findings and the independent output checks.
