# Feeder motherboard REV12CD

Open **mobo.kicad_pro** in KiCad 10. The schematic and single-board PCB use **U1, STM32F031C6T6 (LQFP-48)**. U2 and its isolated schematic block are removed, along with 61 PCB track segments that served only its pads. Shared vias and routing needed by U1 are retained.

The remaining component locations, 247 pads, 842 tracks/vias and schematic connections match upstream REV12. R18 and R19 remain 1 MΩ. No firmware or pin assignment changes are introduced. The original board outline and holes remain unchanged.

The silkscreen identifies this derivative as **REV12CD / crazydart**. Upstream product branding was removed from the modified board; the open-hardware symbol and upstream copyright/license attribution are retained. Custom footprint paths are relative to this repository. The historical MHS110FRGBCT footprint is included in `../../lib/kicad/index.pretty` so D1 resolves without the upstream author's local library.

## Three-board panel and manufacturing

Open [../mobo-panel3/feeder-rev12cd-panel3.kicad_pro](../mobo-panel3/feeder-rev12cd-panel3.kicad_pro) for the editable panel. The panel is generated from this single-board master and contains three electrically separate copies with unique CAD references.

See the [panel README](../mobo-panel3/README.md), [ordering instructions](../mobo-panel3/ORDER-NOTES.md), and [stencil/PnP handoff](../mobo-panel3/STENCIL-AND-PNP.md). The current [BOM](bom/rev12cd-bom.csv) includes population notes. D1/D3 and the optional programming headers still require a final assembly choice; U2 is absent.

The old upstream STEP and interactive BOM were removed because they represented the previous board. The native KiCad board and current catalog/placement files are authoritative.

## Validation and provenance

KiCad schematic-to-PCB parity: **zero issues**. Board connectivity: **zero unconnected items**. Three inherited thermal-relief findings (U7 pad 4, U8 pad 4 and C3 pad 1) and one inherited TP3/J3 courtyard overlap remain. The schematic retains 17 upstream ERC errors; removing U2 adds three isolated-label warnings for the unused U1 PA0/PA1/PA3 signals. These findings are recorded, not hidden by exclusions. See [validation reports](../mobo-panel3/validation).

Modified 2026-10-11 by crazydart from [opulo-inc/feeder](https://github.com/opulo-inc/feeder), commit `05843dd0e7551cbf20dc831514174f446f376858`. This is an independently modified REV12 board, not an upstream revision or the earlier REV12B experiment. Hardware remains under CERN-OHL-W v2; see [LICENSE](../../LICENSE).
