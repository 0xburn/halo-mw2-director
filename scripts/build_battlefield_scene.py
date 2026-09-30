#!/usr/bin/env python3
"""Author the first-person MW2 / CE sniper reveal as editable scene JSON."""
import json
from pathlib import Path
teams=[
 dict(id='mw_red',count=4,model='soldier',weapon='intervention',color='#b9775b',origin=[0,-5.82,-7],spacing=[0,0,2.5]),
 dict(id='mw_blue',count=4,model='soldier',weapon='intervention',color='#768c9c',origin=[12,-5.82,-7],spacing=[0,0,2.5]),
 dict(id='halo_red',count=4,model='chief',weapon='sniper',color='#ab3530',origin=[-3,-5.82,-13],spacing=[0,0,-3.3]),
 dict(id='halo_blue',count=4,model='chief',weapon='sniper',color='#4267bb',origin=[11,-5.82,-13],spacing=[0,0,-3.3]),
]
actions=[]
for own,opponent in [('mw_red','mw_blue'),('mw_blue','mw_red'),('halo_red','halo_blue'),('halo_blue','halo_red')]:
 for i in range(1,5):
  actor=f'{own}-{i}';target=f'{opponent}-{i}'
  actions.append(dict(at=0,actor=actor,type='aim',target=target))
  if actor!='mw_red-1':
   actions.append(dict(at=8.1+i*.19+(.65 if own.endswith('blue') else 0),actor=actor,type='fire',target=target,count=8,every=1.8))
   actions.append(dict(at=9+i*.25,actor=actor,type='move',by=[0,0,.7 if i%2 else -.7],duration=1.8))
   actions.append(dict(at=14+i*.25,actor=actor,type='move',by=[0,0,-.7 if i%2 else .7],duration=1.8))
actions += [dict(at=0,actor='halo_blue-1',type='respawn',position=[10,-5.82,-7]),dict(at=0,actor='halo_blue-1',type='aim',target='mw_red-1'),dict(at=2.2,actor='mw_red-1',type='fire',target='mw_blue-1'),dict(at=4,actor='mw_red-1',type='aim',target='halo_blue-1'),dict(at=5.4,actor='halo_blue-1',type='fire',target='mw_red-1'),dict(at=5.43,actor='mw_red-1',type='die'),dict(at=7.5,actor='halo_blue-1',type='aim',target='halo_red-1')]
camera=[
 dict(at=0,position=[0,-4.17,-7],target='mw_blue-1',fov=76,pov='mw_red-1'),
 dict(at=1.6,position=[0,-4.17,-7],target='mw_blue-1',fov=76,pov='mw_red-1'),
 dict(at=1.95,position=[0,-4.17,-7],target='mw_blue-1',fov=20,pov='mw_red-1',scope=True),
 dict(at=2.22,position=[0,-4.13,-7],target='mw_blue-1',fov=20,pov='mw_red-1',scope=True),
 dict(at=2.6,position=[0,-4.17,-7],target='mw_blue-1',fov=76,pov='mw_red-1'),
 dict(at=4,position=[0,-4.17,-7],target='halo_blue-1',fov=76,pov='mw_red-1'),
 dict(at=5.4,position=[0,-4.17,-7],target='halo_blue-1',fov=76,pov='mw_red-1'),
 dict(at=5.9,position=[-.2,-5.0,-6.7],target='halo_blue-1',fov=80,pov='mw_red-1',roll=-.28),
 dict(at=6,position=[-.2,-5.0,-6.7],target='halo_blue-1',fov=80,roll=-.28),
 dict(at=10,position=[-10,6,12],target=[7,-3.5,-13],fov=70,caption='RUST  //  TWO 4v4 SNIPER FIGHTS'),
 dict(at=12,position=[-10,9,12],target=[7,-3.5,-13],fov=70,caption='RUST  //  TWO 4v4 SNIPER FIGHTS'),
 dict(at=12.1,position=[-6,-2,-7],target='halo_blue-1',fov=55,cut=True),
 dict(at=16,position=[-5,-2.2,-13],target='halo_blue-2',fov=55),
 dict(at=16.1,position=[16,-2,1],target='mw_red-2',fov=60,cut=True),
 dict(at=19,position=[15,-.7,4],target='mw_red-2',fov=60),
 dict(at=24,position=[1,17,15],target=[10,-3,-16],fov=68),
]
scene=dict(version=1,name='Rust — worlds collide',duration=24,teams=teams,actions=actions,camera=camera)
p=Path(__file__).resolve().parents[1]/'web/scenes/worlds-collide.json';p.write_text(json.dumps(scene,indent=2)+'\n')
