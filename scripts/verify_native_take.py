#!/usr/bin/env python3
"""Check the latest completed native take's real simulation telemetry."""
import argparse, ast, re
from pathlib import Path
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',nargs='?',type=Path,default=root/'local-runs/cinema/iw4l-artifacts/logs/latest.log');args=p.parse_args()
takes=[s for s in args.log.read_text().split('CINEMA V2:')[1:] if 'CINEMA COMPLETE:' in s]
assert takes,'No completed v2 native take in log'
s=takes[-1].split('CINEMA COMPLETE:')[0]
deaths=[(float(t),int(i)) for t,i in re.findall(r'CINEMA DEATH t=([\d.]+) id=(\d+)',s)]
main=[(t,i) for t,i in deaths if i in (0,1,2)]
assert [i for _,i in main]==[1,2,0],f'Expected two opponents then player to die; got {main}'
rows=[]
for m in re.finditer(r'CINEMA STATE t=([\d.]+) id=(\d+) p=(\[[^\]]+\]) hp=(-?\d+) ads=([\d.]+).*? sprint=(true|false) speed=([\d.]+)',s):
 t,i,pos,hp,ads,sprint,speed=m.groups();rows.append(dict(t=float(t),id=int(i),pos=ast.literal_eval(pos),hp=int(hp),ads=float(ads),sprint=sprint=='true',speed=float(speed)))
assert rows,'No movement telemetry'
player=[r for r in rows if r['id']==0 and r['t']<main[-1][0]]
assert max(r['pos'][2] for r in player)-min(r['pos'][2] for r in player)>250,'Player did not climb the ramp'
assert all(r['hp']==30 for r in player),'Player took damage before Chief shot'
for start,end in [(0,1),(1.4,2.5),(3.0,3.7)]:
 assert any(r['sprint'] and r['speed']>140 for r in player if start<=r['t']<=end),f'No actual sprint in {start}–{end}s'
chief=[r for r in rows if r['id']==8 and r['t']<main[-1][0]+.2]
assert chief and all(r['ads']==0 for r in chief),'Chief was scoped; expected a hip-fire shot'
print('PASS: two real kills, then player death; 30 HP; ramp ascent; three sprint bursts; Chief unscoped.')
print('Death timings:',', '.join(f'actor {i} at {t:.3f}s' for t,i in main))
