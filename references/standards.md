# Scientific figure standards

## Typography, axes and physical size

The confirmed personal defaults are adjustable when the data and intended size require it:

| Element | Default |
|---|---|
| Typeface | Times New Roman; STIX for mathematics |
| Single / combination width | 90 / 180 mm |
| Axis and colorbar label / tick / legend / panel ID | 13 / 12 / 11 / 14 pt, shared with PRL-inspired style |
| Curve / axes frame | 1.2 / 0.65 pt |
| Marker diameter | 3.5 pt; sparse on dense lines |
| Axes | Four-sided frame; inward ticks; no default Cartesian grid |
| Exports | PDF + SVG with text + 600 DPI PNG, opaque white |
| Panel ID | Outside upper-left; 12 pt left / 5 pt above plot corner |
| Descriptive panel title | Off by default; state/condition/frequency belongs in caption and provenance |
| Vertical colorbar | 3 mm width; 2.4 mm gap; actual single-panel/row height |
| Colorbar numbers | Labels retained, tick marks hidden; normally 5, up to 6 for rounded scalar levels; phase/log keep their semantic notation |

Use italic variables and upright units/operators via mathtext. Write units in parentheses, for example `Frequency (Hz)` and `$p_{\mathrm{rms}}$ (kPa)`. Distinguish indices from units and explain normalization references. Use meaningful decimals and visible powers of ten; avoid excessive digits and repeated offset strings. Set ticks to the data's scale: sparse log minors can help reading; never globally prohibit them. A polar grid is allowed when it provides angular/radial reference.

A four-sided frame is a starting point for Cartesian plots, not an instruction to box every schematic, polar figure, inset, or field domain. Minor ticks, frame simplification and legend position respond to actual density. Keep panel IDs, axis labels and necessary legends, but omit descriptive titles such as `W5: 200.034 Hz` by default. Map conditions and frequencies to panel IDs in the caption and provenance. Show such titles only when explicitly requested, using `panel_label(..., subtitle='...', show_subtitle=True)` or an explicitly enabled manual title.

## Data and mappings

- Preserve branch ID and original parameter order. A continuation curve can turn in frequency without becoming a new sorted function. Separate discontinuities, missing samples and physical branches.
- For positive log quantities, report nonfinite and nonpositive values; keep holes in the plotted arrays. Describe censoring separately from zero and missingness.
- Categorical colors: blue, vermillion, green, purple, ochre, dark gray; supplement with line patterns, markers or hatches. Check the actual background and final-size rendering; a named palette alone does not prove accessibility.
- Positive field: sequential map, normally an explicit baseline of zero for linear magnitude. Strong dynamic range can justify LogNorm on strictly positive values. Record limits and unit conversion.
- Signed field: symmetric about zero by default, with a diverging map. A non-symmetric range requires an explicit physical reason and zero-centred normalization.
- Wrapped phase: cyclic map with fixed domain, e.g. `[-pi,pi]` radians, and explicit undefined regions. Unwrapped phase is a different quantity.
- A scalar level such as SPL is not a nonnegative magnitude: `field_scale(arrays,'level')` uses joint finite observed min/max and the sequential palette, including negative dB when present. A constant level gets a small explicit display range of ±1% of max(1, absolute level). `pressure_level` requires a reference pressure and preserves undefined values without a floor.
- Comparable same-unit amplitude maps use joint limits. Independent limits or per-panel max normalization may be used to compare shape, with the transformation in caption and provenance. Do not share a colorbar between velocity, force and pressure merely because all three images are blue.
- Keep raw image/mesh detail. Never smooth, crop extremes, average duplicate coordinates, or upsample as if it added physical resolution without an explicit scientific decision.
- Colorbar should expose relevant end values and zero for signed fields. Label quantity, unit and multiplier once; shared bars align with their axes group. Long labels must not force one panel to become disproportionately small.
- For multirow clouds, default to per-panel bars or separate per-row bars, never a tall bar that includes inter-row whitespace. Keep a common global normalization for comparable amplitudes even when displaying multiple bars. `add_colorbar(..., ax, ...)` gives a panel bar; call once per row for row bars. Explicit multirow spanning is an exception requiring the intended design.
- Use the fixed-width `add_colorbar` helper. Linear ticks include both limits and signed zero; phase ticks are `-pi,-pi/2,0,pi/2,pi`. Log ticks retain in-range decades (up to five); if fewer than two decades fit, use three explicit log-spaced values. Norm limits remain in the provenance even when end limits are not decimal powers. Suppress minor ticks and redundant numeric detail.
- The default hides the tick strokes but keeps numeric labels; this is separate from deleting tick values. For SPL, prefer outward-rounded integer display limits and regular labels in multiples of 5 dB. `rounded_level_scale` minimizes added empty range while limiting label count; an example range is 100–225 dB, step 25 dB, six labels. Record both observed and displayed limits. Original samples are unchanged. Other units may need a display multiplier, and phase retains pi-based labels.
- When limiting a wide log range to at most five labels, use a regular integer exponent interval, not an uneven subset of adjacent decades. Narrow log labels use enough significant digits to remain distinct, avoiding repeated labels such as `1,1,1` for genuinely different values.

## Statistics and bars

Use a zero baseline for bars in ordinary linear comparisons; a log baseline for bars needs a strong and explicit rationale. Signed power/flux keeps its sign. State whether values are totals, means, fractions or normalized quantities. Different simulation states and channels are not independent replicates. Use error bars only with their defined source and meaning; do not create pseudo-replication from mesh nodes or deterministic frequency points.

## Provenance and review

Keep a per-figure JSON (or equivalent) containing source paths/hashes, columns, units, transforms, exclusions, scale limits, any uncertainty/seed, caption, code/version and output hashes. Prefer meaningful CSV or native analysis tables; XLSX and PDF reports are optional deliverables, not mandatory for every plot.

The exporter verifies PDF size and font embedding and PNG dimensions/DPI, and screens text bounds. Its typography and raster checks are not a publisher acceptance certificate. It does not measure each embedded image's effective DPI, check contrast at every pixel, or prove absence of overlapping artists. Inspect the actual exported PDF at final size. Verify live journal rules only for a specified destination/phase.

## Application prompts

- An upper frequency curve with three lower pressure fields: retain branch order; ensure selected markers correspond to actual rows and lower-panel states. Use shared pressure mapping only. If some fields lie outside the displayed upper frequency range, say so rather than implying a false correspondence.
- A 180 mm figure with long units: keep the canvas fixed, reserve label/colorbar space, simplify repeated labels, or increase height. Do not fix clipping by tight-cropping the output.
- A new environment without Times: report the missing font and request/propose an explicitly approved alternative; do not silently substitute another typeface.
