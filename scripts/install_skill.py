"""Install or symlink personal-scientific-plotting for Antigravity, Claude Code, and Codex."""
from pathlib import Path
import argparse
import os
import shutil
import sys

SKILL_NAME = 'personal-scientific-plotting'
RUNTIME_ITEMS = (
    'SKILL.md',
    'README.md',
    'requirements.txt',
    'package_manifest.json',
    'scripts',
    'assets',
    'references',
)
IGNORE_NAMES = ('__pycache__', '*.pyc', '*.pyo', '.cache', '.venv', 'outputs')


def default_targets():
    home = Path.home()
    codex_home = Path(os.environ['CODEX_HOME']).expanduser() if os.environ.get('CODEX_HOME') else home / '.codex'
    return {
        'antigravity': home / '.gemini' / 'config' / 'skills' / SKILL_NAME,
        'claude': home / '.claude' / 'skills' / SKILL_NAME,
        'codex': codex_home / 'skills' / SKILL_NAME,
    }


def install_to(source_root, dest, *, mode='copy', overwrite=False, dry_run=False):
    source_root = Path(source_root).resolve()
    dest = Path(dest)
    if dest.exists() or dest.is_symlink():
        if not overwrite:
            raise FileExistsError(f'Target already exists: {dest} (pass --overwrite to replace)')
        if not dry_run:
            if dest.is_symlink() or dest.is_file():
                dest.unlink()
            else:
                shutil.rmtree(dest)

    if dry_run:
        print(f'[dry-run] {mode}: {source_root} -> {dest}')
        return

    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == 'symlink':
        dest.symlink_to(source_root, target_is_directory=True)
    else:
        dest.mkdir(parents=True, exist_ok=True)
        ignore = shutil.ignore_patterns(*IGNORE_NAMES)
        for item in RUNTIME_ITEMS:
            src = source_root / item
            dst = dest / item
            if src.is_dir():
                shutil.copytree(src, dst, ignore=ignore)
            elif src.is_file():
                shutil.copy2(src, dst)
    print(f'Installed ({mode}) -> {dest}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--target',
        nargs='+',
        choices=['antigravity', 'claude', 'codex', 'all'],
        default=['all'],
        help='Agent skill location(s) to install into',
    )
    parser.add_argument('--mode', choices=['copy', 'symlink'], default='copy')
    parser.add_argument('--overwrite', action='store_true')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    targets = default_targets()
    selected = list(targets.keys()) if 'all' in args.target else list(dict.fromkeys(args.target))

    for name in selected:
        install_to(
            repo_root,
            targets[name],
            mode=args.mode,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
        )


if __name__ == '__main__':
    sys.dont_write_bytecode = True
    main()
