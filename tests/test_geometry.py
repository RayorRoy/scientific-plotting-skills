"""Rendered geometry contracts from the user's four visual corrections."""
from pathlib import Path
import os
import sys
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


class GeometryTests(unittest.TestCase):
    def tearDown(self):
        plt.close('all')

    def field(self,ax):
        x=np.linspace(-1,1,11)
        norm,cmap=houseplot.field_scale([np.outer(x,x)],'signed')
        im=ax.pcolormesh(x,x,np.outer(x,x),norm=norm,cmap=cmap)
        ax.set(xlabel='$x/L$',ylabel='$z/L$',aspect='equal')
        return im

    def test_main_field_spans_the_full_two_panel_height(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('main_side')
            im=self.field(axes['A'])
            houseplot.add_colorbar(fig,im,axes['A'],'$q/q_0$')
            for key in ['B','C']:
                axes[key].plot([0,1],[0,1]);axes[key].set(xlabel='Frequency (Hz)',ylabel='Response')
            fig.canvas.draw()
            a,b,c=[axes[k].get_window_extent() for k in ['A','B','C']]
            self.assertLess(abs(a.y1-b.y1)/fig.dpi*25.4,.2)
            self.assertLess(abs(a.y0-c.y0)/fig.dpi*25.4,.2)
            self.assertAlmostEqual(a.width,a.height,delta=.2)

    def test_mixed_field_and_polar_plot_boxes_align(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('mixed')
            im=self.field(axes['B'])
            houseplot.add_colorbar(fig,im,axes['B'],'$q/q_0$')
            axes['D'].plot([0,1,2],[1,2,1])
            fig.canvas.draw()
            b,d=[axes[k].get_window_extent() for k in ['B','D']]
            self.assertLess(abs(b.x0-d.x0)/fig.dpi*25.4,.2)
            self.assertLess(abs(b.x1-d.x1)/fig.dpi*25.4,.2)
            self.assertLess(abs(b.height-d.height)/fig.dpi*25.4,.2)

    def test_panel_label_is_outside_above_and_to_left(self):
        with houseplot.style_context():
            fig,ax=plt.subplots(figsize=(4,3),layout='constrained')
            houseplot.panel_label(ax,0)
            fig.canvas.draw()
            label=next(t for t in ax.texts if t.get_text()=='(a)')
            text=label.get_window_extent(fig.canvas.get_renderer());box=ax.get_window_extent()
            self.assertLess(text.x0,box.x0)
            self.assertGreater(text.y0,box.y1)

    def test_panel_name_is_hidden_by_default_but_letter_remains(self):
        with houseplot.style_context():
            fig,ax=plt.subplots()
            houseplot.panel_label(ax,0,'W5: 200.034 Hz')
            self.assertEqual([t.get_text() for t in ax.texts],['(a)'])

    def test_panel_name_can_be_explicitly_enabled(self):
        with houseplot.style_context():
            fig,ax=plt.subplots()
            houseplot.panel_label(ax,0,'W5: 200.034 Hz',show_subtitle=True)
            self.assertIn('W5: 200.034 Hz',[t.get_text() for t in ax.texts])

    def test_colorbar_width_height_and_five_linear_ticks(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('single')
            im=self.field(axes['A'])
            cb=houseplot.add_colorbar(fig,im,axes['A'],'$q/q_0$')
            fig.canvas.draw();fig.canvas.draw()
            bar=cb.ax.get_window_extent();plot=axes['A'].get_window_extent()
            self.assertAlmostEqual(bar.width/fig.dpi*25.4,3.0,delta=.05)
            self.assertAlmostEqual(bar.y0,plot.y0,delta=.5)
            self.assertAlmostEqual(bar.y1,plot.y1,delta=.5)
            np.testing.assert_allclose(cb.get_ticks(),[-1,-.5,0,.5,1])
            self.assertEqual(len(cb.ax.yaxis.get_minorticklocs()),0)
            self.assertTrue(all(line.get_markersize()==0 for line in cb.ax.yaxis.get_ticklines()))
            self.assertTrue(any(t.get_text() for t in cb.ax.get_yticklabels()))

    def test_shared_colorbar_tracks_actual_field_height(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('row3')
            for ax in axes.values():im=self.field(ax)
            cb=houseplot.add_colorbar(fig,im,list(axes.values()),'$q/q_0$')
            fig.canvas.draw();fig.canvas.draw()
            bar=cb.ax.get_window_extent()
            for ax in axes.values():
                box=ax.get_window_extent()
                self.assertAlmostEqual(bar.y0,box.y0,delta=.6)
                self.assertAlmostEqual(bar.y1,box.y1,delta=.6)

    def test_phase_and_log_colorbar_ticks_are_bounded_and_explicit(self):
        from matplotlib.colors import LogNorm
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('row3')
            norm,cmap=houseplot.field_scale([np.array([-np.pi,np.pi])],'phase')
            im=axes['A'].imshow([[0,1],[2,3]],norm=norm,cmap=cmap)
            phase=houseplot.add_colorbar(fig,im,axes['A'],'Phase (rad)',kind='phase')
            np.testing.assert_allclose(phase.get_ticks(),[-np.pi,-np.pi/2,0,np.pi/2,np.pi])
            im=axes['B'].imshow([[.025,1],[10,140]],norm=LogNorm(.025,140))
            log=houseplot.add_colorbar(fig,im,axes['B'],'Pressure (kPa)')
            self.assertGreaterEqual(len(log.get_ticks()),3)
            self.assertLessEqual(len(log.get_ticks()),5)
            self.assertTrue(all(.025<=v<=140 for v in log.get_ticks()))

    def test_mixed_colorbar_label_stays_on_page(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('mixed')
            im=self.field(axes['B']);im.set_clim(-.698,.698)
            cb=houseplot.add_colorbar(fig,im,axes['B'],'$q/q_0$')
            fig.canvas.draw()
            box=cb.ax.yaxis.label.get_window_extent(fig.canvas.get_renderer())
            self.assertLessEqual(box.x1,fig.bbox.x1)

    def test_log_colorbar_decade_intervals_are_uniform(self):
        from matplotlib.colors import LogNorm
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('single')
            im=axes['A'].imshow([[.001,1],[10,100]],norm=LogNorm(.001,100))
            cb=houseplot.add_colorbar(fig,im,axes['A'],'Pressure (kPa)')
            steps=np.diff(np.log10(cb.get_ticks()))
            self.assertGreaterEqual(len(steps),2)
            np.testing.assert_allclose(steps,np.repeat(steps[0],len(steps)))

    def test_narrow_log_labels_keep_distinct_values(self):
        from matplotlib.colors import LogNorm
        for lo,hi in [(1,1.001),(99.99,100.01)]:
            with self.subTest(lo=lo),houseplot.style_context():
                fig,axes=houseplot.make_layout('single')
                im=axes['A'].imshow([[lo,hi]],norm=LogNorm(lo,hi))
                cb=houseplot.add_colorbar(fig,im,axes['A'],'Value')
                fig.canvas.draw()
                labels=[t.get_text() for t in cb.ax.get_yticklabels()]
                self.assertEqual(len(set(labels)),len(cb.get_ticks()))

    def test_mixed_150mm_preserves_colorbar_label_space(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('mixed',width_mm=150)
            im=self.field(axes['B']);im.set_clim(-.698,.698)
            cb=houseplot.add_colorbar(fig,im,axes['B'],'$q/q_0$')
            fig.canvas.draw()
            box=cb.ax.yaxis.label.get_window_extent(fig.canvas.get_renderer())
            self.assertLessEqual(box.x1,fig.bbox.x1)
            self.assertAlmostEqual(axes['B'].get_position().x0,axes['D'].get_position().x0)

    def test_fixed_combinations_reject_widths_too_small_for_their_decorations(self):
        for layout in ['main_side','mixed']:
            with self.subTest(layout=layout),self.assertRaises(ValueError):
                houseplot.make_layout(layout,width_mm=120)

    def test_colorbar_does_not_silently_span_disjoint_rows(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('grid',rows=2,cols=2)
            for ax in axes.values():im=self.field(ax)
            with self.assertRaises(ValueError):
                houseplot.add_colorbar(fig,im,list(axes.values()),'Level')

    def test_row_colorbars_preserve_positions_and_joint_mapping(self):
        with houseplot.style_context():
            fig,axes=houseplot.make_layout('grid',rows=2,cols=2)
            fig.set_layout_engine('none');fig.set_size_inches(180/25.4,166/25.4)
            boxes=[(18,94,58,58),(96,94,58,58),(18,17,58,58),(96,17,58,58)]
            for ax,(x,y,w,h) in zip(axes.values(),boxes):
                ax.set_position([x/180,y/166,w/180,h/166])
            before={k:ax.get_position().bounds for k,ax in axes.items()}
            images=[self.field(ax) for ax in axes.values()]
            images[1].set_norm(images[3].norm)
            top=houseplot.add_colorbar(fig,images[1],[axes['A'],axes['B']],'Level')
            bottom=houseplot.add_colorbar(fig,images[3],[axes['C'],axes['D']],'Level')
            fig.canvas.draw()
            for key,ax in axes.items():np.testing.assert_allclose(ax.get_position().bounds,before[key],atol=1e-12)
            for cb in (top,bottom):
                self.assertAlmostEqual(cb.ax.get_position().height*166,58,places=6)
                self.assertAlmostEqual(cb.ax.get_position().width*180,3.0,places=6)
            self.assertIs(top.norm,bottom.norm)
            np.testing.assert_equal(top.get_ticks(),bottom.get_ticks())
