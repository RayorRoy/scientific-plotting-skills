"""Inspect, validate or compose appearance-only JSON templates."""
from pathlib import Path
import argparse
import json
import os
import sys

sys.dont_write_bytecode=True
os.environ.setdefault('MPLCONFIGDIR',str(Path.cwd()/'.cache/matplotlib'))
from houseplot.profiles import DIRECTORY,DEFAULT_PROFILE,load_profile,profile_fingerprint,compose_profile


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    sub.add_parser('list')
    for name in ['show','validate']:
        p=sub.add_parser(name);p.add_argument('profile')
    p=sub.add_parser('compose');p.add_argument('--base',default=DEFAULT_PROFILE)
    p.add_argument('--patch',type=Path,required=True);p.add_argument('--id',required=True)
    p.add_argument('--version',required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--evidence',type=Path,help='JSON source object with kind/references/observations to add')
    args=parser.parse_args()
    if args.command=='list':
        for file in sorted(DIRECTORY.glob('*.json')):
            p=load_profile(file);print(f'{p["id"]}\t{p["version"]}\t{p["status"]}')
    elif args.command in ('show','validate'):
        p=load_profile(args.profile)
        print(json.dumps(p,indent=2,ensure_ascii=False) if args.command=='show' else f'Valid: {p["id"]}@{p["version"]} SHA256={profile_fingerprint(p)}')
    else:
        patch=json.loads(args.patch.read_text(encoding='utf-8'))
        source=json.loads(args.evidence.read_text(encoding='utf-8')) if args.evidence else None
        derived=compose_profile(args.base,profile_id=args.id,version=args.version,patch=patch,source=source)
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with args.output.open('x',encoding='utf-8') as stream:
            json.dump(derived,stream,indent=2,ensure_ascii=False);stream.write('\n')
        print(f'Created draft {derived["id"]}@{derived["version"]}: {args.output}')


if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8');main()
