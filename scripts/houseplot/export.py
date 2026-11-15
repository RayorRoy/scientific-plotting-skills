"""Explicit export plus automated PNG/SVG/PDF quality checks. No publisher or Illustrator certification claims."""
from pathlib import Path
import base64
import hashlib
import importlib.metadata
import inspect
import io
import json
import os
import platform
import re
import tempfile
import xml.etree.ElementTree as ET

import matplotlib as mpl
from matplotlib import font_manager
from matplotlib.text import Text
from matplotlib.legend import Legend
from PIL import Image

try:
    import pymupdf
except ImportError:
    pymupdf = None

from .profiles import current_profile, profile_fingerprint

_SVG_NS = 'http://www.w3.org/2000/svg'
_XLINK_HREF = '{http://www.w3.org/1999/xlink}href'
_VECTOR_TAGS = frozenset({'path', 'line', 'polyline', 'polygon', 'rect', 'circle', 'ellipse'})
_FILTER_TAGS = frozenset({
    'filter', 'feBlend', 'feColorMatrix', 'feComponentTransfer', 'feComposite',
    'feConvolveMatrix', 'feDiffuseLighting', 'feDisplacementMap', 'feDropShadow',
    'feFlood', 'feFuncA', 'feFuncB', 'feFuncG', 'feFuncR', 'feGaussianBlur',
    'feImage', 'feMerge', 'feMergeNode', 'feMorphology', 'feOffset',
    'fePointLight', 'feSpecularLighting', 'feSpotLight', 'feTile', 'feTurbulence',
})
_STRIP_EXTS = frozenset({'.png', '.svg', '.pdf', '.py', '.json'})
_UNIT_TO_PT = {'pt': 1.0, 'in': 72.0, 'mm': 72.0 / 25.4, 'cm': 72.0 / 2.54, 'px': 72.0 / 96.0, '': 1.0}


