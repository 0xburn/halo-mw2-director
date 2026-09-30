#!/usr/bin/env python3
"""Inspect, validate, compile and preview native cinematic scene recipes."""
import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from director.core import ZONE, SceneError, compile_scene, describe, doctor, read, validate, write_scene


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['catalog', 'inspect', 'check', 'build', 'preview'])
    parser.add_argument('scene', nargs='?', type=Path)
    parser.add_argument('-o', '--output', type=Path)
    args = parser.parse_args()
    if args.command == 'catalog':
        print(json.dumps({'maps': [{'id': p.stem, 'status': 'rehearsed' if p.stem == 'mp_rust' else 'installed; unverified'}
                                  for p in sorted(ZONE.glob('mp_*.ff')) if not p.stem.endswith('_load')],
                          'templates': [p.name.removesuffix('.native.json') for p in (ROOT/'director/templates').glob('*.native.json')],
                          'characters': ['MW2 soldier (slots 0–7)', 'CE blue Chief on MW2 rig (slots 8–15)'],
                          'note': 'Installed files are not a guarantee of native map/rig compatibility. Halo map playback is not implemented here.'}, indent=2))
        return
    if args.scene is None:
        parser.error('scene file is required')
    scene = compile_scene(read(args.scene))
    warnings = validate(scene)
    if args.command == 'inspect':
        print(json.dumps(describe(scene), indent=2))
        return
    assets = doctor(scene) if args.command != 'build' else {'status': 'not checked during offline build; use check before preview'}
    print(json.dumps({'checks': 'passed', 'assets': assets, 'warnings': warnings}, indent=2))
    if args.command == 'check':
        return
    output = args.output or ROOT / 'local-assets/scenes' / f'{args.scene.stem}.native.json'
    path = write_scene(output, scene)
    print(f'Compiled native scene: {path}', flush=True)
    if args.command == 'preview':
        launcher = str(ROOT / 'scripts/native_scene.sh')
        os.execv(launcher, [launcher, '--scene', str(path), '--map', assets['map']])


if __name__ == '__main__':
    try:
        main()
    except (SceneError, KeyError, TypeError, OSError) as error:
        print(f'Scene error: {error}', file=sys.stderr)
        sys.exit(1)
