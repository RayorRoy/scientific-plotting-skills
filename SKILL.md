---
name: personal-scientific-plotting
description: Create or revise Python scientific figures using the user's basic or PRL-inspired style, enforcing 600 DPI white-background PNG, Adobe Illustrator-editable SVG, reproducible Python source (.py), and automated export quality checks across Antigravity, Claude Code, and Codex.
metadata:
  version: "1.1.0"
---

# Personal Scientific Plotting

Use Matplotlib's object API and the bundled `scripts/houseplot/` helpers. This skill is self-contained and works identically in **Antigravity**, **Claude Code**, and **Codex** across Linux, macOS, and Windows. User explicit choices take precedence over defaults. Read [README](README.md) for installation and runnable examples.

## Locate the skill helpers (Antigravity, Claude Code, Codex)

Resolve the skill's `scripts/` directory dynamically before importing `houseplot` (avoid hardcoding a single agent directory):

1. Workspace/project local: `.agents/skills/personal-scientific-plotting/scripts` or `.claude/skills/personal-scientific-plotting/scripts`
2. Antigravity global: `~/.gemini/config/skills/personal-scientific-plotting/scripts`
3. Claude Code global: `~/.claude/skills/personal-scientific-plotting/scripts`
4. Codex global: `$CODEX_HOME/skills/personal-scientific-plotting/scripts` (default `~/.codex/skills/personal-scientific-plotting/scripts`)
5. Or direct repository checkout `<repo>/scripts`.

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

## Mandatory Figure Export & Quality Checks (强制图片导出规范)

**Whenever generating a scientific figure, ALWAYS provide both PNG and SVG formats by default** (plus the reproducible Python script), using the unified interface `save_publication_figure`:

```python
report = save_publication_figure(
    fig,
    output_name,          # e.g. "outputs/fig1" -> produces .png, .svg, .py, .pdf, .json
    provenance={
        "data_kind": "simulation",   # synthetic | simulation | experiment
        "sources": [...],
        "transformations": [...],
    },
    source_script=Path(__file__),    # optional; auto-snapshots caller script if omitted
)
```

Do NOT bypass `save_publication_figure` / `export_figure` with a bare `plt.savefig(...)` that writes only PNG or omits checks.

### 1. PNG export rules
- **Resolution**: `600` DPI by default (`dpi=600`; `save_publication_figure` rejects non-600 DPI unless `require_600_dpi=False` is explicitly passed for drafts).
- **Pixel size**: determined directly by the figure's final printed physical size (`width_mm / 25.4 * 600` × `height_mm / 25.4 * 600`).
- **Background**: opaque white (`facecolor='white'`, `transparent=False`).
- **No upsampling**: render directly from Matplotlib at 600 DPI; never upscale a low-resolution raster image to satisfy 600 DPI.
- **Readability & metadata**: verify typography, axes, legends, and curves at final printed size, and confirm PNG `dpi` metadata is 600.

### 2. SVG export rules (Adobe Illustrator editable)
- **True vector graphics**: keep curves, axes, ticks, markers, legends, annotations, and text independent and editable; NEVER rasterize the whole figure (`fig.set_rasterized(True)` / `ax.set_rasterized(True)`) into an embedded PNG.
- **Editable text**: enforce `svg.fonttype = 'none'` by default so text stays editable (`<text>` / `<tspan>`), not converted to paths.
- **SVG 1.1 & Illustrator compatibility**: generate standard SVG 1.1 (`version="1.1"`, `svg.image_inline=True`), clean `<g id="...">` groups (`panel_A`, `colorbar_1`, `legend_1`, etc.), and avoid `<filter>`, `mix-blend-mode`, `isolation`, `<foreignObject>`, and external CSS/file dependencies.
- **Embedded bitmaps when necessary**: dense fields (`pcolormesh(..., rasterized=True)`) or photos may be embedded inline (`data:image/png;base64,...`), rendered at `dpi=600` relative to printed size; avoid unnecessary rasterization.
- **Font compatibility & optional outline fallback**: record all fonts referenced in the SVG (including `STIXGeneral` for mathtext). Do NOT convert all text to paths by default. When missing-font risk exists on a target Illustrator machine, pass `svg_text_to_path=True` to export an **additional** `<stem>.outlined.svg` (`svg.fonttype='path'`) alongside the editable `<stem>.svg`.
- **DPI scope**: SVG is vector and has no canvas DPI; 600 DPI applies to PNG and embedded raster bitmaps inside SVG.

### 3. Automated post-export verification & honest reporting
`save_publication_figure` (and `export_figure`) automatically run `inspect_png` and `inspect_svg` and record all metrics in `<stem>.json` (`report['checks']`, `report['png_checks']`, `report['svg_checks']`):
- **PNG checks**: file exists & decodable, DPI metadata == 600, pixel dimensions match print size, opaque white background.
- **SVG checks**: valid SVG 1.1 XML, true vector (not whole-figure rasterized), editable `<text>` retained, structured `<g id="...">` groups, zero external dependencies, Illustrator-compatible features only, embedded bitmap effective DPI, and canvas bounds (`text_outside_canvas`).
- **Reporting honesty**: if Adobe Illustrator is not installed in the current environment, NEVER claim the SVG was opened or tested in Adobe Illustrator (`checks['illustrator_tested']` is `False`); report only the automated SVG 1.1 structure, vector/text editability, and compatibility checks actually performed.

## Layout & colorbar implementation

Add this skill's `scripts/` directory to Python's import path. Apply `style_context(profile=...)` while creating a fresh figure. Use `series_style(i)` and explicitly bind its colors/lines/markers to physical cases; hollow markers alone do not establish experimental provenance.

`add_colorbar` uses 3 mm width and a 2.4 mm gap without shrinking host axes. Labels/numbers inherit the large font hierarchy; tick strokes are hidden. Use one bar per panel or per row, repeating joint limits where appropriate. Spanning disjoint rows requires an explicit design and `allow_multirow=True`.

Draw at final physical size. Do not combine constrained layout with tight layout/tight cropping, or re-enable automatic layout on the fixed `main_side`/`mixed` presets. Inspect the exported PNG/PDF preview, physical dimensions, raster DPI, fonts, legends, panel IDs and colorbars. Bounds checks do not establish absence of every overlap, accessibility, publisher acceptance or physical model validity. Check current official venue rules only when compliance with a particular venue is requested.

## Extend and migrate

Read [template library](references/template-library.md) for screenshot/PDF extraction or composing profiles. Profiles change appearance, not scientific transformations. Distinguish observed pixels, estimates, assumptions and confirmed personal choices. New variants start as drafts and retain source evidence; keep existing versions used by figures. Research reference images may stay local while their hashes/observations accompany the public profile.

Read [portability](references/portability.md) for cross-machine setup. The default profiles require `Times New Roman`; missing fonts fail explicitly unless another font is explicitly selected in a separate profile. Do not automatically upload research data or publish figures merely because the skill is invoked.
