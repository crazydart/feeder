# AI Herding Cats board artwork

`robot-cat-white.svg` is the user's supplied original vector logo, copied unchanged from `pcb-engineering/assets/logos/robot-cat/robot-cat-white.svg`. White represents silkscreen ink; all facial and body openings are transparent. No preview background is part of the artwork.

The single-board PCB contains the logo as seven filled `B.SilkS` polygons, grouped with the **AI Herding Cats** caption under **AI Herding Cats logo**. The eight enclosed transparent cutouts are preserved using KiCad's fractured polygon contours. Curves were approximated with a sampled chord error of at most 0.004 mm.

- SVG canvas on the PCB: **26 × 16.9345 mm**, preserving the original aspect ratio.
- Placement: canvas spans CAD X **113–139 mm**, Y **36.0655–53 mm**.
- Artwork is mirrored for the back layer and rotated **180°** to read correctly with the feeder installed. Both preview images use the installed orientation.
- Caption: centered at CAD **(126, 35) mm**, 180° rotation, 1.25 mm lettering, 0.20 mm stroke.
- **Feeder REV12CD** is centered at **(134, 100.5) mm**; the 20 × 6 mm serial block spans **(124, 92)–(144, 98) mm** and **SN:** is centered at **(120.8, 95) mm**.
- **aiherdingcats.com** is centered at **(134, 89.2) mm**, 1.05 mm lettering.
- **github.com/crazydart/feeder** is directly underneath in the installed view, centered at **(134, 87.6) mm**, 1 mm lettering and 0.15 mm stroke.
- **Original design: Opulo / Open-source hardware** is a two-line credit centered at **(113.4, 58.5) mm**, 1 mm lettering.
- All added back text is mirrored and rotated 180°. The original open-hardware mark remains intact.

Move the named group to reposition the logo and caption together. Retain the SVG as the editable artwork source. The panel and manufacturing ZIP have not yet been regenerated with this draft artwork.
