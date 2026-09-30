#!/usr/bin/env python3
"""Record the running native window and audio, replay, and export a scene-only MP4."""
import argparse
import datetime
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('output', nargs='?', type=Path)
p.add_argument('--raw', type=Path, help='Reuse an existing raw recording and its timing JSON')
p.add_argument('--crop', help='Optional capture-border crop: width:height:x:y')
p.add_argument('--scene', type=Path, help='Scene JSON used by the running native window')
args = p.parse_args()
stamp = datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
output = (args.output or ROOT / 'exports' / f'rust-halo-{stamp}.mp4').resolve()
output.parent.mkdir(parents=True, exist_ok=True)
if output.exists():
    raise SystemExit(f'Refusing to overwrite {output}; choose a new filename.')
raw = args.raw.resolve() if args.raw else output.with_name(output.stem + '-raw.mp4')
source = ROOT / 'scripts/record_native_scene.swift'
recorder = ROOT / '.tools/record-native-scene'
if not args.raw and (not recorder.exists() or source.stat().st_mtime > recorder.stat().st_mtime):
    subprocess.run(['swiftc', '-parse-as-library', str(source), '-o', str(recorder),
                    '-module-cache-path', str(ROOT / '.tools/swift-module-cache')], check=True)
if not args.raw:
    command = [str(recorder), str(ROOT), str(raw)]
    if args.scene:
        command.append(str(args.scene.resolve()))
    subprocess.run(command, check=True)
timing = json.loads(raw.with_suffix('.json').read_text())
video_filter = f'crop={args.crop},scale=1280:720,setsar=1,fps=60' if args.crop else 'fps=60'
subprocess.run(['ffmpeg', '-hide_banner', '-nostdin', '-n',
                '-ss', str(timing['trim_start_seconds']), '-i', str(raw),
                '-t', str(timing['take_duration_seconds']), '-map', '0:v:0', '-map', '0:a:0',
                '-vf', video_filter, '-c:v', 'libx264', '-preset', 'fast', '-crf', '18',
                '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k',
                '-movflags', '+faststart', str(output)], check=True)
probe = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_streams',
                                           '-show_format', '-of', 'json', str(output)]))
assert {'audio', 'video'} <= {s['codec_type'] for s in probe['streams']}
output.with_suffix('.json').write_text(json.dumps({'capture': timing, 'crop': args.crop, 'media': probe}, indent=2))
print(f'Exported: {output}')