def _sha(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def _json(value):
    if isinstance(value, Path):
        return str(value)
    if hasattr(value, 'tolist'):
        return value.tolist()
    raise TypeError(f'Cannot serialize {type(value).__name__}')


def _pkg_version(name):
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _atomic_write_text(target, text):
    target = Path(target)
    fd, temp = tempfile.mkstemp(prefix='.export-', suffix=target.suffix, dir=target.parent)
    os.close(fd)
    try:
        Path(temp).write_text(text, encoding='utf-8')
        os.replace(temp, target)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def _local_tag(tag):
    return tag.split('}', 1)[-1] if '}' in tag else tag


def _parse_svg_length_pt(value):
    if value is None:
        return None
    m = re.fullmatch(r'\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)\s*([a-zA-Z%]*)\s*', str(value))
    if not m:
        return None
    num = float(m.group(1))
    unit = m.group(2).lower()
    if unit not in _UNIT_TO_PT:
        return None
    return num * _UNIT_TO_PT[unit]


def _parse_style_dict(style_str):
    result = {}
    if not style_str:
        return result
    for chunk in style_str.split(';'):
        if ':' in chunk:
            key, val = chunk.split(':', 1)
            result[key.strip().lower()] = val.strip()
    return result


def _extract_font_families(style_dict, attr_font_family):
    raw = style_dict.get('font-family') or attr_font_family or ''
    families = []
    for item in raw.split(','):
        cleaned = item.strip().strip("'\"")
        if cleaned:
            families.append(cleaned)
    return families


def _check_font_compatibility(fonts_referenced):
    """Evaluate font availability and Illustrator cross-machine risks."""
    mpl_data = Path(mpl.get_data_path()).resolve()
    warnings = []
    details = []
    for name in sorted(fonts_referenced):
        entry = {'family': name, 'found_locally': False, 'bundled_with_matplotlib': False, 'file': None}
        try:
            fpath = font_manager.findfont(font_manager.FontProperties(family=[name]), fallback_to_default=False)
            resolved = Path(fpath).resolve()
            entry['found_locally'] = True
            entry['file'] = str(resolved)
            try:
                resolved.relative_to(mpl_data)
                entry['bundled_with_matplotlib'] = True
            except ValueError:
                entry['bundled_with_matplotlib'] = False
        except Exception:
            entry['found_locally'] = False

        if entry['bundled_with_matplotlib']:
            warnings.append(
                f"Font '{name}' is bundled inside Matplotlib ({Path(entry['file']).name}) and may not be installed as an OS font for Adobe Illustrator; install the font on the editing system or use optional svg_text_to_path=True if missing-font substitution occurs."
            )
        elif not entry['found_locally']:
            warnings.append(
                f"Font '{name}' was not resolved locally; Adobe Illustrator may substitute it unless installed, or use optional svg_text_to_path=True."
            )
        elif name.lower() in {'times new roman', 'arial', 'calibri'}:
            warnings.append(
                f"Font '{name}' is an OS-dependent font; verify availability on any external Illustrator workstation or export optional outlined SVG (svg_text_to_path=True)."
            )
        details.append(entry)
    return details, warnings


def inspect_png(png_path, expected_size_mm, expected_dpi=600):
    """Inspect a generated PNG file for existence, DPI metadata, dimensions, and white opaque background."""
    png_path = Path(png_path)
    result = {
        'file': png_path.name,
        'exists': png_path.is_file(),
        'bytes': png_path.stat().st_size if png_path.is_file() else 0,
        'valid_png': False,
        'pixels': None,
        'expected_pixels': [
            int(round(expected_size_mm[0] / 25.4 * expected_dpi)),
            int(round(expected_size_mm[1] / 25.4 * expected_dpi)),
        ],
        'pixel_dimensions_match': False,
        'dpi': None,
        'expected_dpi': float(expected_dpi),
        'dpi_matches_target': False,
        'dpi_is_600': False,
        'mode': None,
        'has_transparency': None,
        'white_opaque_background': False,
    }
    if not result['exists'] or result['bytes'] == 0:
        return result
    try:
        with Image.open(png_path) as im:
            im.load()
            result['valid_png'] = (im.format == 'PNG')
            result['pixels'] = list(im.size)
            result['mode'] = im.mode
            exp_w = expected_size_mm[0] / 25.4 * expected_dpi
            exp_h = expected_size_mm[1] / 25.4 * expected_dpi
            result['pixel_dimensions_match'] = (
                abs(im.size[0] - exp_w) < 1.1 and abs(im.size[1] - exp_h) < 1.1
            )
            dpi_info = im.info.get('dpi')
            if isinstance(dpi_info, (tuple, list)) and len(dpi_info) >= 2:
                dpi_x, dpi_y = float(dpi_info[0]), float(dpi_info[1])
                result['dpi'] = [dpi_x, dpi_y]
                result['dpi_matches_target'] = (
                    abs(dpi_x - expected_dpi) <= 0.15 and abs(dpi_y - expected_dpi) <= 0.15
                )
                result['dpi_is_600'] = (
                    abs(dpi_x - 600.0) <= 0.15 and abs(dpi_y - 600.0) <= 0.15
                )

            w, h = im.size
            corners = [(0, 0), (max(0, w - 1), 0), (0, max(0, h - 1)), (max(0, w - 1), max(0, h - 1))]
            if im.mode == 'RGBA':
                min_alpha, _ = im.getchannel('A').getextrema()
                has_trans = min_alpha < 255
                corner_vals = [im.getpixel(pt) for pt in corners]
                white_corners = all(c[0] >= 254 and c[1] >= 254 and c[2] >= 254 and c[3] == 255 for c in corner_vals)
                result['has_transparency'] = bool(has_trans)
                result['white_opaque_background'] = (not has_trans) and white_corners
            elif im.mode == 'RGB':
                corner_vals = [im.getpixel(pt) for pt in corners]
                result['has_transparency'] = False
                result['white_opaque_background'] = all(c[0] >= 254 and c[1] >= 254 and c[2] >= 254 for c in corner_vals)
            elif im.mode == 'LA':
                min_alpha, _ = im.getchannel('A').getextrema()
                has_trans = min_alpha < 255
                corner_vals = [im.getpixel(pt) for pt in corners]
                result['has_transparency'] = bool(has_trans)
                result['white_opaque_background'] = (not has_trans) and all(c[0] >= 254 and c[1] == 255 for c in corner_vals)
            elif im.mode == 'L':
                corner_vals = [im.getpixel(pt) for pt in corners]
                result['has_transparency'] = False
                result['white_opaque_background'] = all(c >= 254 for c in corner_vals)
            else:
                rgb_im = im.convert('RGBA')
                min_alpha, _ = rgb_im.getchannel('A').getextrema()
                has_trans = min_alpha < 255
                corner_vals = [rgb_im.getpixel(pt) for pt in corners]
                result['has_transparency'] = bool(has_trans)
                result['white_opaque_background'] = (not has_trans) and all(
                    c[0] >= 254 and c[1] >= 254 and c[2] >= 254 and c[3] == 255 for c in corner_vals
                )
    except Exception as exc:
        result['error'] = str(exc)
    return result


def inspect_svg(
    svg_path,
    *,
    expected_size_mm=None,
    expect_editable_text=True,
    expect_outlined_text=False,
    min_embedded_dpi=300.0,
):
    """Inspect SVG structure, vector/text editability, embedded image DPI, and Illustrator compatibility."""
    svg_path = Path(svg_path)
    result = {
        'file': svg_path.name,
        'exists': svg_path.is_file(),
        'bytes': svg_path.stat().st_size if svg_path.is_file() else 0,
        'valid_xml': False,
        'is_svg_root': False,
        'svg_version': None,
        'is_svg_1_1': False,
        'size_pt': None,
        'size_mm': None,
        'dimensions_match': None if expected_size_mm is None else False,
        'group_count': 0,
        'group_ids_sample': [],
        'has_structured_groups': False,
        'vector_primitive_count': 0,
        'text_element_count': 0,
        'tspan_element_count': 0,
        'has_editable_text': False,
        'fonts_referenced': [],
        'font_compatibility': [],
        'font_compatibility_warnings': [],
        'embedded_image_count': 0,
        'embedded_images': [],
        'min_embedded_image_dpi': None,
        'embedded_images_dpi_ok': True,
        'whole_figure_rasterized': False,
        'is_true_vector': False,
        'external_dependencies': [],
        'no_external_dependencies': False,
        'illustrator_incompatible_features': [],
        'illustrator_compatible': False,
        'illustrator_tested': False,
        'illustrator_note': (
            'Adobe Illustrator is not installed or executed in this environment; '
            'verified via automated SVG 1.1 XML, vector/text editability, '
            'embedded raster DPI, grouping, and external-dependency checks only.'
        ),
    }
    if not result['exists'] or result['bytes'] == 0:
        return result

    try:
        tree = ET.parse(svg_path)
        root = tree.getroot()
    except ET.ParseError as exc:
        result['xml_error'] = str(exc)
        return result

    result['valid_xml'] = True
    result['is_svg_root'] = (_local_tag(root.tag) == 'svg') and (
        root.tag == f'{{{_SVG_NS}}}svg' or '{' not in root.tag
    )
    svg_version = root.attrib.get('version')
    result['svg_version'] = svg_version
    result['is_svg_1_1'] = (svg_version == '1.1')

    w_pt = _parse_svg_length_pt(root.attrib.get('width'))
    h_pt = _parse_svg_length_pt(root.attrib.get('height'))
    if w_pt is not None and h_pt is not None:
        result['size_pt'] = [float(w_pt), float(h_pt)]
        size_mm = [float(w_pt * 25.4 / 72.0), float(h_pt * 25.4 / 72.0)]
        result['size_mm'] = size_mm
        if expected_size_mm is not None:
            result['dimensions_match'] = (
                abs(size_mm[0] - expected_size_mm[0]) < 0.05
                and abs(size_mm[1] - expected_size_mm[1]) < 0.05
            )
    canvas_area_pt2 = (w_pt * h_pt) if (w_pt and h_pt) else 0.0

    group_ids = []
    fonts_referenced = set()
    external_deps = []
    incompatible = []
    embedded_images = []
    vector_count = 0
    text_count = 0
    tspan_count = 0
    group_count = 0

    def _scan_css_text(css_text, context_label):
        if '@import' in css_text:
            external_deps.append(f'{context_label}: @import rule')
            incompatible.append(f'{context_label}: CSS @import')
        for match in re.finditer(r'url\(\s*([^)]+?)\s*\)', css_text):
            ref = match.group(1).strip().strip("'\"")
            if not ref.startswith('#') and not ref.startswith('data:'):
                external_deps.append(f'{context_label}: external url({ref})')

    def _walk(node, in_metadata=False):
        nonlocal vector_count, text_count, tspan_count, group_count
        tag = _local_tag(node.tag)
        if tag == 'metadata':
            return
        if in_metadata:
            return

        if tag == 'g':
            group_count += 1
            gid = node.attrib.get('id')
            if gid:
                group_ids.append(gid)
        elif tag in _VECTOR_TAGS:
            vector_count += 1
        elif tag == 'text':
            text_count += 1
        elif tag == 'tspan':
            tspan_count += 1

        if tag in _FILTER_TAGS:
            incompatible.append(f'SVG filter element <{tag}>')
        if tag in ('foreignObject', 'script', 'link'):
            incompatible.append(f'Unsupported/incompatible element <{tag}>')
            if tag in ('link', 'script'):
                href = node.attrib.get('href') or node.attrib.get(_XLINK_HREF) or node.attrib.get('src')
                if href and not href.startswith('data:'):
                    external_deps.append(f'<{tag}> reference: {href}')

        if tag == 'style' and node.text:
            _scan_css_text(node.text, '<style>')

        style_attr = node.attrib.get('style', '')
        style_dict = _parse_style_dict(style_attr)
        if style_attr:
            _scan_css_text(style_attr, f'<{tag} style>')
        if 'mix-blend-mode' in style_dict or 'mix-blend-mode' in node.attrib:
            incompatible.append(f'<{tag}> uses mix-blend-mode')
        if 'isolation' in style_dict or 'isolation' in node.attrib:
            incompatible.append(f'<{tag}> uses isolation')
        if 'filter' in style_dict or 'filter' in node.attrib:
            incompatible.append(f'<{tag}> uses CSS/attribute filter')

        if tag in ('text', 'tspan'):
            for fam in _extract_font_families(style_dict, node.attrib.get('font-family')):
                fonts_referenced.add(fam)

        href = node.attrib.get('href') or node.attrib.get(_XLINK_HREF)
        if href is not None:
            if not href.startswith('#') and not href.startswith('data:'):
                external_deps.append(f'<{tag}> external href: {href}')

        if tag == 'image':
            img_w = _parse_svg_length_pt(node.attrib.get('width')) or 0.0
            img_h = _parse_svg_length_pt(node.attrib.get('height')) or 0.0
            area_ratio = (img_w * img_h / canvas_area_pt2) if canvas_area_pt2 > 0 else 0.0
            img_entry = {
                'id': node.attrib.get('id'),
                'width_pt': img_w,
                'height_pt': img_h,
                'canvas_area_ratio': round(area_ratio, 4),
                'embedded_data_uri': bool(href and href.startswith('data:')),
                'pixels': None,
                'effective_dpi': None,
            }
            if href and href.startswith('data:image/') and ';base64,' in href:
                try:
                    raw = base64.b64decode(href.split(';base64,', 1)[1])
                    with Image.open(io.BytesIO(raw)) as im:
                        px_w, px_h = im.size
                    img_entry['pixels'] = [px_w, px_h]
                    eff_x = (px_w / (img_w / 72.0)) if img_w > 0 else 0.0
                    eff_y = (px_h / (img_h / 72.0)) if img_h > 0 else 0.0
                    img_entry['effective_dpi'] = [round(eff_x, 2), round(eff_y, 2)]
                except Exception as exc:
                    img_entry['decode_error'] = str(exc)
            embedded_images.append(img_entry)

        for child in node:
            _walk(child, in_metadata=False)

    _walk(root)

    result['group_count'] = group_count
    result['group_ids_sample'] = group_ids[:30]
    result['has_structured_groups'] = group_count >= 2 and len(group_ids) >= 2
    result['vector_primitive_count'] = vector_count
    result['text_element_count'] = text_count
    result['tspan_element_count'] = tspan_count
    result['has_editable_text'] = (text_count > 0)
    result['fonts_referenced'] = sorted(fonts_referenced)
    font_details, font_warnings = _check_font_compatibility(fonts_referenced)
    result['font_compatibility'] = font_details
    result['font_compatibility_warnings'] = font_warnings

    result['embedded_image_count'] = len(embedded_images)
    result['embedded_images'] = embedded_images
    eff_dpis = [
        min(img['effective_dpi'])
        for img in embedded_images
        if img.get('effective_dpi') is not None
    ]
    if eff_dpis:
        min_eff = min(eff_dpis)
        result['min_embedded_image_dpi'] = round(min_eff, 2)
        result['embedded_images_dpi_ok'] = (min_eff >= float(min_embedded_dpi) - 0.5)

    max_area_ratio = max((img['canvas_area_ratio'] for img in embedded_images), default=0.0)
    # Matplotlib creates 1-2 background <path> patches; a whole-figure rasterized SVG has
    # an <image> without vector plot elements or text.
    whole_raster = bool(embedded_images) and (
        (vector_count <= 2 and text_count == 0)
        or (max_area_ratio >= 0.85 and vector_count <= 3 and text_count == 0)
    )
    result['whole_figure_rasterized'] = whole_raster
    result['is_true_vector'] = (
        result['valid_xml']
        and result['is_svg_root']
        and (not whole_raster)
        and (vector_count > 0 or text_count > 0)
    )
    result['external_dependencies'] = external_deps
    result['no_external_dependencies'] = (len(external_deps) == 0)
    result['illustrator_incompatible_features'] = sorted(set(incompatible))
    result['illustrator_compatible'] = (
        result['valid_xml']
        and result['is_svg_root']
        and result['is_svg_1_1']
        and result['no_external_dependencies']
        and (len(incompatible) == 0)
        and (not whole_raster)
    )
    if expect_outlined_text:
        result['text_mode'] = 'outlined_paths'
    elif expect_editable_text:
        result['text_mode'] = 'editable_text' if text_count > 0 else 'no_text_detected'
    else:
        result['text_mode'] = 'unspecified'
    return result


def _assign_semantic_svg_gids(fig):
    """Attach readable SVG group IDs for Adobe Illustrator without overwriting user IDs."""
    panel_axes = getattr(fig, '_houseplot_panel_axes', {}) or {}
    for name, ax in panel_axes.items():
        if ax.get_gid() is None:
            ax.set_gid(f'panel_{name}')
    for idx, cb in enumerate(getattr(fig, '_houseplot_colorbars', []) or [], 1):
        if cb.ax.get_gid() is None:
            cb.ax.set_gid(f'colorbar_{idx}')


def _collect_bounds_issues(fig):
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    canvas = fig.bbox
    outside = []
    hidden_tick_labels = set()
    for ax in fig.axes:
        for axis in (ax.xaxis, ax.yaxis):
            lo, hi = sorted(axis.get_view_interval())
            for tick in axis.get_major_ticks() + axis.get_minor_ticks():
                if not lo - 1e-10 <= tick.get_loc() <= hi + 1e-10:
                    hidden_tick_labels.update((id(tick.label1), id(tick.label2)))
    visible_text_count = 0
    for item in fig.findobj(match=Text):
        # Tick labels outside the displayed data interval are intentionally hidden by axes.
        if not item.get_visible() or not item.get_text().strip():
            continue
        if id(item) in hidden_tick_labels:
            continue
        visible_text_count += 1
        box = item.get_window_extent(renderer)
        if box.width > 0 and box.height > 0 and (
            box.x0 < canvas.x0 - 1
            or box.y0 < canvas.y0 - 1
            or box.x1 > canvas.x1 + 1
            or box.y1 > canvas.y1 + 1
        ):
            outside.append(item.get_text())
    for legend in fig.findobj(match=Legend):
        if not legend.get_visible():
            continue
        box = legend.get_window_extent(renderer)
        if (
            box.x0 < canvas.x0 - 1
            or box.y0 < canvas.y0 - 1
            or box.x1 > canvas.x1 + 1
            or box.y1 > canvas.y1 + 1
        ):
            outside.append('[legend bounding box]')
    return outside, visible_text_count


def _find_caller_script():
    houseplot_dir = Path(__file__).resolve().parent
    for frame_info in inspect.stack():
        fname = frame_info.filename
        if not fname or fname.startswith('<'):
            continue
        fpath = Path(fname)
        try:
            resolved = fpath.resolve()
        except OSError:
            continue
        if not resolved.is_file():
            continue
        if houseplot_dir in resolved.parents or resolved.parent == houseplot_dir:
            continue
        if 'unittest' in resolved.parts:
            continue
        if resolved.suffix.lower() == '.py':
            return resolved
    return None


def _write_reproducible_script(target_py, source_script, *, profile, size_mm, dpi, provenance):
    target_py = Path(target_py)
    if source_script is not None:
        if isinstance(source_script, Path) or (
            isinstance(source_script, str)
            and '\n' not in source_script
            and len(source_script) < 512
            and Path(source_script).is_file()
        ):
            src_path = Path(source_script)
            if src_path.resolve() == target_py.resolve():
                return {'mode': 'self_existing', 'origin': src_path.name}
            _atomic_write_text(target_py, src_path.read_text(encoding='utf-8'))
            return {'mode': 'source_script_file', 'origin': src_path.name}
        if isinstance(source_script, str):
            _atomic_write_text(target_py, source_script if source_script.endswith('\n') else source_script + '\n')
            return {'mode': 'source_script_text', 'origin': 'inline_string'}
        raise TypeError('source_script must be a Path or str')

    caller = _find_caller_script()
    if caller is not None:
        if caller.resolve() == target_py.resolve():
            return {'mode': 'self_existing', 'origin': caller.name}
        _atomic_write_text(target_py, caller.read_text(encoding='utf-8'))
        return {'mode': 'caller_script_snapshot', 'origin': caller.name}

    stub = (
        '"""Interactive-session figure snapshot (supply source_script=... for full script capture)."""\n'
        'import matplotlib.pyplot as plt\n'
        'from houseplot import style_context, save_publication_figure\n\n'
        f'PROFILE = {profile["id"]!r}\n'
        f'SIZE_MM = ({size_mm[0]:.3f}, {size_mm[1]:.3f})\n'
        f'DPI = {dpi}\n'
        f'PROVENANCE = {json.dumps(provenance, ensure_ascii=False, indent=2, default=_json)}\n\n'
        '# Recreate your figure here inside style_context(profile=PROFILE), then call:\n'
        f'# save_publication_figure(fig, {target_py.with_suffix("").name!r}, PROVENANCE, dpi=DPI)\n'
    )
    _atomic_write_text(target_py, stub)
    return {'mode': 'interactive_stub', 'origin': None}


def _save_matplotlib_formats(fig, targets, *, dpi, svg_fonttype='none'):
    saved_hashes = {}
    rc_base = {
        'savefig.bbox': None,
        'savefig.facecolor': 'white',
        'savefig.transparent': False,
        'svg.fonttype': svg_fonttype,
        'svg.image_inline': True,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
    }
    for fmt, target in targets.items():
        actual_fmt = 'svg' if fmt == 'outlined_svg' else fmt
        fmt_rc = dict(rc_base)
        if fmt == 'outlined_svg':
            fmt_rc['svg.fonttype'] = 'path'
        fd, temp = tempfile.mkstemp(prefix='.export-', suffix='.' + actual_fmt, dir=target.parent)
        os.close(fd)
        try:
            with mpl.rc_context(fmt_rc):
                fig.savefig(
                    temp,
                    format=actual_fmt,
                    dpi=dpi,
                    bbox_inches=None,
                    facecolor='white',
                    transparent=False,
                )
            os.replace(temp, target)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)
        saved_hashes[fmt] = {
            'file': target.name,
            'bytes': target.stat().st_size,
            'sha256': _sha(target),
        }
    return saved_hashes


