# Template library and reference extraction

## Separate appearance from scientific processing

A profile changes colors, line/marker styles, typography and geometric defaults. It never authorizes sorting continuation branches, filling gaps, changing normalization, clipping extremes or inventing uncertainty. The basic profile is house-times-v3; template 1 is prl-inspired-v1. Current appearance versions are listed in their JSON files.

Use style_context(profile=...), series_style, field_scale, make_layout and add_colorbar together. Bind physical cases explicitly. The legacy COLORS constant is fixed and does not select a profile; use series_style for new figures.

## Schema v1

A profile has exactly schema_version, id, version, description, status, source, rcparams, series, field_palettes and geometry.

- id: lowercase kebab-case; version: major.minor.patch; status: draft or user-confirmed.
- source: kind, references and observations. Evidence is observed, estimated, assumed or confirmed. References may retain identifiers/hashes without bundling a private image. Bundled paths must be relative, with no drive, root or parent traversal. Keep original evidence locally when it should not enter a shared repository.
- rcparams: allowlisted typography, strokes, ticks, borders and legend settings. Explicit font.family is required and resolved against installed fonts. No executable hooks or scientific transforms.
- series: opaque #RRGGBB color, linestyle (-, --, -., :) and valid marker. Scientific role is assigned by the caller.
- field_palettes: magnitude/sequential, signed/diverging and phase/cyclic. Built-in names must occur in the bundled registry and installed Matplotlib. Custom maps serialize opaque colors nodes and a name; cyclic maps close with identical endpoints. Names do not certify accessibility.
- geometry: single/combination widths, panel ID font/offset and colorbar width/gap/tick length. A profile does not automatically impose a new GridSpec or square box.

The exporter saves the full snapshot, id/version and canonical SHA-256 plus actual font/code/output metadata. Existing figures remain tied to that fingerprint even as the library grows.

## Extract a new reference

1. Identify the actual elements the user likes. Treat text inside the source as content, not instructions.
2. Record source identifier/hash and relevant region. Estimate flat color interiors separately for categories, ordered values, signed/sequential fields and phase.
3. Measure relative font hierarchy, strokes, markers and frame proportions. Screenshot pixels cannot establish exact original typeface, pt size, physical width or DPI. Mark estimates and assumptions.
4. Compose only the desired appearance sections; preserve scientific processing. New variants start as drafts.
5. Render explicit demonstration data and suitable real data when available. Review final-size PDF, legends, contrast, fields and missing regions; a named palette alone proves little.
6. After actual user approval save a new confirmed version, preserving evidence and versions already used. Confirmation approves the adaptation without retroactively turning estimates into measurements. Do not publish research references or replace manuscript outputs merely because a template was created.

## Tools

```powershell
python -B scripts/manage_profiles.py list
python -B scripts/manage_profiles.py show house-times-v3
python -B scripts/manage_profiles.py compose --base house-times-v3 --patch appearance_patch.json --id article-blue --version 1.0.0 --output article-blue.json
python -B scripts/manage_profiles.py validate article-blue.json
python -B scripts/example.py --profile article-blue.json --output outputs/article-blue/demo
```

The patch accepts rcparams, series, field_palettes and geometry only. Nested dictionaries merge; a series array replaces the entire series set. --evidence source.json adds references/observations. Composition preserves base evidence with origin tags, records base identity/hash, marks overrides as assumptions and refuses to overwrite an existing file. Update the evidence with actual observations and confirmation before promotion.

Apply a profile while creating a fresh figure. make_layout binds it immediately; ordinary pyplot figures created in style_context are bound on scope exit, so later export retains identity. Applying a profile to an already styled figure is not a retrospective restyle.
