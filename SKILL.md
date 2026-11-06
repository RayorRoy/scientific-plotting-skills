---
name: personal-scientific-plotting
description: Create or revise Python scientific figures using the user's basic or PRL-inspired style, including curves, bars, spatial fields, polar plots and multipanel layouts; extract new appearance profiles from reference figures when requested.
metadata:
  version: "1.0.0"
---

# Personal Scientific Plotting

Use Matplotlib's object API and the bundled `scripts/houseplot/` helpers. This skill is self-contained; `scientific-visualization` is optional conceptual guidance, not a runtime dependency. The user's explicit choices take precedence over either skill's defaults. Read [README](README.md) for setup and runnable examples.

## Select the appearance

- **Basic / 基础风格**: default `house-times-v3`; established categorical palette, 1.2 pt curves, 0.65 pt frames and flexible layouts.
- **Template 1 / PRL / 模板一**: `prl-inspired-v1`; blue/red categories, 1.5 pt curves, 0.8 pt frames and square preferred plot boxes. Read [PRL notes](references/prl-inspired-v1.md); `prl_examples.square_layout()` supplies its fixed boxes. Ordinary `make_layout('grid')` does not enforce squares.
- Both use Times New Roman + STIX, labels/ticks/legends/panel IDs **13/12/11/14 pt**. Start at 90 mm for single figures and 180 mm for combinations. These are personal choices, not publisher requirements.
- Keep `(a)…` outside the upper left. Omit condition/state/frequency titles by default; map IDs to conditions in captions and data records. Enable `panel_label(..., subtitle='...', show_subtitle=True)` only when requested.
- Reserve room for large labels, legends and bars. Reflow a crowded composition rather than silently reducing type. Read [layouts](references/layouts.md) for mixed and nested figures.

## Preserve scientific meaning

Read [standards](references/standards.md) when preparing an actual figure. Identify variables, units, source columns, physical states, transformations, uncertainty and intended final size before plotting.

- Preserve raw inputs, continuation order, branch identity and data gaps. Call `plot_curve` separately for each physical branch; do not globally sort turning paths. It leaves nonfinite samples and nonpositive log values as gaps and reports counts.
- Retain signed power/flux and meaningful baselines. Do not invent error bars, significance or independent replicates from deterministic states, frequencies or mesh nodes.
- Use sequential maps for magnitudes/scalar levels, zero-centred diverging maps for signed fields, and cyclic maps for wrapped phase. Comparable same-unit amplitude maps share a normalization; independent shape normalization must be explicit.
- `field_scale(...,'level')` retains negative dB if present. `pressure_level(...,reference_pa=...)` does not floor invalid pressure. `rounded_level_scale(...,quantum=5)` rounds display limits outward without rounding samples or clipping extremes. Multiples of five suit SPL; do not impose them on phase or arbitrary small quantities.
- Preserve spatial aspect and mesh holes. `rectilinear_grid` rejects duplicates rather than averaging them. `unit_vectors` creates direction-only arrows and leaves zero/invalid vectors undefined; describe the encoding in the caption.

## Implement and export

Add this skill's `scripts/` directory to Python's import path. Apply `style_context(profile=...)` while creating a fresh figure. Use `series_style(i)` and explicitly bind its colors/lines/markers to physical cases; hollow markers alone do not establish experimental provenance.

`add_colorbar` uses 3 mm width and a 2.4 mm gap without shrinking host axes. Labels/numbers inherit the large font hierarchy; tick strokes are hidden. Use one bar per panel or per row, repeating joint limits where appropriate. Spanning disjoint rows requires an explicit design and `allow_multirow=True`.

`export_figure(fig,stem,provenance,dpi=600,overwrite=False)` creates PDF, editable-text SVG, PNG, a PDF-rendered preview and a JSON audit. Required provenance fields are `data_kind`, `sources`, `transformations`; also record source hashes, units, caption, scale limits, normalization and uncertainty where applicable. Existing outputs require explicit overwrite.

Draw at final physical size. Do not combine constrained layout with tight layout/tight cropping, or re-enable automatic layout on the fixed `main_side`/`mixed` presets. Inspect the **actual exported PDF preview**, physical dimensions, raster DPI, fonts, legends, panel IDs and colorbars. Bounds checks do not establish absence of every overlap, accessibility, publisher acceptance or physical model validity. Check current official venue rules only when compliance with a particular venue is requested.

## Extend and migrate

Read [template library](references/template-library.md) for screenshot/PDF extraction or composing profiles. Profiles change appearance, not scientific transformations. Distinguish observed pixels, estimates, assumptions and confirmed personal choices. New variants start as drafts and retain source evidence; keep existing versions used by figures. Research reference images may stay local while their hashes/observations accompany the public profile.

Read [portability](references/portability.md) for another machine. Times must exist on the destination; missing fonts fail explicitly. Use an alternative only after it is selected and recorded in a separate profile. Do not automatically install this skill, replace other skills, upload research data or publish figures merely because the skill is invoked.
