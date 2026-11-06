"""Portable templates change appearance without changing scientific mappings."""
from pathlib import Path
import copy
import json
import os
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'.cache/matplotlib')
(ROOT/'.cache').mkdir(exist_ok=True)
sys.path.insert(0,str(ROOT/'scripts'))
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import houseplot
from houseplot.profiles import load_profile, validate_profile, profile_fingerprint, compose_profile


class ProfileTests(unittest.TestCase):
    def tearDown(self):plt.close('all')

    def test_large_house_type_reaches_axes_legends_and_colorbars(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('single');ax=axes['A']
            ax.set(xlabel='Position',ylabel='Response')
            ax.plot([0,1],[0,1],label='Case');legend=ax.legend()
            image=ax.imshow([[0,1],[1,0]])
            cb=houseplot.add_colorbar(fig,image,ax,'Amplitude')
            houseplot.panel_label(ax,0)
            fig.canvas.draw()
            self.assertEqual(ax.xaxis.label.get_fontsize(),13)
            self.assertEqual(ax.get_xticklabels()[0].get_fontsize(),12)
            self.assertEqual(legend.get_texts()[0].get_fontsize(),11)
            self.assertEqual(ax.texts[0].get_fontsize(),14)
            self.assertEqual(cb.ax.yaxis.label.get_fontsize(),13)
            self.assertEqual(cb.ax.get_yticklabels()[0].get_fontsize(),12)

    def test_default_is_a_portable_versioned_times_profile(self):
        p=load_profile('house-times-v3')
        self.assertEqual(p['id'],'house-times-v3')
        self.assertEqual(p['rcparams']['font.family'],'Times New Roman')
        self.assertEqual(p['geometry']['single_width_mm'],90)
        self.assertNotRegex(json.dumps(p['source']),r'[A-Za-z]:[\\/]')

    def test_bundled_reference_paths_must_be_portable(self):
        for path in ['C:/example/private.png','C:private.png','../outside.png','/tmp/private.png']:
            p=load_profile();p['source']['references']=[{'path':path}]
            with self.subTest(path=path),self.assertRaises(ValueError):validate_profile(p)

    def test_template_changes_palette_and_size_but_not_field_values_or_norm(self):
        p=load_profile();p['id']='test-local';p['version']='1.0.0'
        p['series'][0]['color']='#602080';p['rcparams']['axes.labelsize']=11
        p['field_palettes']['signed']['name']='PuOr'
        p['geometry']['single_width_mm']=100
        original=matplotlib.rcParams['axes.labelsize']
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as d:
            file=Path(d)/'local.json';file.write_text(json.dumps(p),encoding='utf-8')
            with houseplot.style_context(profile=file):
                fig,ax=houseplot.make_layout('single')
                style=houseplot.series_style(0)
                self.assertEqual(style['color'],'#602080')
                self.assertEqual(matplotlib.rcParams['axes.labelsize'],11)
                self.assertAlmostEqual(fig.get_figwidth()*25.4,100)
                data=np.array([-2.,5.]);norm,cmap=houseplot.field_scale([data],'signed')
                self.assertEqual((norm.vmin,norm.vmax),(-5,5))
                self.assertEqual(cmap.name,'PuOr')
                np.testing.assert_equal(data,[-2,5])
            self.assertEqual(matplotlib.rcParams['axes.labelsize'],original)

    def test_templates_cannot_override_data_or_unsafe_rc_settings(self):
        base=load_profile()
        for field,value in [('normalization','per-panel-max'),('rcparams',{'text.usetex':True})]:
            p=copy.deepcopy(base);p[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_profile(p)

    def test_invalid_colors_and_wrong_phase_semantic_rejected(self):
        p=load_profile();p['series'][0]['color']='not-a-color'
        with self.assertRaises(ValueError):validate_profile(p)
        p=load_profile();p['field_palettes']['phase']['kind']='sequential'
        with self.assertRaises(ValueError):validate_profile(p)

    def test_profile_loads_are_independent_and_fingerprint_tracks_changes(self):
        a=load_profile();b=load_profile()
        self.assertEqual(profile_fingerprint(a),profile_fingerprint(b))
        a['series'][0]['color']='#123456'
        self.assertNotEqual(profile_fingerprint(a),profile_fingerprint(b))
        self.assertNotEqual(load_profile()['series'][0]['color'],'#123456')

    def test_export_records_the_actual_font_and_profile(self):
        p=load_profile();p['id']='test-dejavu';p['rcparams']['font.family']='DejaVu Sans'
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as d:
            path=Path(d)/'dejavu.json';path.write_text(json.dumps(p),encoding='utf-8')
            with houseplot.style_context(profile=path):
                fig,axes=houseplot.make_layout('single');axes['A'].plot([0,1],[0,1])
                report=houseplot.export_figure(fig,Path(d)/'font',{'data_kind':'synthetic','sources':[],'transformations':[]},dpi=100)
                self.assertEqual(report['profile']['id'],'test-dejavu')
                self.assertIn('dejavusans',report['font_file'].lower())
                self.assertTrue(report['checks']['configured_font_in_pdf'])
                self.assertFalse(report['checks']['times_font_in_pdf'])

    def test_composition_preserves_base_and_marks_new_style_as_draft(self):
        base=load_profile();old=profile_fingerprint(base)
        derived=compose_profile(base,profile_id='article-blue-v1',version='1.0.0',
                                patch={'rcparams':{'axes.labelsize':10}})
        self.assertEqual(derived['rcparams']['axes.labelsize'],10)
        self.assertEqual(derived['rcparams']['font.family'],'Times New Roman')
        self.assertEqual(derived['status'],'draft')
        self.assertEqual(old,profile_fingerprint(base))
        with self.assertRaises(ValueError):
            compose_profile(base,profile_id='bad-v1',version='1.0.0',patch={'normalization':'per-panel'})

    def test_layout_keeps_template_identity_when_exported_after_context_exit(self):
        p=load_profile();p['id']='test-bound';p['rcparams']['font.family']='DejaVu Sans'
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as d:
            path=Path(d)/'bound.json';path.write_text(json.dumps(p),encoding='utf-8')
            with houseplot.style_context(profile=path):
                fig,axes=houseplot.make_layout('single');axes['A'].plot([0,1],[0,1])
            report=houseplot.export_figure(fig,Path(d)/'outside',{'data_kind':'synthetic','sources':[],'transformations':[]},dpi=100)
            self.assertEqual(report['profile']['id'],'test-bound')
            self.assertIn('dejavusans',report['font_file'].lower())

    def test_plain_matplotlib_figure_keeps_profile_after_scope_exit(self):
        p=load_profile();p['id']='test-plain';p['rcparams']['font.family']='DejaVu Sans'
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as d:
            path=Path(d)/'plain-profile.json';path.write_text(json.dumps(p),encoding='utf-8')
            with houseplot.style_context(profile=path):
                fig,ax=plt.subplots(figsize=(3,2));ax.plot([0,1],[0,1])
            report=houseplot.export_figure(fig,Path(d)/'plain',{'data_kind':'synthetic','sources':[],'transformations':[]},dpi=100)
            self.assertEqual(report['profile']['id'],'test-plain')
            self.assertTrue(report['checks']['configured_font_in_pdf'])

    def test_composition_keeps_reference_evidence(self):
        base=load_profile();base['source']['references']=[{'path':'assets/evidence/crop.png','sha256':'abc'}]
        base['source']['observations'].append({'parameter':'line.width','evidence':'estimated','value':1.2})
        derived=compose_profile(base,profile_id='with-evidence-v1',version='1.0.0',patch={'rcparams':{'axes.labelsize':10}})
        self.assertEqual(derived['source']['references'],base['source']['references'])
        self.assertTrue(any(obs['parameter']=='line.width' for obs in derived['source']['observations']))

    def test_custom_colormap_requires_serialized_nodes(self):
        from matplotlib.colors import LinearSegmentedColormap
        name='test_profile_temporary_map'
        matplotlib.colormaps.register(LinearSegmentedColormap.from_list(name,['white','navy']))
        try:
            p=load_profile();p['field_palettes']['magnitude']['name']=name
            with self.assertRaises(ValueError):validate_profile(p)
        finally:matplotlib.colormaps.unregister(name)
        p['field_palettes']['magnitude']['colors']=['#FFFFFF','#000080']
        with tempfile.TemporaryDirectory(dir=ROOT/'.cache') as d:
            path=Path(d)/'nodes.json';path.write_text(json.dumps(p),encoding='utf-8')
            with houseplot.style_context(profile=path):
                norm,cmap=houseplot.field_scale([np.array([0.,1.])],'magnitude')
                np.testing.assert_allclose(cmap(1.),[0,0,128/255,1])
