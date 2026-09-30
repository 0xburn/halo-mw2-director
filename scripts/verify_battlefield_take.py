#!/usr/bin/env python3
"""Verify native cinematic outcomes from the actual completed runtime trace."""
import argparse,ast,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('log',nargs='?',type=Path,default=ROOT/'local-runs/cinema/iw4l-artifacts/logs/latest.log');args=p.parse_args()
segments=[x for x in args.log.read_text().split('CINEMA V2:')[1:] if 'CINEMA COMPLETE:' in x]
assert segments,'No completed take'
s=segments[-1].split('CINEMA COMPLETE:')[0]
deaths=[(float(t),int(i)) for t,i in re.findall(r'CINEMA DEATH t=([\d.]+) id=(\d+)',s)]
assert [i for _,i in deaths if i<3]==[1,2,0],deaths
assert 'killcam: script seat viewer=0' not in s,'Killcam rewound the local view'
for sound in ('warthog-engine','halo-splat','chief-death','warthog-splat','triple-kill'):
 assert f'CINEMA SOUND play {sound} ' in s,f'Missing audio playback: {sound}'
assert 'CINEMA TRIPLE KILL' in s,'No confirmed native rocket triple kill'
impact=re.findall(r'CINEMA SPLATTER t=([\d.]+)',s)
promotion=re.findall(r'CINEMA PROMOTION impact t=([\d.]+) sound=mp_level_up',s)
assert len(impact)==1 and promotion==impact,'Promotion must trigger once, at the Warthog impact'
assert s.count('CINEMA PROMOTION overlay key=promotion duration_ms=4000')==1,'Native promotion overlay did not activate exactly once'
assert sum('kind=grenade' in line for line in s.splitlines() if 'CINEMA EXPLOSION' in line)>=20,'Foreground grenades failed to detonate'
assert 'CINEMA SHOT actor=13 ' in s,'Rocket actor did not fire the native weapon'
rows=[]
for m in re.finditer(r'CINEMA STATE t=([\d.]+) id=(\d+) p=(\[[^\]]+\]) hp=(-?\d+) ads=([\d.]+).*? sprint=(true|false) speed=([\d.]+)',s):
 t,i,pos,hp,ads,sprint,speed=m.groups();rows.append(dict(t=float(t),id=int(i),p=ast.literal_eval(pos),hp=int(hp),ads=float(ads),sprint=sprint=='true',speed=float(speed)))
air=[r for r in rows if r['id']==13 and 8.6<r['t']<10.4]
assert max(r['p'][2] for r in air)>295,'No upward jump from the 268-inch platform'
assert min(r['p'][2] for r in air)<100,'Rocket actor never left the tower'
assert any(i==6 and 13.3<t<15 for t,i in deaths),'No foreground sniper duel kill for the ending'
for i in (11,12,14,15):
 final=[r for r in rows if r['id']==i and r['t']>22]
 assert final and all(r['hp']>0 for r in final),f'Final Spartan {i} died'
 assert all((r['p'][0]+130)**2+(r['p'][1]-220)**2<80**2 for r in final),f'Spartan {i} missed the ending mark'
sprinters={r['id'] for r in rows if 5.5<r['t']<14 and r['id']>0 and r['hp']>0 and r['sprint'] and r['speed']>200}
assert len(sprinters)>=8,f'Only {len(sprinters)} background actors sprinted'
print('PASS: opening kills; no killcam rewind; impact promotion; engine/impact/death audio; native airborne RPG shot; rocket triple; 20+ grenade blasts; four live Spartans at corpse.')
print('Fast background sprinters:',sorted(sprinters))
print('Deaths:',deaths)
