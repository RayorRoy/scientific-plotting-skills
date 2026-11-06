"""Self-contained analytic example for the basic or a selected appearance profile."""
from pathlib import Path
import argparse
import os
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--output',type=Path,default=Path('outputs/basic/demo'))
parser.add_argument('--overwrite',action='store_true')
parser.add_argument('--profile',default='house-times-v3')
args=parser.parse_args()
os.environ['MPLCONFIGDIR']=str(args.output.parent/'.cache/matplotlib')
sys.dont_write_bytecode=True

import matplotlib
matplotlib.use('Agg')
import numpy as np
import matplotlib.pyplot as plt
from houseplot import style_context, make_layout, plot_curve, export_figure, panel_label,series_style

with style_context(profile=args.profile):
    fig,axes=make_layout('grid',rows=1,cols=2,width_mm=180)
    x=np.linspace(0,1,101)
    for i,ax in enumerate(axes.values()):
        y=np.sin(np.pi*x)**2 if i==0 else np.exp(-3*x)
        plot_curve(ax,x,y,label='Synthetic response',**series_style(i),markevery=12)
        ax.set(xlabel='$t/t_0$',ylabel='$R/R_0$');ax.legend();panel_label(ax,i)
    fig.supxlabel('Synthetic data | standalone skill example',fontsize=7)
    report=export_figure(fig,args.output,{
        'data_kind':'synthetic','sources':[],
        'transformations':['x=linspace(0,1,101); y=sin(pi*x)^2 or exp(-3*x)'],
        'uncertainty':'none; analytic demonstration'},overwrite=args.overwrite)
    plt.close(fig)
    print(f'Exported to {args.output.parent.resolve()}; checks: {report["checks"]}')
