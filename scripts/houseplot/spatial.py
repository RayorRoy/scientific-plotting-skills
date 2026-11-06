"""Small spatial-data adapters with explicit missingness and normalization."""
import numpy as np


def _real(values):
    if np.iscomplexobj(values):raise ValueError('Choose a real physical quantity before plotting')
    return np.ma.asarray(values,dtype=float).filled(np.nan)


def rectilinear_grid(x,z,values,*,max_cells=2_000_000):
    """Place samples without interpolation; reject duplicates and huge sparse pivots."""
    x,z,values=map(_real,(x,z,values))
    if x.ndim!=1 or z.shape!=x.shape or values.shape!=x.shape or not x.size:
        raise ValueError('Grid inputs must be equally sized nonempty 1-D arrays')
    if not np.isfinite(x).all() or not np.isfinite(z).all():raise ValueError('Invalid spatial coordinates')
    gx,ix=np.unique(x,return_inverse=True);gz,iz=np.unique(z,return_inverse=True)
    if type(max_cells) is not int or max_cells<1 or len(gx)*len(gz)>max_cells:
        raise ValueError('Grid would exceed max_cells; use an appropriate unstructured mesh representation')
    ids=iz*len(gx)+ix
    if np.unique(ids).size!=ids.size:raise ValueError('Duplicate spatial coordinates require a scientific decision')
    grid=np.full((len(gz),len(gx)),np.nan)
    grid[iz,ix]=values
    return gx,gz,grid


def pressure_level(pressure_rms_pa,*,reference_pa):
    """SPL in dB; zero/negative/nonfinite RMS values stay undefined, never floored."""
    if not np.isfinite(reference_pa) or reference_pa<=0:raise ValueError('reference_pa must be finite and positive')
    p=_real(pressure_rms_pa);finite=np.isfinite(p);valid=finite & (p>0)
    result=np.full(p.shape,np.nan)
    result[valid]=20*(np.log10(p[valid])-np.log10(reference_pa))
    return result,{'reference_pa':float(reference_pa),'nonfinite':int((~finite).sum()),
                   'nonpositive':int((finite & (p<=0)).sum()),'formula':'20 log10(p_rms / reference_pa); no floor'}


def unit_vectors(u,v):
    """Direction-only arrows; preserve zero and missing vectors as undefined."""
    u,v=map(_real,(u,v))
    if u.shape!=v.shape:raise ValueError('Vector component shapes differ')
    magnitude=np.hypot(u,v)
    valid=np.isfinite(magnitude) & (magnitude>0)
    out_u,out_v=np.full(u.shape,np.nan),np.full(v.shape,np.nan)
    np.divide(u,magnitude,out=out_u,where=valid)
    np.divide(v,magnitude,out=out_v,where=valid)
    return out_u,out_v,{'undefined':int((~valid).sum()),'normalization':'each nonzero finite vector divided by its own magnitude; directions only'}
