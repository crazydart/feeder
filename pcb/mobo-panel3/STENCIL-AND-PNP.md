# REV12CD stencil and future PnP setup

Both front (`F_Paste.gtp`) and back (`B_Paste.gbp`) paste files are included in **feeder-rev12cd-panel3-jlcpcb.zip**. U2 is absent from the electrical PCB, schematic, stencil and placement catalog. Use **U1 / STM32F031C6T6**.

## Manual stencil order

- Order together with the PCB / Panel by Customer.
- Frameless, Top only, quantity 1, **0.10 mm** thickness selected by customer.
- **1:1 as per Paste Layer**. This preserves the exported aperture geometry.
- Standard 380 × 280 mm fits the panel; custom **244 × 164 mm** is a compact alternative with 30 mm margins around the board envelope.
- No stencil fiducials for manual printing. The PCB's nine optical fiducials remain available for PnP alignment.
- Electropolishing and nano-coating are optional. No production-file confirmation is requested.

The MCU is a 0.5 mm-pitch LQFP with 0.30 mm-wide, 1.475 mm-long paste apertures. At the same aperture geometry, 0.10 mm thickness supplies about 17% less nominal paste volume than 0.12 mm. Printing alignment and avoiding paste smear remain important; the thinner foil may require touch-up on larger connector pads. This is a process recommendation, not a tested production recipe.

Top paste has 654 pad flashes plus the six original J5 mounting polygons and their strokes. Bottom paste has 30 apertures, all for the three J1 programming headers. A bottom stencil is unnecessary if J1 is unpopulated or hand soldered. Top+Bottom on separate stencils can be selected if both sides will be printed.

Stencil remark (under 200 characters):

> Top paste only, 1:1 apertures, 0.10mm foil. Match 184x104mm 3-up panel; keep spacing/orientation. U2 is absent. Ignore mask-only openings. No extra apertures.

## Saved machine data

`assembly/panel-smd-placement-cad.csv` contains **165 candidate SMD placements** with unique P1_/P2_/P3_ references, source-unit references, values, footprints, coordinates, side and raw KiCad rotations. It excludes U2, fiducials, test points, graphics, holes and the through-hole J8 header.

`assembly/component-catalog-cad.json` retains the complete remaining footprint catalog. `panel-layout-and-machine-handoff.json` records the 59 mm board pitch, unit offsets, panel origin, existing fiducials and electrical-master SHA256. `stencil-settings.json` preserves the paste layer names and stencil choices.

Coordinates are millimeters from the **top-left panel corner**, X right and Y down. Gerber Y is negative CAD Y. Rotations are **raw KiCad angles**, not calibrated machine angles; bottom placements are not pre-mirrored. These data are suitable for preparing an OpenPnP job after assigning actual parts/packages, feeders, nozzles, component heights, pickup corrections and camera alignment. Verify the transform and rotations before the first assembly.

The D1/D3 LED alternative and optional J1/J9 programming-header population remain to be chosen. Their source paste apertures are retained; cover unused optional apertures during manual printing. The panel frame has no extra tooling holes or frame fiducials.

## References

- [JLCPCB stencil ordering](https://jlcpcb.com/help/article/how-to-order-a-stencil)
- [JLCPCB stencil aperture instructions](https://jlcpcb.com/help/article/instructions-for-stencil-order)
- [JLCPCB thickness guidance](https://jlcpcb.com/blog/how-to-choose-a-solder-paste-stencil)
