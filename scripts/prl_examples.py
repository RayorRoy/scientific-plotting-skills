"""Portable PRL-inspired examples; all data are explicit analytic demos."""
from pathlib import Path
import argparse
import hashlib
import os


def square_layout(single=False):
    """Physical plot boxes; no change to the data-coordinate aspect ratio."""
    import matplotlib.pyplot as plt
    from matplotlib.ticker import StrMethodFormatter
    from houseplot import make_layout, panel_label
    width,height=(90,86) if single else (180,166)
    fig,axes=make_layout('single' if single else 'grid',width_mm=width)
    fig.set_layout_engine('none')
    fig.set_size_inches(width/25.4,height/25.4)
    boxes=[(18,16,58,58)] if single else [(18,96,56,56),(98,96,56,56),(18,18,56,56),(98,18,56,56)]
    for i,(ax,box) in enumerate(zip(axes.values(),boxes)):
        x,y,w,h=box
        ax.set_position([x/width,y/height,w/width,h/height])
        ax.tick_params(top=False,right=False)
        ax.xaxis.set_major_formatter(StrMethodFormatter('{x:g}'))
        ax.yaxis.set_major_formatter(StrMethodFormatter('{x:g}'))
        if not single:panel_label(ax,i)
    return fig,axes


def style_bar(cb):
    """Apply the selected font hierarchy, including custom colorbars."""
    import matplotlib as mpl
    cb.ax.tick_params(labelsize=mpl.rcParams['ytick.labelsize'])
    cb.ax.yaxis.label.set_size(mpl.rcParams['axes.labelsize'])
    cb.ax.yaxis.get_offset_text().set_size(mpl.rcParams['ytick.labelsize'])
    cb.outline.set_linewidth(mpl.rcParams['axes.linewidth'])


