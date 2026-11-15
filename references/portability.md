# Portability

Copy (or symlink) the complete skill directory, not `SKILL.md` alone. Runtime resources use relative package paths; no circular-plate project or upstream scientific skills are required. Installation commands for **Antigravity**, **Claude Code**, and **Codex** are in [README](../README.md) and automated via `scripts/install_skill.py`.

## Agent discovery paths

- **Antigravity**: `~/.gemini/config/skills/personal-scientific-plotting` (global) or `.agents/skills/personal-scientific-plotting` (workspace)
- **Claude Code**: `~/.claude/skills/personal-scientific-plotting` (global) or `.claude/skills/personal-scientific-plotting` (project)
- **Codex**: `$CODEX_HOME/skills/personal-scientific-plotting` (default `~/.codex/skills/personal-scientific-plotting`) or `.agents/skills/personal-scientific-plotting`

## Python environment & dependencies

Core runtime dependencies are **NumPy**, **Matplotlib**, and **Pillow** (tested on Python 3.12 on Windows and Python 3.14 on Ubuntu Linux). `requirements.txt` records tested direct versions, not a cross-platform lock. Reuse a suitable scientific environment or create an isolated environment.

`pymupdf` is optional: when installed, `save_publication_figure` / `export_figure` also inspects PDF font embedding and renders `<stem>.preview.png`; when absent, PDF, 600 DPI PNG, Illustrator-editable SVG, reproducible `.py`, and JSON audit + PNG/SVG checks still run cleanly.

## Fonts & SVG Illustrator compatibility

`Times New Roman` must exist on the destination system for the default `house-times-v3` and `prl-inspired-v1` profiles; it is not bundled. A missing selected font fails explicitly. On Linux systems without `Times New Roman`, either install Microsoft Core Fonts / Times New Roman or explicitly compose a separate profile (for example using `Liberation Serif`) via `scripts/manage_profiles.py` instead of silently substituting.

Matplotlib provides `STIXGeneral` internally for mathtext (`mathtext.fontset: stix`). Because editable SVGs (`svg.fonttype: 'none'`) reference both the body font and `STIXGeneral` by name, `inspect_svg` records all referenced fonts and compatibility warnings. If an Adobe Illustrator workstation lacks those fonts, pass `svg_text_to_path=True` to `save_publication_figure(...)` to export an additional `<stem>.outlined.svg` fallback without outlining the primary editable `.svg`.

Set `MPLCONFIGDIR` before importing Matplotlib when a writable cache location matters. The example scripts use output-local caches, and profile management respects an existing `MPLCONFIGDIR`. Keep generated outputs separate from installed skill files.

## Relocation check

```bash
python -B scripts/manage_profiles.py list
python -B scripts/example.py --output outputs/basic/demo --profile <installed-profile-or-default>
python -B -m unittest discover -s tests -q
```

Check exported size, PNG 600 DPI metadata, SVG 1.1 vector/text editability, font compatibility warnings, text bounds, and profile fingerprint. A same-OS relocation check does not prove compatibility with every OS, font installation, or Adobe Illustrator version; only report Illustrator testing if Illustrator was actually run.
