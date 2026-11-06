from contextlib import contextmanager
from pathlib import Path
import copy

import matplotlib as mpl
from matplotlib import font_manager
import matplotlib.pyplot as plt
from .profiles import profile_context, current_profile

COLORS = ('#0072B2', '#D55E00', '#009E73', '#7A5195', '#A67600', '#333333')
ASSETS = Path(__file__).resolve().parents[2] / 'assets'


@contextmanager
def style_context(overrides=None,*,profile=None):
    """Scope style changes and require the user's actual font, never a silent fallback."""
    with profile_context(profile) as selected:
        font_manager.findfont(selected['rcparams']['font.family'],fallback_to_default=False)
        with mpl.rc_context(fname=ASSETS / 'times.mplstyle'):
            mpl.rcParams.update(selected['rcparams'])
            mpl.rcParams['axes.prop_cycle']=mpl.cycler(color=[s['color'] for s in selected['series']])
            if overrides:mpl.rcParams.update(overrides)
            def figures():
                numbers=plt.get_fignums()
                active=plt.gcf().number if numbers else None
                result=[plt.figure(n) for n in numbers]
                if active is not None:plt.figure(active)
                return result
            before={id(fig) for fig in figures()}
            try:yield
            finally:
                for fig in figures():
                    if id(fig) not in before and not hasattr(fig,'_houseplot_profile'):
                        fig._houseplot_profile=copy.deepcopy(selected)
                        fig._houseplot_font_family=mpl.rcParams['font.family'][0]


def panel_label(ax, index, subtitle=None, *, show_subtitle=False):
    """Place letter IDs; descriptive panel names are explicitly opt-in."""
    label = chr(ord('a') + index) if isinstance(index, int) else str(index)
    geom=current_profile()['geometry']
    artist=ax.annotate(f'({label})',xy=(0,1),xycoords='axes fraction',
                       xytext=geom['panel_offset_pt'],textcoords='offset points',
                       ha='left',va='bottom',fontsize=geom['panel_fontsize'],fontweight='bold',
                       annotation_clip=False)
    if subtitle and show_subtitle:
        ax.annotate(subtitle,xy=(1,1),xycoords='axes fraction',
                    xytext=(0,5),textcoords='offset points',
                    ha='right',va='bottom',fontsize=mpl.rcParams['legend.fontsize'],annotation_clip=False)
    return artist