def source(path):
    path=Path(path)
    return {'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}


def build(output,overwrite=False):
    import numpy as np
    import matplotlib.pyplot as plt
    from houseplot import style_context,series_style,field_scale,add_colorbar,export_figure
    output=Path(output)
    targets=[output/f'{name}.{ext}' for name in ('prl_single','prl_atlas')
             for ext in ('pdf','svg','png','json','preview.png')]
    targets += [output/p for p in ('analytic_curves.csv','analytic_bars.csv','analytic_field.csv')]
    if not overwrite and any(p.exists() for p in targets):raise FileExistsError('Existing example outputs; use --overwrite')
    output.mkdir(parents=True,exist_ok=True)
    x=np.linspace(0,1,201)
    y1=.15+.75*np.sin(np.pi*x)**2
    y2=.1+.65*np.sin(np.pi*x)**2+.12*x
    k=np.array([0.,.2,.5])
    ordered=np.array([np.sqrt(np.maximum(x-.3,0))-.35*value for value in k])
    pos=np.arange(1,5);bars=np.array([[.2,.65,.9,.4],[.3,.5,.75,.6]])
    coord=np.linspace(-1,1,101);xx,yy=np.meshgrid(coord,coord);q=xx**2-yy**2
    np.savetxt(output/'analytic_curves.csv',np.column_stack((x,y1,y2,*ordered)),delimiter=',',header='x,y1,y2,k0,k02,k05',comments='')
    np.savetxt(output/'analytic_bars.csv',np.column_stack((pos,*bars)),delimiter=',',header='condition,A,B',comments='')
    np.savetxt(output/'analytic_field.csv',np.column_stack((xx.ravel(),yy.ravel(),q.ravel())),delimiter=',',header='x,y,q',comments='')
    reports={}
    with style_context(profile='prl-inspired-v1'):
        fig,axes=square_layout(single=True);ax=axes['A']
        for i,y in enumerate((y1,y2)):
            ax.plot(x,y,**series_style(i),markevery=25,markerfacecolor='none',label=f'Case {chr(65+i)}')
        ax.set(xlim=(0,1),ylim=(0,1.1),xticks=[0,.5,1],yticks=[0,.5,1],xlabel='$x/x_0$',ylabel='$R/R_0$')
        ax.legend(loc='upper left')
        reports['prl_single']=export_figure(fig,output/'prl_single',{
            'data_kind':'synthetic','sources':[source(output/'analytic_curves.csv')],
            'transformations':['x=linspace(0,1,201); y1=.15+.75*sin(pi*x)^2; y2=.1+.65*sin(pi*x)^2+.12*x'],
            'caption':'Analytic style demonstration, not measured or solved physical data. Hollow markers are sampled analytic points, not experimental observations.',
            'panel_titles_shown':False,'uncertainty':'none; deterministic analytic demo'},overwrite=overwrite)
        plt.close(fig)
        fig,axes=square_layout();a,b,c,d=axes.values()
        for i,y in enumerate((y1,y2)):
            a.plot(x,y,**series_style(i),markevery=25,markerfacecolor='none',label=f'Case {chr(65+i)}')
        a.set(xlim=(0,1),ylim=(0,1.2),xticks=[0,.5,1],yticks=[0,.5,1],xlabel='$x/x_0$',ylabel='$R/R_0$')
        a.legend(loc='upper left')
        for value,y,color,ls in zip(k,ordered,['#BFCDE9','#5B80C5','#003399'],[':','--','-']):
            b.plot(x,y,color=color,ls=ls,label=f'$k={value:g}$')
        b.set(xlim=(0,1),ylim=(-.4,.9),xticks=[0,.5,1],yticks=[0,.4,.8],xlabel='$x/x_0$',ylabel='$S/S_0$')
        b.legend(loc='upper left')
        for i,values in enumerate(bars):
            style=series_style(i)
            c.bar(pos+(i-.5)*.32,values,width=.32,color=style['color'],edgecolor=style['color'] if i==0 else '#333333',hatch='' if i==0 else '//',label=f'Case {chr(65+i)}',linewidth=.6)
        c.set(xlim=(.5,4.5),ylim=(0,1.2),xticks=pos,yticks=[0,.5,1],xlabel='Condition',ylabel='$A/A_0$')
        c.legend(loc='upper left')
        norm,cmap=field_scale([q],'signed')
        im=d.pcolormesh(xx,yy,q,norm=norm,cmap=cmap,shading='nearest',rasterized=True)
        d.contour(xx,yy,q,levels=[0],colors='#333333',linewidths=.8)
        d.set(xlim=(-1,1),ylim=(-1,1),xticks=[-1,0,1],yticks=[-1,0,1],xlabel='$x/x_0$',ylabel='$y/y_0$')
        d.set_aspect('equal')
        cb=add_colorbar(fig,im,d,'$q/q_0$',kind='signed');style_bar(cb)
        reports['prl_atlas']=export_figure(fig,output/'prl_atlas',{
            'data_kind':'synthetic','sources':[source(output/f'analytic_{s}.csv') for s in ('curves','bars','field')],
            'transformations':['(a) y1=.15+.75*sin(pi*x)^2; y2=.1+.65*sin(pi*x)^2+.12*x; 201 samples.',
                '(b) sqrt(max(x-.3,0))-.35*k; k=0,.2,.5; analytic model, not an EP claim.',
                '(c) Explicit invented bar values: A=[.2,.65,.9,.4], B=[.3,.5,.75,.6].',
                '(d) q=x^2-y^2 on 101x101 grid; fixed symmetric [-1,1]; zero contour.'],
            'caption':'Analytic appearance atlas: (a) categorical curves; (b) ordered parameter shades with redundant line styles; (c) paired bars with hatch redundancy; (d) signed field with zero-centred blue-white-red mapping. Hollow markers are sampled analytic points. No inference, experimental claim or error bars.',
            'panel_titles_shown':False,'uncertainty':'none; explicit deterministic demonstration'},overwrite=overwrite)
        plt.close(fig)
    return reports


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir',type=Path,required=True)
    parser.add_argument('--overwrite',action='store_true')
    args=parser.parse_args()
    os.environ['MPLCONFIGDIR']=str(args.output_dir.resolve()/'.cache/matplotlib')
    import matplotlib
    matplotlib.use('Agg')
    reports=build(args.output_dir,args.overwrite)
    print({name:report['checks'] for name,report in reports.items()})
