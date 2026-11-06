import math
import copy
import matplotlib as mpl
import matplotlib.pyplot as plt
from .profiles import current_profile


def make_layout(name, *, width_mm=None, rows=2, cols=2):
    """Create exact-size canvases. Returned axes are in reading/panel order."""
    if width_mm is None:
        width_mm=current_profile()['geometry']['single_width_mm' if name=='single' else 'combination_width_mm']
    if not math.isfinite(width_mm) or width_mm <= 0:
        raise ValueError('width_mm must be finite and positive')
    if name in ('main_side','mixed') and width_mm<150:
        raise ValueError('Fixed main_side/mixed presets require at least 150 mm; use a custom grid for narrower figures')
    specs = {
        'single': ([['A']], .70, {}),
        'row3': ([['A','B','C']], .36, {}),
        'column3': ([['A'],['B'],['C']], 1.45, {}),
        'matrix2x3': ([['A','B','C'],['D','E','F']], .67, {}),
        'overview': ([['A','A','A'],['B','C','D']], .77, {'height_ratios':[.9,1.1]}),
        'main_side': ([['A','B'],['A','C']], .68, {'width_ratios':[1.25,1]}),
        'mixed': ([['A','B'],['C','D']], .71, {}),
    }
    if name == 'grid':
        if not isinstance(rows,int) or not isinstance(cols,int) or rows<1 or cols<1 or rows*cols>26:
            raise ValueError('Grid needs positive integer rows/cols and at most 26 panels')
        mosaic=[[chr(65+r*cols+c) for c in range(cols)] for r in range(rows)]
        specs['grid']=(mosaic,.70*rows/cols,{})
    if name in ('main_side','mixed'):
        # Fixed physical panel boxes preserve equal-aspect spatial geometry.
        # Reserve the colorbar gutter without stealing width from a panel.
        height_mm=width_mm*(100/180 if name=='main_side' else 136/180)
        fig=plt.figure(figsize=(width_mm/25.4,height_mm/25.4))
        fig.set_layout_engine('none')
        if name=='main_side':
            boxes={'A':(14,16,74,74),'B':(118,61,56,29),'C':(118,16,56,29)}
            nominal_height=100
        else:
            boxes={'A':(14,80,78,46),'B':(114,80,46,46),
                   'C':(14,16,78,46),'D':(114,16,46,46)}
            nominal_height=136
        # Larger tick and label fonts need a wider decoration gutter. Preserve
        # the field/polar box sizes and their shared column alignment.
        gutter_mm=20+max(0,float(mpl.rcParams['ytick.labelsize'])-8)*1.25
        right_shift=max(0,gutter_mm-width_mm/9)/width_mm if name=='mixed' else 0
        axes={key:fig.add_axes([x/180-(right_shift if key in ('B','D') and name=='mixed' else 0),
                               y/nominal_height,w/180,h/nominal_height],
                              projection='polar' if name=='mixed' and key=='D' else None)
              for key,(x,y,w,h) in boxes.items()}
    elif name == 'nested':
        fig=plt.figure(figsize=(width_mm/25.4,width_mm*.68/25.4),layout='constrained')
        outer=fig.add_gridspec(1,2,wspace=.12)
        axes={}
        for col, keys in enumerate([('A','B'),('C','D')]):
            inner=outer[0,col].subgridspec(2,1,hspace=.05)
            for row,key in enumerate(keys):
                axes[key]=fig.add_subplot(inner[row,0])
    elif name in specs:
        mosaic, ratio, kw = specs[name]
        subplot_kw={'D':{'projection':'polar'}} if name=='mixed' else None
        fig,axes=plt.subplot_mosaic(mosaic,figsize=(width_mm/25.4,width_mm*ratio/25.4),
                                   layout='constrained',gridspec_kw=kw,
                                   per_subplot_kw=subplot_kw)
    else:
        raise ValueError(f'Unknown layout: {name}')
    engine=fig.get_layout_engine()
    if engine is not None and hasattr(engine,'set'):
        engine.set(w_pad=.045,h_pad=.045,wspace=.06,hspace=.075)
    fig._houseplot_panel_axes=axes
    fig._houseplot_profile=copy.deepcopy(current_profile())
    fig._houseplot_font_family=mpl.rcParams['font.family'][0]
    return fig,axes