def _run_export(
    fig,
    stem,
    provenance,
    *,
    dpi=600,
    overwrite=False,
    include_pdf=True,
    save_py=False,
    source_script=None,
    svg_text_to_path=False,
    require_600_dpi=False,
    strict_checks=False,
):
    if require_600_dpi and abs(float(dpi) - 600.0) > 1e-6:
        raise ValueError(
            'Publication PNG export requires dpi=600 (pass require_600_dpi=False only for draft previews)'
        )
    if not isinstance(dpi, (int, float)) or not 0 < dpi <= 2400:
        raise ValueError('dpi must be positive and at most 2400')

    stem = Path(stem)
    formats = ['png', 'svg']
    if include_pdf:
        formats.insert(0, 'pdf')
    targets = {fmt: stem.with_suffix('.' + fmt) for fmt in formats}
    if svg_text_to_path:
        targets['outlined_svg'] = stem.with_name(stem.name + '.outlined.svg')
    json_target = stem.with_suffix('.json')
    py_target = stem.with_suffix('.py')
    preview = stem.with_suffix('.preview.png')

    preflight_paths = [*targets.values(), json_target]
    if save_py:
        preflight_paths.append(py_target)
    if include_pdf and pymupdf is not None:
        preflight_paths.append(preview)
    for path in preflight_paths:
        if path.exists() and not overwrite:
            raise FileExistsError(path)

    stem.parent.mkdir(parents=True, exist_ok=True)
    width, height = fig.get_size_inches() * 25.4
    versions = {
        name: _pkg_version(name) for name in ('numpy', 'matplotlib', 'pillow', 'pymupdf')
    }

    _assign_semantic_svg_gids(fig)
    outside, visible_text_count = _collect_bounds_issues(fig)

    selected = getattr(fig, '_houseplot_profile', current_profile())
    family = getattr(fig, '_houseplot_font_family', mpl.rcParams['font.family'][0])
    font_file = font_manager.findfont(
        font_manager.FontProperties(family=[family]), fallback_to_default=False
    )

    report = {
        'size_mm': [float(width), float(height)],
        'dpi': dpi,
        'font_file': font_file,
        'profile': {
            'id': selected['id'],
            'version': selected['version'],
            'sha256': profile_fingerprint(selected),
            'snapshot': selected,
        },
        'versions': versions,
        'python': platform.python_version(),
        'provenance': provenance,
        'checks': {'text_outside_canvas': outside},
        'outputs': {},
        'warnings': [],
        'limitations': [
            'No automated scientific or publisher compliance certification',
            'Adobe Illustrator was not executed in this environment; SVG checks cover XML 1.1 structure, vector primitives, editable text, embedded DPI, grouping, and external dependencies only',
            'Editable SVG text (svg.fonttype="none") requires referenced fonts on the viewing/Illustrator machine',
            'Text bounds do not detect all inter-artist overlaps or raster detail loss',
        ],
    }

    package = Path(__file__).resolve().parents[2]
    report['helper_code_sha256'] = {
        str(p.relative_to(package)): _sha(p)
        for p in sorted((package / 'scripts/houseplot').glob('*.py'))
    }
    report['helper_code_sha256']['assets/times.mplstyle'] = _sha(package / 'assets/times.mplstyle')

    def geometry_box(ax):
        box = ax.get_position()
        return {
            'x_mm': float(box.x0 * width),
            'y_mm': float(box.y0 * height),
            'width_mm': float(box.width * width),
            'height_mm': float(box.height * height),
        }

    report['geometry'] = {
        'panels': {
            name: geometry_box(ax)
            for name, ax in getattr(fig, '_houseplot_panel_axes', {}).items()
        },
        'colorbars': [
            dict(geometry_box(cb.ax), ticks=[float(t) for t in cb.get_ticks()])
            for cb in getattr(fig, '_houseplot_colorbars', [])
        ],
    }

    report['outputs'] = _save_matplotlib_formats(fig, targets, dpi=dpi, svg_fonttype='none')

    if save_py:
        py_meta = _write_reproducible_script(
            py_target,
            source_script,
            profile=selected,
            size_mm=(float(width), float(height)),
            dpi=dpi,
            provenance=provenance,
        )
        report['outputs']['py'] = {
            'file': py_target.name,
            'bytes': py_target.stat().st_size,
            'sha256': _sha(py_target),
            **py_meta,
        }

    png_audit = inspect_png(targets['png'], (width, height), expected_dpi=dpi)
    svg_audit = inspect_svg(
        targets['svg'],
        expected_size_mm=(width, height),
        expect_editable_text=(visible_text_count > 0),
        min_embedded_dpi=min(300.0, float(dpi)),
    )
    report['raster'] = {
        'pixels': png_audit['pixels'],
        'dpi': tuple(png_audit['dpi']) if png_audit['dpi'] else None,
        'mode': png_audit['mode'],
    }
    report['png_checks'] = png_audit
    report['svg_checks'] = svg_audit

    if svg_text_to_path and 'outlined_svg' in targets:
        report['outlined_svg_checks'] = inspect_svg(
            targets['outlined_svg'],
            expected_size_mm=(width, height),
            expect_editable_text=False,
            expect_outlined_text=True,
            min_embedded_dpi=min(300.0, float(dpi)),
        )

    actual_name = font_manager.FontProperties(fname=font_file).get_name()
    normalize = lambda s: ''.join(c.lower() for c in s if c.isalnum())

    if include_pdf and pymupdf is not None:
        with pymupdf.open(targets['pdf']) as doc:
            page = doc[0]
            actual_mm = [page.rect.width * 25.4 / 72, page.rect.height * 25.4 / 72]
            fonts = [
                {'name': f[3], 'type': f[2], 'embedded': bool(doc.extract_font(f[0])[3])}
                for f in page.get_fonts(full=True)
            ]
            report['pdf'] = {'size_mm': actual_mm, 'fonts': fonts, 'raster_images': len(page.get_images()), 'inspected': True}
            page.get_pixmap(matrix=pymupdf.Matrix(140 / 72, 140 / 72), alpha=False).save(preview)
        report['preview'] = preview.name
        pdf_dim_ok = all(abs(a - b) < 0.02 for a, b in zip(actual_mm, [width, height]))
        report['checks']['pdf_inspected'] = True
        report['checks']['pdf_fonts_embedded'] = bool(fonts) and all(f['embedded'] for f in fonts)
        report['checks']['times_font_in_pdf'] = any('TimesNewRoman' in f['name'] for f in fonts)
        report['checks']['configured_font_in_pdf'] = any(
            normalize(actual_name) in normalize(f['name']) for f in fonts
        )
    else:
        report['pdf'] = {
            'size_mm': None,
            'fonts': [],
            'raster_images': None,
            'inspected': False,
            'reason': 'pymupdf not installed' if include_pdf else 'PDF export disabled',
        }
        report['preview'] = None
        pdf_dim_ok = bool(svg_audit['dimensions_match'])
        report['checks']['pdf_inspected'] = False
        report['checks']['pdf_fonts_embedded'] = None
        report['checks']['times_font_in_pdf'] = None
        report['checks']['configured_font_in_pdf'] = None
        if include_pdf:
            report['limitations'].append('pymupdf is not installed; PDF font embedding and .preview.png generation were skipped')

    report['checks'].update({
        'page_dimensions': bool(png_audit['pixel_dimensions_match']) and pdf_dim_ok,
        'png_generated': bool(png_audit['valid_png']),
        'png_dpi_ok': bool(png_audit['dpi_matches_target']),
        'png_dpi_is_600': bool(png_audit['dpi_is_600']),
        'png_dimensions_ok': bool(png_audit['pixel_dimensions_match']),
        'png_white_background': bool(png_audit['white_opaque_background']),
        'svg_valid_xml': bool(svg_audit['valid_xml']),
        'svg_is_1_1': bool(svg_audit['is_svg_1_1']),
        'svg_true_vector': bool(svg_audit['is_true_vector']),
        'svg_editable_text': (bool(svg_audit['has_editable_text']) if visible_text_count > 0 else True),
        'svg_no_external_deps': bool(svg_audit['no_external_dependencies']),
        'svg_illustrator_compatible': bool(svg_audit['illustrator_compatible']),
        'svg_embedded_images_dpi_ok': bool(svg_audit['embedded_images_dpi_ok']),
        'illustrator_tested': False,
    })

    if outside:
        report['warnings'].append(f'Text/legend bounds extend outside canvas: {outside}')
    report['warnings'].extend(svg_audit.get('font_compatibility_warnings', []))
    if not svg_audit['embedded_images_dpi_ok']:
        report['warnings'].append(
            f"Embedded raster image inside SVG has effective DPI {svg_audit['min_embedded_image_dpi']} (< 300)"
        )

    critical_failures = []
    if strict_checks:
        if not report['checks']['png_generated']:
            critical_failures.append('PNG failed generation or validation')
        if not report['checks']['png_dpi_ok']:
            critical_failures.append(f"PNG DPI metadata {png_audit['dpi']} does not match expected {dpi}")
        if not report['checks']['png_dimensions_ok']:
            critical_failures.append(
                f"PNG pixel dimensions {png_audit['pixels']} do not match expected {png_audit['expected_pixels']}"
            )
        if not report['checks']['png_white_background']:
            critical_failures.append('PNG does not have an opaque white background')
        if not report['checks']['svg_valid_xml'] or not report['checks']['svg_is_1_1']:
            critical_failures.append('SVG is not valid SVG 1.1 XML')
        if not report['checks']['svg_true_vector']:
            critical_failures.append('SVG appears whole-figure rasterized rather than true vector graphics')
        if visible_text_count > 0 and not report['checks']['svg_editable_text']:
            critical_failures.append('SVG lacks editable <text> elements despite visible figure text')
        if not report['checks']['svg_no_external_deps']:
            critical_failures.append(
                f"SVG contains external dependencies: {svg_audit['external_dependencies']}"
            )
        if not report['checks']['svg_illustrator_compatible']:
            critical_failures.append(
                f"SVG contains Illustrator-incompatible features: {svg_audit['illustrator_incompatible_features']}"
            )

    _atomic_write_text(
        json_target,
        json.dumps(report, ensure_ascii=False, indent=2, default=_json, allow_nan=False),
    )

    if critical_failures:
        raise RuntimeError('Export quality check failed: ' + '; '.join(critical_failures))
    return report


