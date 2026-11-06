import numpy as np
import matplotlib as mpl
from .profiles import profile_colormap


def plot_curve(ax, x, y, *, log_y=False, **kwargs):
    """Keep continuation order and gaps; call once per physical branch."""
    x = np.ma.asarray(x, dtype=float).filled(np.nan)
    y = np.ma.asarray(y, dtype=float).filled(np.nan)
    if x.ndim != 1 or y.ndim != 1 or len(x) != len(y) or not len(x):
        raise ValueError('Curve x and y must be non-empty equally sized 1-D arrays')
    finite = np.isfinite(x) & np.isfinite(y)
    nonpositive = finite & (y <= 0) if log_y else np.zeros(y.shape, dtype=bool)
    valid = finite & ~nonpositive
    if not np.any(valid):
        raise ValueError('No drawable observations for the selected scale')
    draw_x, draw_y = x.copy(), y.copy()
    draw_x[~finite], draw_y[~valid] = np.nan, np.nan
    if log_y:
        ax.set_yscale('log')
    line, = ax.plot(draw_x, draw_y, **kwargs)
    return line, {'rows':len(x), 'nonfinite':int((~finite).sum()),
                  'nonpositive':int(nonpositive.sum()), 'drawable':int(valid.sum()),
                  'order':'input order retained; invalid observations are gaps'}


def field_scale(arrays, kind):
    """One semantic normalization across all supplied comparable fields.

    `phase` is wrapped phase in radians; undefined low-magnitude phase must
    already be masked by the caller using a documented threshold.
    """
    if kind not in ('magnitude','signed','phase','level'):
        raise ValueError(f'Unknown field semantic: {kind}')
    parts = [np.ma.asarray(a, dtype=float).compressed() for a in arrays]
    finite = np.concatenate(parts) if parts else np.array([])
    finite = finite[np.isfinite(finite)]
    if not finite.size:
        raise ValueError('No finite field values')
    if kind=='level':
        lo,hi=float(finite.min()),float(finite.max())
        if lo==hi:
            delta=max(1.,abs(lo))*.01
            lo,hi=lo-delta,hi+delta
        norm=mpl.colors.Normalize(lo,hi,clip=False)
    elif kind == 'magnitude':
        if finite.min() < 0:
            raise ValueError('Negative values cannot be encoded as a magnitude')
        norm = mpl.colors.Normalize(0, float(finite.max()) or 1., clip=False)
    elif kind == 'signed':
        bound = float(np.max(np.abs(finite))) or 1.
        norm = mpl.colors.TwoSlopeNorm(vmin=-bound, vcenter=0, vmax=bound)
    else:
        if finite.min() < -np.pi-1e-12 or finite.max() > np.pi+1e-12:
            raise ValueError('Wrapped phase must lie in [-pi, pi] radians')
        norm = mpl.colors.Normalize(-np.pi, np.pi, clip=False)
    cmap=profile_colormap('magnitude' if kind=='level' else kind)
    return norm, cmap.with_extremes(bad='#D0D0D0')


def rounded_level_scale(arrays,*,quantum=5.,max_ticks=6):
    """Outward-rounded scalar-level display; all ticks are quantum multiples.

    Use an explicit physical quantum (for example 5 dB for SPL), not on
    arbitrary small amplitudes, phase or logarithmic normalization.
    """
    if not np.isfinite(quantum) or quantum<=0:raise ValueError('quantum must be finite and positive')
    if type(max_ticks) is not int or not 2<=max_ticks<=12:raise ValueError('max_ticks must lie between 2 and 12')
    parts=[np.ma.asarray(a,dtype=float).compressed() for a in arrays]
    data=np.concatenate(parts) if parts else np.array([])
    data=data[np.isfinite(data)]
    if not len(data):raise ValueError('No finite level values')
    raw_lo,raw_hi=float(data.min()),float(data.max())
    span=max(raw_hi-raw_lo,quantum)
    base=10.**np.floor(np.log10(max(span/(max_ticks-1)/quantum,1.)))
    multipliers=np.unique(np.maximum(1,np.rint(base*np.array([.1,.2,.5,1,2,2.5,3,4,5,6,7.5,8,10,15,20,25,50,100]))))
    choices=[]
    for multiple in multipliers:
        step=float(quantum*multiple)
        lo=float(step*np.floor(raw_lo/step));hi=float(step*np.ceil(raw_hi/step))
        if hi==lo:hi=lo+step
        count=int(round((hi-lo)/step))+1
        if 2<=count<=max_ticks:
            choices.append(((raw_lo-lo)+(hi-raw_hi),abs(count-5),step,lo,hi,count))
    if not choices:raise ValueError('No readable rounded scale; choose another quantum')
    _,_,step,lo,hi,count=min(choices)
    ticks=lo+np.arange(count)*step
    _,cmap=field_scale([data],'level')
    norm=mpl.colors.Normalize(lo,hi,clip=False)
    report={'observed_limits':[raw_lo,raw_hi],'display_limits':[lo,hi],
            'quantum':float(quantum),'tick_step':step,'ticks':ticks.tolist(),
            'no_data_clipping':lo<=raw_lo and hi>=raw_hi}
    return norm,cmap,ticks,report
