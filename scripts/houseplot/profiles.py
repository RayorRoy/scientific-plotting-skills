"""Versioned appearance-only JSON profiles, independent of workstation paths."""
from contextlib import contextmanager
from contextvars import ContextVar
from pathlib import Path, PurePosixPath, PureWindowsPath
import copy
import hashlib
import json
import math
import re

import matplotlib as mpl
from matplotlib.markers import MarkerStyle

DIRECTORY=Path(__file__).resolve().parents[2]/'assets/profiles'
DEFAULT_PROFILE='house-times-v3'
_BUILTIN_CMAPS=frozenset(json.loads((DIRECTORY.parent/'builtin_colormaps.json').read_text(encoding='utf-8')))
_ACTIVE=ContextVar('houseplot_profile',default=None)
_RC_ALLOWED={
    'font.family','font.size','mathtext.fontset','axes.labelsize','axes.titlesize',
    'xtick.labelsize','ytick.labelsize','legend.fontsize','axes.linewidth',
    'lines.linewidth','lines.markersize','xtick.direction','ytick.direction',
    'axes.grid','axes.spines.top','axes.spines.right','axes.spines.left','axes.spines.bottom',
    'xtick.major.size','ytick.major.size','xtick.major.width','ytick.major.width',
    'legend.frameon','legend.handlelength','legend.borderaxespad'
}
_GEOMETRY={'single_width_mm','combination_width_mm','panel_fontsize','panel_offset_pt',
           'colorbar_width_mm','colorbar_gap_mm'}


def _positive(value):
    return type(value) in (int,float) and math.isfinite(value) and value>0


def validate_profile(profile):
    required={'schema_version','id','version','description','status','source','rcparams',
              'series','field_palettes','geometry'}
    if not isinstance(profile,dict) or set(profile)!=required:
        raise ValueError('Profile requires exactly the documented appearance fields')
    p=copy.deepcopy(profile)
    if type(p['schema_version']) is not int or p['schema_version']!=1:
        raise ValueError('Unsupported profile schema_version')
    if not isinstance(p['id'],str) or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',p['id']):
        raise ValueError('Profile id must be a lowercase kebab-case identifier')
    if not isinstance(p['version'],str) or not re.fullmatch(r'\d+\.\d+\.\d+',p['version']):
        raise ValueError('Profile version must be major.minor.patch')
    if p['status'] not in ('draft','user-confirmed') or not isinstance(p['description'],str):
        raise ValueError('Invalid profile status or description')
    source=p['source']
    if not isinstance(source,dict) or set(source)!={'kind','references','observations'}:
        raise ValueError('source requires kind, references and observations')
    if not isinstance(source['references'],list) or not isinstance(source['observations'],list):
        raise ValueError('Profile evidence must be arrays')
    for ref in source['references']:
        if not isinstance(ref,dict):raise ValueError('Reference evidence must be an object')
        if 'path' in ref:
            path=str(ref['path']).replace('\\','/')
            if PurePosixPath(path).is_absolute() or PureWindowsPath(path).drive or PureWindowsPath(path).root or '..' in PurePosixPath(path).parts:
                raise ValueError('Bundled reference paths must be relative without parent traversal')
    for obs in source['observations']:
        if not isinstance(obs,dict) or obs.get('evidence') not in ('observed','estimated','assumed','confirmed'):
            raise ValueError('Each extracted parameter needs an evidence category')
    rc=p['rcparams']
    if not isinstance(rc,dict) or not set(rc)<=_RC_ALLOWED or 'font.family' not in rc:
        raise ValueError('Profile rcparams contains unknown fields or lacks font.family')
    family=rc['font.family']
    if not isinstance(family,str) or not family.strip():raise ValueError('Use one explicit font family')
    for key,value in rc.items():
        if key.endswith(('size','width','pad','length')) and not _positive(value):
            raise ValueError(f'{key} must be a finite positive number')
    try:
        with mpl.rc_context(rc):pass
    except (ValueError,TypeError) as e:raise ValueError(f'Invalid Matplotlib appearance value: {e}') from e
    if not isinstance(p['series'],list) or not p['series']:
        raise ValueError('At least one categorical series style is required')
    for style in p['series']:
        if not isinstance(style,dict) or set(style)!={'color','linestyle','marker'}:
            raise ValueError('Series style needs color, linestyle, marker')
        if not isinstance(style['color'],str) or not re.fullmatch(r'#[a-fA-F0-9]{6}',style['color']):
            raise ValueError('Series colors must be opaque #RRGGBB')
        if style['linestyle'] not in ('-','--','-.',':'):raise ValueError('Unsupported line style')
        try:MarkerStyle(style['marker'])
        except (ValueError,TypeError) as e:raise ValueError('Invalid marker') from e
    palettes=p['field_palettes']
    expected={'magnitude':'sequential','signed':'diverging','phase':'cyclic'}
    if not isinstance(palettes,dict) or set(palettes)!=set(expected):raise ValueError('Need all three semantic field palettes')
    for key,kind in expected.items():
        value=palettes[key]
        if not isinstance(value,dict) or not {'kind','name'}<=set(value) or not set(value)<={'kind','name','colors'} or value['kind']!=kind:
            raise ValueError(f'{key} field palette must declare {kind}')
        if not isinstance(value['name'],str) or not value['name']:raise ValueError('Colormap name is required')
        if 'colors' in value:
            colors=value['colors']
            if not isinstance(colors,list) or len(colors)<2 or not all(isinstance(c,str) and re.fullmatch(r'#[a-fA-F0-9]{6}',c) for c in colors):
                raise ValueError('Custom field maps need at least two opaque #RRGGBB color nodes')
            if kind=='cyclic' and colors[0].lower()!=colors[-1].lower():
                raise ValueError('Custom cyclic maps must close with the same first/last color')
        elif value['name'] not in _BUILTIN_CMAPS or value['name'] not in mpl.colormaps:
            raise ValueError('Non-builtin field colormaps require serialized colors')
    geom=p['geometry']
    if not isinstance(geom,dict) or not _GEOMETRY<=set(geom) or not set(geom)<=_GEOMETRY|{'colorbar_tick_length_pt'}:raise ValueError('Invalid geometry fields')
    for key,value in geom.items():
        if key=='panel_offset_pt':
            if not isinstance(value,list) or len(value)!=2 or not all(type(v) in (int,float) and math.isfinite(v) for v in value):
                raise ValueError('panel_offset_pt must contain two finite numbers')
        elif key=='colorbar_tick_length_pt':
            if type(value) not in (int,float) or not math.isfinite(value) or value<0:raise ValueError('Colorbar tick length must be nonnegative')
        elif not _positive(value):raise ValueError(f'{key} must be positive')
    return p


