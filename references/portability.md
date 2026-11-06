# Portability

Copy the complete skill directory, not SKILL.md alone. Runtime resources use relative package paths; no circular-plate project or upstream scientific skills are required. Installation and commands are in [README](../README.md).

The verified environment is Python 3.12.10 on Windows. requirements.txt records tested direct versions, not a transitive or cross-platform lock. Reuse a suitable environment or create an isolated environment; do not replace an existing scientific environment merely to draw a figure.

Times New Roman must exist on the destination system; it is not bundled. A missing selected font fails explicitly. Select another font through a separate profile instead of silently substituting. PDF embeds fonts, while editable SVG text depends on the viewing system. Matplotlib provides the STIX mathematics fonts.

Set MPLCONFIGDIR before importing Matplotlib when a writable cache location matters. The example scripts use output-local caches, and profile management respects an existing MPLCONFIGDIR. Keep generated outputs separate from installed skill files.

Relocation check:

```powershell
python -B scripts/manage_profiles.py list
python -B scripts/example.py --output outputs/basic/demo
python -B scripts/prl_examples.py --output-dir outputs/prl
python -B -m unittest discover -s tests -q
```

Check exported size, font embedding, text bounds and profile fingerprint; view the PDF-rendered preview. A same-OS relocation check does not prove compatibility with every OS or font installation. Research source paths in figure metadata are identifiers; actual reproduction requires the corresponding source data, supplied independently.
