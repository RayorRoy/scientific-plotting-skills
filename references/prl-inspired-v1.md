# Template 1 — PRL-inspired

Select profile prl-inspired-v1 for “模板一 / PRL 风格”. This is the user's confirmed personal adaptation, not an official journal style. The profile keeps evidence categories and source hashes; original research screenshots stay local. User approval confirms the resulting appearance, not otherwise unknowable original fonts or point sizes.

## Reference features and chosen parameters

Most measured outer frames were approximately 244–245 by 222–224 pixels (ratio about 1.09–1.10), not exact squares. One photograph was near square; another panel consisted of three short stacked subaxes. Square preferred boxes are the personal adaptation, not a claim about every reference subaxis.

Use Times New Roman with STIX mathematics, 13 pt labels, 12 pt ticks, 11 pt legends and bold 14 pt external IDs. Both current styles share this large hierarchy. Data curves are 1.5 pt, frames 0.8 pt and markers 5 pt. Use sparse inward major ticks, a white background, thin four-sided frames and compact frameless legends. Top/right ticks vary in the references; choose deliberately.

| Encoding | Approximate colors |
|---|---|
| Categories | #003399 blue; #C41614 red; #EC941E orange; #1EAE37 green; #0073BD cyan-blue; #333333 gray |
| Ordered parameter | #BFCDE9 → #5B80C5 → #003399; add redundant line patterns |
| Signed field | Blue → white → red, centred on zero |
| Magnitude/scalar level | White → red, sequential; dB limits follow the physical data range |
| Wrapped phase | Inherited twilight_shifted; not extracted from a phase reference |

Hex values approximate screenshot pixels affected by antialiasing and capture settings. Pale blue has weak contrast on white; red/green pairs need shape or line redundancy. Serialized custom nodes reproduce the chosen maps but do not certify perceptual uniformity. A rainbow-like source field is not the quantitative default.

Markers, arrows, highlighted points, broken axes and dual axes express specific scientific content. Do not copy reference annotations or infer that hollow markers mean experiments without actual evidence. Keep conditions/frequencies in captions; no descriptive titles by default. Retain 3 mm panel/row bars with hidden tick strokes and visible numbers.

## Use

```python
from houseplot import style_context
from prl_examples import square_layout

with style_context(profile='prl-inspired-v1'):
    fig, axes = square_layout()  # 180×166 mm, four 56 mm squares
    # Draw actual data and explicitly bind cases to styles.
```

Use square_layout(single=True) for a single 58 mm square plot. Ordinary make_layout('grid') does not force squares. For a non-square physical domain, preserve coordinate aspect rather than stretch the data.

Run scripts/prl_examples.py --output-dir outputs/prl for reproducible analytic examples, actual CSVs, PDF/SVG/PNG, previews and metadata. The hollow markers sample analytic curves and imply no experimental observations. Inspect the exported PDF at its intended final size.