def export_figure(fig, stem, provenance, *, dpi=600, overwrite=False):
    """Preserve page dimensions; preflight overwrite; publish each output atomically.

    Exports PDF, Illustrator-editable SVG, PNG, optional PyMuPDF preview, and JSON audit.
    """
    required = {'data_kind', 'sources', 'transformations'}
    if not required.issubset(provenance):
        raise ValueError(f'Provenance must include {sorted(required)}')
    if provenance['data_kind'] not in ('synthetic', 'simulation', 'experiment'):
        raise ValueError('data_kind must be synthetic, simulation or experiment')
    return _run_export(
        fig,
        stem,
        provenance,
        dpi=dpi,
        overwrite=overwrite,
        include_pdf=True,
        save_py=False,
        require_600_dpi=False,
        strict_checks=False,
    )


def save_publication_figure(
    fig,
    output_name,
    provenance=None,
    *,
    source_script=None,
    dpi=600,
    overwrite=False,
    include_pdf=True,
    svg_text_to_path=False,
    require_600_dpi=True,
    strict_checks=True,
):
    """Unified publication exporter: saves 600 DPI PNG, Illustrator-editable SVG, reproducible .py, PDF, and JSON audit.

    Parameters
    ----------
    fig : matplotlib.figure.Figure
        Figure to export at its exact configured physical dimensions.
    output_name : str | Path
        Output stem (or filename ending in .png/.svg/.pdf/.py/.json).
    provenance : dict, optional
        Provenance metadata (`data_kind`, `sources`, `transformations`, `caption`, etc.).
        If omitted, defaults to an explicit `unspecified` provenance stub.
    source_script : str | Path, optional
        Path to the plotting script or Python source string to save as `<stem>.py`.
        If omitted, automatically snapshots the calling `.py` script when available.
    dpi : int | float, default=600
        PNG resolution and embedded SVG raster resolution. Must be 600 unless `require_600_dpi=False`.
    overwrite : bool, default=False
        Allow replacing existing output files.
    include_pdf : bool, default=True
        Also export `<stem>.pdf` (embedded fonts) and `<stem>.preview.png` (when PyMuPDF is installed).
    svg_text_to_path : bool, default=False
        Keep `<stem>.svg` as editable text (`svg.fonttype='none'`) and additionally export
        `<stem>.outlined.svg` (`svg.fonttype='path'`) as a fallback for systems missing fonts.
    require_600_dpi : bool, default=True
        Enforce 600 DPI for publication PNG exports.
    strict_checks : bool, default=True
        Raise RuntimeError if mandatory PNG or SVG quality checks fail.
    """
    out_path = Path(output_name)
    if out_path.suffix.lower() in _STRIP_EXTS:
        out_path = out_path.with_suffix('')
    if provenance is None:
        prov = {
            'data_kind': 'unspecified',
            'sources': [],
            'transformations': [],
            'auto_provenance': True,
        }
    else:
        if not isinstance(provenance, dict):
            raise ValueError('provenance must be a dict when provided')
        prov = dict(provenance)
        prov.setdefault('data_kind', 'unspecified')
        prov.setdefault('sources', [])
        prov.setdefault('transformations', [])
        if prov['data_kind'] not in ('synthetic', 'simulation', 'experiment', 'unspecified'):
            raise ValueError('data_kind must be synthetic, simulation, experiment, or unspecified')
    return _run_export(
        fig,
        out_path,
        prov,
        dpi=dpi,
        overwrite=overwrite,
        include_pdf=include_pdf,
        save_py=True,
        source_script=source_script,
        svg_text_to_path=svg_text_to_path,
        require_600_dpi=require_600_dpi,
        strict_checks=strict_checks,
    )
