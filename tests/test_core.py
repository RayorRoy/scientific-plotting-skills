"""Behavioral checks for data integrity and delivered figure files."""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR'] = str(ROOT / '.cache' / 'matplotlib')
(ROOT / '.cache').mkdir(exist_ok=True)
sys.path.insert(0, str(ROOT / 'scripts'))

import matplotlib
matplotlib.use('Agg')
from matplotlib import font_manager
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

try:
    import pymupdf
except ImportError:
    pymupdf = None

from houseplot import (
    style_context,
    make_layout,
    plot_curve,
    field_scale,
    add_colorbar,
    export_figure,
    save_publication_figure,
    inspect_png,
    inspect_svg,
)
from houseplot.profiles import load_profile


def _available_profile(tmpdir):
    """Use default Times profile if installed; otherwise build a temp profile with an installed font."""
    try:
        font_manager.findfont('Times New Roman', fallback_to_default=False)
        return None
    except Exception:
        pass
    for candidate in ('Liberation Serif', 'DejaVu Serif', 'DejaVu Sans'):
        try:
            font_manager.findfont(candidate, fallback_to_default=False)
            p = load_profile('house-times-v3')
            p['id'] = 'test-local-font'
            p['rcparams']['font.family'] = candidate
            path = Path(tmpdir) / '_test_profile.json'
            path.write_text(json.dumps(p), encoding='utf-8')
            return path
        except Exception:
            continue
    raise RuntimeError('No suitable test font installed')


class ScienceTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_log_invalid_observations_remain_gaps(self):
        fig, ax = plt.subplots()
        values = np.array([1., np.nan, 2., 0., -1., 3.])
        line, report = plot_curve(ax, np.arange(6), values, log_y=True)
        np.testing.assert_allclose(line.get_ydata(), [1., np.nan, 2., np.nan, np.nan, 3.], equal_nan=True)
        self.assertEqual(report['nonpositive'], 2)
        self.assertEqual(report['nonfinite'], 1)
        self.assertEqual(len(line.get_xdata()), 6)
        self.assertEqual(values[3], 0.)

    def test_continuation_turning_order_is_not_sorted(self):
        fig, ax = plt.subplots()
        line, _ = plot_curve(ax, [1, 3, 2, 4], [1, 2, 3, 4])
        self.assertEqual(list(line.get_xdata()), [1, 3, 2, 4])

    def test_nonfinite_x_breaks_the_path(self):
        fig, ax = plt.subplots()
        line, report = plot_curve(ax, [1, np.inf, 3], [1, 2, 3])
        self.assertTrue(np.isnan(line.get_ydata()[1]))
        self.assertEqual(report['nonfinite'], 1)

    def test_masked_observation_is_not_restored_as_valid_data(self):
        fig, ax = plt.subplots()
        values = np.ma.array([1., 99., 3.], mask=[False, True, False])
        line, report = plot_curve(ax, [1, 2, 3], values)
        self.assertTrue(np.isnan(line.get_ydata()[1]))
        self.assertEqual(report['nonfinite'], 1)

    def test_mismatched_or_empty_curve_rejected(self):
        fig, ax = plt.subplots()
        for x, y in [([1], [1, 2]), ([], []), ([np.nan], [1])]:
            with self.assertRaises(ValueError):
                plot_curve(ax, x, y)

    def test_shared_amplitude_scale_uses_all_panels(self):
        norm, cmap = field_scale([np.array([0., 2.]), np.array([0., 8.])], 'magnitude')
        self.assertEqual((norm.vmin, norm.vmax), (0., 8.))
        self.assertFalse(norm.clip)
        self.assertTrue(np.isfinite(cmap(norm(2))).all())

    def test_signed_scale_centres_zero_and_preserves_extremes(self):
        norm, _ = field_scale([np.array([-2., 5.])], 'signed')
        self.assertEqual((norm.vmin, norm.vmax), (-5., 5.))
        self.assertAlmostEqual(float(norm(0)), .5)

    def test_phase_uses_fixed_wrapped_domain(self):
        norm, cmap = field_scale([np.array([-.1, .2])], 'phase')
        self.assertAlmostEqual(norm.vmin, -np.pi)
        self.assertAlmostEqual(norm.vmax, np.pi)
        np.testing.assert_allclose(cmap(0.), cmap(1.), atol=.025)

    def test_invalid_field_semantics_rejected(self):
        for values, kind in [([np.nan], 'signed'), ([-1, 2], 'magnitude'), ([0, 4], 'phase')]:
            with self.assertRaises(ValueError):
                field_scale([np.array(values)], kind)


class DeliveryTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def test_style_scope_restores_caller_settings(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            before = matplotlib.rcParams['font.family'][:]
            expected_family = [load_profile(prof)['rcparams']['font.family']] if prof else ['Times New Roman']
            with style_context(profile=prof):
                self.assertEqual(matplotlib.rcParams['font.family'], expected_family)
            self.assertEqual(matplotlib.rcParams['font.family'], before)

    def test_all_layouts_have_unique_panel_axes(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            for name, count in [('row3', 3), ('column3', 3), ('matrix2x3', 6), ('overview', 4), ('main_side', 3), ('mixed', 4), ('nested', 4)]:
                with self.subTest(name=name), style_context(profile=prof):
                    fig, axes = make_layout(name)
                    self.assertEqual(len(axes), count)
                    self.assertEqual(len({id(a) for a in axes.values()}), count)
                    self.assertAlmostEqual(fig.get_size_inches()[0] * 25.4, 180.)

    def test_bad_width_and_unknown_layout_rejected(self):
        for width in [0, -1, float('nan')]:
            with self.assertRaises(ValueError):
                make_layout('row3', width_mm=width)
        with self.assertRaises(ValueError):
            make_layout('nonexistent')

    def test_single_layout_default_uses_single_column_width(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, _ = make_layout('single')
                self.assertAlmostEqual(fig.get_size_inches()[0] * 25.4, 90.)

    def test_exact_page_size_editable_svg_and_embedded_pdf_fonts(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4), layout='constrained')
                ax.plot([0, 1], [0, 1])
                ax.set(xlabel='Frequency (Hz)', ylabel='Response (m)')
                stem = Path(d) / 'figure'
                report = export_figure(fig, stem, {'data_kind': 'synthetic', 'sources': [], 'transformations': []}, dpi=150)
                self.assertTrue(report['checks']['page_dimensions'])
                self.assertTrue(report['checks']['svg_editable_text'])
                self.assertTrue(report['checks']['svg_true_vector'])
                self.assertFalse(report['checks']['illustrator_tested'])
                svg = ET.parse(stem.with_suffix('.svg')).getroot()
                self.assertAlmostEqual(float(svg.attrib['width'][:-2]) * 25.4 / 72, 90, places=3)
                self.assertTrue(svg.findall('.//{http://www.w3.org/2000/svg}text'))
                if pymupdf is not None:
                    doc = pymupdf.open(stem.with_suffix('.pdf'))
                    self.assertAlmostEqual(doc[0].rect.width * 25.4 / 72, 90, places=3)
                    fonts = doc[0].get_fonts(full=True)
                    self.assertTrue(all(len(doc.extract_font(f[0])[3]) > 0 for f in fonts))
                    doc.close()
                with Image.open(stem.with_suffix('.png')) as im:
                    self.assertLessEqual(abs(im.width - 90 / 25.4 * 150), 1)
                    self.assertAlmostEqual(im.info['dpi'][0], 150, delta=.2)
                manifest = json.loads(stem.with_suffix('.json').read_text(encoding='utf-8'))
                self.assertEqual(manifest['provenance']['data_kind'], 'synthetic')
                self.assertIn('sha256', manifest['outputs']['pdf'])

    def test_save_publication_figure_default_600dpi_png_svg_and_py(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, axes = make_layout('single')
                ax = axes['A']
                ax.plot([0, 1], [0, 1], label='$p_{\\mathrm{rms}}$ (Pa)')
                ax.set(xlabel='Frequency (Hz)', ylabel='Amplitude')
                ax.legend()
                out_stem = Path(d) / 'pub_demo'
                report = save_publication_figure(fig, out_stem)
                for ext in ('.png', '.svg', '.py', '.pdf', '.json'):
                    self.assertTrue(out_stem.with_suffix(ext).is_file(), f'Missing {ext}')
                self.assertTrue(report['checks']['png_dpi_is_600'])
                self.assertTrue(report['checks']['png_dimensions_ok'])
                self.assertTrue(report['checks']['png_white_background'])
                self.assertTrue(report['checks']['svg_valid_xml'])
                self.assertTrue(report['checks']['svg_is_1_1'])
                self.assertTrue(report['checks']['svg_true_vector'])
                self.assertTrue(report['checks']['svg_editable_text'])
                self.assertTrue(report['checks']['svg_no_external_deps'])
                self.assertTrue(report['checks']['svg_illustrator_compatible'])
                self.assertFalse(report['checks']['illustrator_tested'])
                self.assertIn('panel_A', report['svg_checks']['group_ids_sample'])
                self.assertTrue(len(report['svg_checks']['fonts_referenced']) >= 1)

    def test_save_publication_figure_rejects_non_600_dpi_unless_explicit(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
                ax.plot([0, 1], [0, 1])
                with self.assertRaises(ValueError):
                    save_publication_figure(fig, Path(d) / 'low_dpi', dpi=150)

    def test_save_publication_figure_optional_outlined_svg(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, axes = make_layout('single')
                axes['A'].plot([0, 1], [0, 1])
                axes['A'].set(xlabel='Time (s)', ylabel='Signal')
                out_stem = Path(d) / 'with_outline'
                report = save_publication_figure(fig, out_stem, svg_text_to_path=True)
                outlined = Path(d) / 'with_outline.outlined.svg'
                self.assertTrue(outlined.is_file())
                self.assertTrue(report['svg_checks']['has_editable_text'])
                self.assertFalse(report['outlined_svg_checks']['has_editable_text'])

    def test_svg_inspector_detects_embedded_raster_dpi_and_whole_figure_rasterization(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                # 1. Valid vector figure containing a 600 DPI rasterized heatmap
                fig, axes = make_layout('single')
                x = np.linspace(-1, 1, 25)
                im = axes['A'].pcolormesh(x, x, np.outer(x, x), rasterized=True)
                add_colorbar(fig, im, axes['A'], '$q/q_0$')
                axes['A'].set(xlabel='$x/L$', ylabel='$z/L$')
                report = save_publication_figure(fig, Path(d) / 'heatmap')
                self.assertTrue(report['checks']['svg_true_vector'])
                self.assertGreaterEqual(report['svg_checks']['embedded_image_count'], 1)
                self.assertGreaterEqual(report['svg_checks']['min_embedded_image_dpi'], 590.0)

                # 2. Whole-figure/axes rasterized anti-pattern must be caught and rejected
                fig_bad, ax_bad = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
                ax_bad.plot([0, 1], [0, 1])
                ax_bad.set_rasterized(True)
                with self.assertRaises(RuntimeError):
                    save_publication_figure(fig_bad, Path(d) / 'bad_raster')

    def test_svg_inspector_detects_external_deps_and_filters(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            bad_svg = Path(d) / 'bad.svg'
            bad_svg.write_text(
                '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                'version="1.1" width="100pt" height="100pt" viewBox="0 0 100 100">'
                '<defs><filter id="f1"><feGaussianBlur stdDeviation="2"/></filter></defs>'
                '<g id="figure_1"><image xlink:href="https://example.com/a.png" width="100" height="100"/>'
                '<text style="mix-blend-mode: multiply">Hi</text></g></svg>',
                encoding='utf-8',
            )
            audit = inspect_svg(bad_svg)
            self.assertFalse(audit['no_external_dependencies'])
            self.assertFalse(audit['illustrator_compatible'])
            self.assertTrue(audit['illustrator_incompatible_features'])

    def test_overwrite_refused_before_any_output_is_written(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, ax = plt.subplots()
                stem = Path(d) / 'existing'
                stem.with_suffix('.svg').write_text('original')
                with self.assertRaises(FileExistsError):
                    export_figure(fig, stem, {'data_kind': 'synthetic', 'sources': [], 'transformations': []})
                self.assertFalse(stem.with_suffix('.pdf').exists())
                self.assertEqual(stem.with_suffix('.svg').read_text(), 'original')

    def test_missing_provenance_rejected(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            fig, ax = plt.subplots()
            with self.assertRaises(ValueError):
                export_figure(fig, Path(d) / 'missing', {})

    def test_bounds_audit_ignores_ticks_outside_view_but_catches_figure_text(self):
        from matplotlib.ticker import MultipleLocator
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4), layout='constrained')
                ax.plot([0, 1], [0, 1])
                ax.set_ylim(0, 1.05)
                ax.yaxis.set_major_locator(MultipleLocator(.25))
                provenance = {'data_kind': 'synthetic', 'sources': [], 'transformations': []}
                report = export_figure(fig, Path(d) / 'clean', provenance, dpi=100)
                self.assertEqual(report['checks']['text_outside_canvas'], [])
                fig.text(1.2, .5, 'outside')
                report = export_figure(fig, Path(d) / 'bad', provenance, dpi=100)
                self.assertIn('outside', report['checks']['text_outside_canvas'])

    def test_bounds_audit_catches_off_page_legend(self):
        with tempfile.TemporaryDirectory(dir=ROOT / '.cache') as d:
            prof = _available_profile(d)
            with style_context(profile=prof):
                fig, ax = plt.subplots(figsize=(90 / 25.4, 60 / 25.4))
                ax.plot([0, 1], [0, 1], label='Clipped legend')
                ax.legend(loc='upper left', bbox_to_anchor=(1.5, 1))
                report = export_figure(
                    fig,
                    Path(d) / 'legend',
                    {'data_kind': 'synthetic', 'sources': [], 'transformations': []},
                    dpi=100,
                )
                self.assertTrue(any('legend' in label.lower() for label in report['checks']['text_outside_canvas']))


if __name__ == '__main__':
    unittest.main()
