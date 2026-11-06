"""Colorbars with measured physical width and live alignment to field axes."""
import numpy as np
import matplotlib as mpl
import matplotlib.ticker as ticker
from matplotlib.transforms import Bbox
from .profiles import current_profile


class _AlignedBar:
    def __init__(self,fig,axes,width_mm,gap_mm):
        self.fig,self.axes,self.width_mm,self.gap_mm=fig,axes,width_mm,gap_mm

    def __call__(self,ax,renderer):
        bounds=Bbox.union([a.get_position() for a in self.axes])
        fig_width_mm=self.fig.get_figwidth()*25.4
        return Bbox.from_bounds(bounds.x1+self.gap_mm/fig_width_mm,bounds.y0,
                                self.width_mm/fig_width_mm,bounds.height)


def add_colorbar(fig,mappable,axes,label,*,kind=None,width_mm=None,gap_mm=None,allow_multirow=False):
    """Attach a vertical bar without resizing the associated field axes.

    Height equals the actual panel/row height. Disjoint rows require separate
    bars by default; explicit allow_multirow is reserved for a requested design.
    Linear and wrapped-phase
    bars have five major labels; log bars use up to five in-range decades,
    falling back to three log-spaced ticks for a narrow non-decade range.
    """
    geom=current_profile()['geometry']
    if width_mm is None:width_mm=geom['colorbar_width_mm']
    if gap_mm is None:gap_mm=geom['colorbar_gap_mm']
    hosts=[axes] if hasattr(axes,'get_position') else list(axes)
    if not hosts or any(a.figure is not fig for a in hosts):
        raise ValueError('Colorbar hosts must belong to the supplied Figure')
    boxes=[a.get_position() for a in hosts]
    if len(hosts)>1 and max(b.y0 for b in boxes)>=min(b.y1 for b in boxes)-1e-9 and not allow_multirow:
        raise ValueError('Use one colorbar per panel or per row; a bar spanning disjoint rows needs explicit allow_multirow=True')
    if not np.isfinite(width_mm) or width_mm<=0 or not np.isfinite(gap_mm) or gap_mm<0:
        raise ValueError('Colorbar width must be positive and gap nonnegative')
    anchor=max(hosts,key=lambda a:a.get_position().x1)
    # Child axes are included in the host tight bbox for constrained layout.
    cax=anchor.inset_axes([1.05,0,.05,1])
    cax.set_axes_locator(_AlignedBar(fig,hosts,width_mm,gap_mm))
    cb=fig.colorbar(mappable,cax=cax)
    cb.set_label(label,labelpad=3,fontsize=mpl.rcParams['axes.labelsize'])
    norm=mappable.norm
    if kind=='phase':
        cb.set_ticks([-np.pi,-np.pi/2,0,np.pi/2,np.pi],
                     labels=['$-\\pi$','$-\\pi/2$','0','$\\pi/2$','$\\pi$'])
    elif isinstance(norm,mpl.colors.LogNorm):
        powers=np.arange(np.ceil(np.log10(norm.vmin)),np.floor(np.log10(norm.vmax))+1)
        ticks=10.**powers
        if len(ticks)>5:
            step=int(np.ceil((powers[-1]-powers[0])/4))
            start=np.ceil(powers[0]/step)*step
            ticks=10.**np.arange(start,powers[-1]+1,step)
        if len(ticks)<2:
            ticks=np.unique(np.geomspace(norm.vmin,norm.vmax,3))
            for precision in range(3,18):
                labels=[f'{v:.{precision}g}' for v in ticks]
                if len(set(labels))==len(ticks):break
            cb.set_ticks(ticks,labels=labels)
        else:
            cb.set_ticks(ticks)
            cb.formatter=ticker.LogFormatterMathtext(base=10)
            cb.update_ticks()
    else:
        cb.set_ticks(np.linspace(norm.vmin,norm.vmax,5))
        formatter=ticker.ScalarFormatter(useMathText=True,useOffset=False)
        formatter.set_powerlimits((-3,3))
        cb.formatter=formatter
        cb.update_ticks()
    cb.minorticks_off()
    cb.ax.tick_params(which='major',labelsize=mpl.rcParams['ytick.labelsize'],length=geom.get('colorbar_tick_length_pt',2),width=.6,pad=2)
    cb.outline.set_linewidth(.65)
    cb.ax.yaxis.get_offset_text().set_fontsize(mpl.rcParams['ytick.labelsize'])
    if not hasattr(fig,'_houseplot_colorbars'):fig._houseplot_colorbars=[]
    fig._houseplot_colorbars.append(cb)
    return cb
