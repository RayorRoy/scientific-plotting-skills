"""Explicit export plus measured metadata. No publisher acceptance claims."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import platform
import tempfile

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.legend import Legend
from PIL import Image
import pymupdf
from .profiles import current_profile, profile_fingerprint


def _sha(path):
    digest=hashlib.sha256()
    with open(path,'rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            digest.update(block)
    return digest.hexdigest()


def _json(value):
    if isinstance(value,Path): return str(value)
    if hasattr(value,'tolist'): return value.tolist()
    raise TypeError(f'Cannot serialize {type(value).__name__}')


def export_figure(fig, stem, provenance, *, dpi=600, overwrite=False):
    """Preserve page dimensions; preflight overwrite; publish each output atomically.

    A complete multi-format export is not transactional. The manifest lists
    only completed files. SVG retains text and requires Times on the reader.
    """
    required={'data_kind','sources','transformations'}
    if not required.issubset(provenance):
        raise ValueError(f'Provenance must include {sorted(required)}')
    if provenance['data_kind'] not in ('synthetic','simulation','experiment'):
        raise ValueError('data_kind must be synthetic, simulation or experiment')
    if not isinstance(dpi,(int,float)) or not 0 < dpi <= 2400:
        raise ValueError('dpi must be positive and at most 2400')
    stem=Path(stem)
    targets={fmt:stem.with_suffix('.'+fmt) for fmt in ('pdf','svg','png','json')}
    preview=stem.with_suffix('.preview.png')
    for path in [*targets.values(),preview]:
        if path.exists() and not overwrite:
            raise FileExistsError(path)
    stem.parent.mkdir(parents=True,exist_ok=True)
    width,height=fig.get_size_inches()*25.4
    versions={name:importlib.metadata.version(name) for name in ('numpy','matplotlib','pillow','pymupdf')}
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    canvas=fig.bbox
    outside=[]
    hidden_tick_labels=set()
    for ax in fig.axes:
        for axis in (ax.xaxis,ax.yaxis):
            lo,hi=sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks()+axis.get_minor_ticks():
                if not lo-1e-10 <= tick.get_loc() <= hi+1e-10:
                    hidden_tick_labels.update((id(tick.label1),id(tick.label2)))
    for item in fig.findobj(match=Text):
        # Tick labels outside the displayed data interval are intentionally hidden by axes.
        if not item.get_visible() or not item.get_text().strip(): continue
        if id(item) in hidden_tick_labels: continue
        box=item.get_window_extent(renderer)
        if box.width>0 and box.height>0 and (box.x0<canvas.x0-1 or box.y0<canvas.y0-1 or box.x1>canvas.x1+1 or box.y1>canvas.y1+1):
            outside.append(item.get_text())
    for legend in fig.findobj(match=Legend):
        if not legend.get_visible(): continue
        box=legend.get_window_extent(renderer)
        if box.x0<canvas.x0-1 or box.y0<canvas.y0-1 or box.x1>canvas.x1+1 or box.y1>canvas.y1+1:
            outside.append('[legend bounding box]')
    selected=getattr(fig,'_houseplot_profile',current_profile())
    family=getattr(fig,'_houseplot_font_family',mpl.rcParams['font.family'][0])
    report={'size_mm':[float(width),float(height)],'dpi':dpi,
            'font_file':font_manager.findfont(font_manager.FontProperties(family=[family]),fallback_to_default=False),
            'profile':{'id':selected['id'],'version':selected['version'],'sha256':profile_fingerprint(selected),'snapshot':selected},
            'versions':versions,'python':platform.python_version(),'provenance':provenance,
            'checks':{'text_outside_canvas':outside},'outputs':{},
            'limitations':['No automated scientific or publisher compliance certification',
                          'SVG text requires fonts on the viewing system',
                          'Text bounds do not detect all inter-artist overlaps or raster detail loss']}
    package=Path(__file__).resolve().parents[2]
    report['helper_code_sha256']={str(p.relative_to(package)):_sha(p)
        for p in sorted((package/'scripts/houseplot').glob('*.py'))}
    report['helper_code_sha256']['assets/times.mplstyle']=_sha(package/'assets/times.mplstyle')
    def geometry_box(ax):
        box=ax.get_position()
        return {'x_mm':float(box.x0*width),'y_mm':float(box.y0*height),
                'width_mm':float(box.width*width),'height_mm':float(box.height*height)}
    report['geometry']={
        'panels':{name:geometry_box(ax) for name,ax in getattr(fig,'_houseplot_panel_axes',{}).items()},
        'colorbars':[dict(geometry_box(cb.ax),ticks=[float(t) for t in cb.get_ticks()])
                     for cb in getattr(fig,'_houseplot_colorbars',[])]}
    for fmt in ('pdf','svg','png'):
        fd,temp=tempfile.mkstemp(prefix='.export-',suffix='.'+fmt,dir=stem.parent)
        os.close(fd)
        try:
            with mpl.rc_context({'savefig.bbox':None,'svg.fonttype':'none','pdf.fonttype':42}):
                fig.savefig(temp,format=fmt,dpi=dpi,bbox_inches=None,facecolor='white',transparent=False)
            os.replace(temp,targets[fmt])
        finally:
            if os.path.exists(temp): os.unlink(temp)
        report['outputs'][fmt]={'file':targets[fmt].name,'bytes':targets[fmt].stat().st_size,'sha256':_sha(targets[fmt])}
    with Image.open(targets['png']) as im:
        actual_dpi=im.info.get('dpi')
        report['raster']={'pixels':list(im.size),'dpi':actual_dpi,'mode':im.mode}
        pixel_ok=all(abs(a-b)<1.1 for a,b in zip(im.size,(width/25.4*dpi,height/25.4*dpi)))
    with pymupdf.open(targets['pdf']) as doc:
        page=doc[0]
        actual_mm=[page.rect.width*25.4/72,page.rect.height*25.4/72]
        fonts=[]
        for f in page.get_fonts(full=True):
            fonts.append({'name':f[3],'type':f[2],'embedded':bool(doc.extract_font(f[0])[3])})
        report['pdf']={'size_mm':actual_mm,'fonts':fonts,'raster_images':len(page.get_images())}
        page.get_pixmap(matrix=pymupdf.Matrix(140/72,140/72),alpha=False).save(preview)
    report['checks']['page_dimensions']=pixel_ok and all(abs(a-b)<.02 for a,b in zip(actual_mm,[width,height]))
    report['checks']['pdf_fonts_embedded']=bool(fonts) and all(f['embedded'] for f in fonts)
    report['checks']['times_font_in_pdf']=any('TimesNewRoman' in f['name'] for f in fonts)
    actual_name=font_manager.FontProperties(fname=report['font_file']).get_name()
    normalize=lambda s:''.join(c.lower() for c in s if c.isalnum())
    report['checks']['configured_font_in_pdf']=any(normalize(actual_name) in normalize(f['name']) for f in fonts)
    report['preview']=preview.name
    fd,temp=tempfile.mkstemp(prefix='.manifest-',suffix='.json',dir=stem.parent)
    os.close(fd)
    try:
        Path(temp).write_text(json.dumps(report,ensure_ascii=False,indent=2,default=_json,allow_nan=False),encoding='utf-8')
        os.replace(temp,targets['json'])
    finally:
        if os.path.exists(temp): os.unlink(temp)
    return report
