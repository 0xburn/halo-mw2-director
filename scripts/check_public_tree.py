#!/usr/bin/env python3
"""Check the staged public tree for local assets, credentials and machine paths."""
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
paths = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
private_roots = ('.tools/', 'local-assets/', 'local-runs/', 'exports/', 'previews/', 'vendor-src/', 'context/', 'docs/starter/')
blocked_extensions = {'.ff', '.iwd', '.iwi', '.d3dbsp', '.bik', '.map', '.iso', '.rar', '.glb',
                      '.gltf', '.rgba', '.wav', '.mp4', '.webm', '.exe', '.dll', '.dylib', '.pem', '.key'}
secret_shapes = [re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}'), re.compile(r'github_pat_[A-Za-z0-9_]{40,}'),
                 re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----')]
failures = []
total = 0
for name in filter(None, paths):
    path = Path(name)
    if (name.startswith(private_roots) or (name.startswith('web/assets/') and name != 'web/assets/README.txt')
            or path.suffix.lower() in blocked_extensions or path.name.startswith('.env')
            or name in ('HANDOFF.md', 'VERIFICATION.md', 'web/config.json') or '__pycache__' in path.parts):
        failures.append((name, 'private/generated/game data must not be published'))
    data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
    total += len(data)
    if b'\0' in data:
        failures.append((name, 'unexpected binary file'))
        continue
    text = data.decode('utf8', errors='replace')
    if str(Path.home()) in text:
        failures.append((name, 'machine-specific home path'))
    if any(pattern.search(text) for pattern in secret_shapes):
        failures.append((name, 'possible credential/private key'))
for name, reason in failures:
    print(f'BLOCKED: {name}: {reason}')
if failures:
    sys.exit(1)
print(f'PASS: {len(list(filter(None, paths)))} staged source files, {total:,} bytes; no excluded asset paths, known credential shapes or home paths.')
print('This is an accidental-disclosure check, not proof of provenance or licensing.')
