# Layouts and scientific relationships

Return panels in reading order, with continuous (a)… IDs outside the upper left. Conditions and frequencies belong in captions/data records by default. Enable descriptive text only on explicit request with panel_label(..., subtitle='...', show_subtitle=True). Insets normally belong to the parent panel.

| Name | Composition |
|---|---|
| single | Single panel, starting width 90 mm |
| row3 / column3 | Horizontal / vertical triplet |
| matrix2x3 | Two rows and three columns |
| overview | Upper full-width panel and three lower panels |
| main_side | Large left panel and two right auxiliary panels |
| mixed | Curve/inset, field, bars and polar example; D is polar |
| nested | Two groups with two internal panels each |
| grid | Parameterized rows/columns, at most 26 panels |

Use make_layout with rows/cols for grid and an explicit width_mm when needed. For PRL square preferred boxes use prl_examples.square_layout(); it returns a 180×166 mm canvas with four 56 mm squares, or a 90×86 mm single canvas with a 58 mm square when single=True. A square box does not imply equal x/y data units for arbitrary curves. Physical spatial fields retain equal coordinate aspect; non-square domains may need non-square boxes.

Most presets use constrained layout. main_side and mixed use explicit physical boxes: do not re-enable automatic layout or tight cropping. At 180 mm, main_side is 100 mm high; its main field is 74 mm square, matching the full B + gap + C height. Mixed is 136 mm high; its right field/polar boxes are both 46 mm square and aligned. With the current 12 pt ticks a 25 mm decoration gutter gives both B/D x=109 mm. Large or long labels still need inspection.

The two fixed complex presets require at least 150 mm total width. Narrower compositions should simplify or reflow. The mixed gutter follows font size; preserve shared column alignment and spatial aspect when adjusting it. Do not shrink one panel merely because a colorbar was attached.

Share axes only when variable, unit and scale match. Share color normalization only for comparable physical quantities. Multirow fields use per-panel or per-row bars; repeated bars can retain the same global normalization. The helper rejects disjoint-row spanning unless allow_multirow=True is explicitly requested.

For zooms preserve the parent data, show actual zoom bounds/connectors and explain them in the caption. For polar plots declare zero direction, rotation sense, radial reference/unit and any dB transformation. A radial plot is not an area comparison; negative dB must not silently become positive linear radius.

When reusing a layout, compare canvas/panel dimensions in millimetres. A new composition is allowed but should be identified; equal total width does not prove equal panel sizes. Review additional nested, marginal or 3D layouts before describing them as supplied presets.