def load_profile(reference=DEFAULT_PROFILE):
    ref=Path(reference)
    if ref.suffix.lower()=='.json' or ref.is_file():path=ref
    else:
        if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',str(reference)):
            raise ValueError('Use a registered template id or an explicit JSON path')
        path=DIRECTORY/(str(reference)+'.json')
    return validate_profile(json.loads(path.read_text(encoding='utf-8')))


def profile_fingerprint(profile):
    return hashlib.sha256(json.dumps(profile,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode('utf-8')).hexdigest()


def current_profile():
    active=_ACTIVE.get()
    return active if active is not None else load_profile()


@contextmanager
def profile_context(reference=None):
    p=load_profile(reference) if reference is not None else copy.deepcopy(current_profile())
    token=_ACTIVE.set(p)
    try:yield p
    finally:_ACTIVE.reset(token)


def series_style(index):
    if type(index) is not int or index<0:raise ValueError('Series index must be a nonnegative integer')
    styles=current_profile()['series']
    return copy.deepcopy(styles[index%len(styles)])


def profile_colormap(kind):
    palette=current_profile()['field_palettes'][kind]
    if 'colors' in palette:
        return mpl.colors.LinearSegmentedColormap.from_list(palette['name'],palette['colors'],N=256)
    return mpl.colormaps[palette['name']]


def compose_profile(base,*,profile_id,version,patch,source=None):
    """Compose appearance sections; new variants start as unconfirmed drafts."""
    selected=validate_profile(base) if isinstance(base,dict) else load_profile(base)
    if not isinstance(patch,dict) or not set(patch)<={'rcparams','series','field_palettes','geometry'}:
        raise ValueError('Only appearance sections can be composed')
    derived=copy.deepcopy(selected)
    def merge(dest,changes):
        for key,value in changes.items():
            if isinstance(value,dict) and isinstance(dest.get(key),dict):merge(dest[key],value)
            else:dest[key]=copy.deepcopy(value)
    merge(derived,patch)
    derived.update(id=profile_id,version=version,status='draft')
    derived['description']=f'Draft derived from {selected["id"]}@{selected["version"]}'
    derived['source']=copy.deepcopy(selected['source'])
    derived['source']['kind']='derived'
    for obs in derived['source']['observations']:
        obs.setdefault('origin_template',f'{selected["id"]}@{selected["version"]}')
    if source is not None:
        if not isinstance(source,dict) or set(source)!={'kind','references','observations'}:
            raise ValueError('New evidence source needs kind, references, observations')
        for ref in source['references']:
            if ref not in derived['source']['references']:derived['source']['references'].append(copy.deepcopy(ref))
        derived['source']['observations'].extend(copy.deepcopy(source['observations']))
    for section,changes in patch.items():
        derived['source']['observations'].append({'parameter':section,'evidence':'assumed',
            'value':copy.deepcopy(changes),'note':'New appearance override; awaiting user confirmation'})
    derived['source']['observations'].append({'parameter':'base-template','evidence':'observed',
        'value':f'{selected["id"]}@{selected["version"]}','note':f'Canonical SHA256 {profile_fingerprint(selected)}; new appearance remains draft'})
    return validate_profile(derived)
