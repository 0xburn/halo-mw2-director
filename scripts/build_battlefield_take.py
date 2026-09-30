#!/usr/bin/env python3
"""Native Rust/Warthog battlefield take. All times are seconds; positions IW inches/Z-up."""
import argparse,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ATTACK,SPRINT,JUMP,ADS,BREATH,FRAG=1,2,1024,2048,8192,16384

def aim(a,b,target,**kw):return dict(start=a,end=b,actor=target,**kw)
def actor(i,name,route,aims=(),buttons=(),weapon=None,yaw=90):return dict(id=i,name=name,weapon=weapon or ('wa2000_mp' if i>=8 else 'cheytac_mp'),yaw=yaw,route=route,aim=list(aims),buttons=list(buttons))
actors=[
 actor(0,'xX RampGod Xx',[[0,470,40,-210],[.55,510,180,-220],[1.3,513,285,-155],[2.3,513,480,-40],[3.1,513,500,-30],[3.7,513,660,80],[5.5,513,680,95],[24,513,680,95]],
  [aim(.76,1.36,1,height=40,turn_speed=540,response=26),aim(2.48,3.12,2,height=35,turn_speed=680,response=32),aim(3.75,4.75,8,height=55),dict(start=4.86,end=24,point=[513,880,190],turn_speed=640)],
  [[0,1.03,SPRINT],[1.,1.37,ADS|BREATH],[1.30,1.37,ATTACK],[1.37,2.78,SPRINT],[2.75,3.13,ADS|BREATH],[3.05,3.12,ATTACK],[3.13,3.98,SPRINT],[3.94,4.78,ADS|BREATH]]),
 actor(1,'iTz Scopez',[[0,205,320,-242],[.55,130,405,-242],[1.35,115,590,-242],[2.0,220,665,-242],[24,220,665,-242]],[],[[0,1.4,SPRINT]],yaw=128),
 actor(2,'FaZe-ish',[[0,-80,520,-242],[.8,-160,550,-242],[1.6,-100,530,-242],[2.3,-110,590,-242],[3.3,-100,645,-242],[24,-100,645,-242]],
  [aim(0,2.2,0,offset_z=90),aim(2.2,2.65,0,offset_z=28),aim(2.65,24,0,offset_z=90)],[[.35,.5,JUMP],[2.0,2.65,ADS],[2.34,2.43,ATTACK],[1.2,1.33,JUMP]],yaw=180),
 actor(8,'Master Chief',[[0,1360,560,-210],[6,1360,560,-242],[8,1250,680,-242],[10,1380,730,-242],[12,1150,710,-242],[16,1370,500,-242],[24,1100,570,-242]],
  [aim(0,5.5,0,height=48),aim(6,24,7)],[[6.8,7.2,ADS],[7.05,7.14,ATTACK],[9.3,9.65,ADS],[9.55,9.64,ATTACK],[10.4,10.52,JUMP],[13.1,13.2,ATTACK],[18.1,18.2,ATTACK]]),
]
# Each duel alternates movement, fast scope pulls, misses and later lethal shots.
for i,x,y,target in [(3,180,720,11),(4,20,500,12),(5,-130,550,14),(6,1040,60,9),(7,1320,190,10),(9,1030,850,6),(10,1480,850,7),(11,30,1150,3),(12,240,1230,4),(14,450,1050,5)]:
 route=[[0,x,y,-230]]
 for k,t in enumerate([.6,1.3,2.1,3.,4.,5.1,6.3,7.2,8.5,9.5,10.6,11.7,13,14.2,15.5,17,19,21,24]):
  route.append([t,x+(-1 if k%2 else 1)*(65+(k%3)*15),y+((k%4)-1)*38,-230])
 aims=[];buttons=[]
 for k in range(10):
  shot=.5+(i%3)*.24+k*2.25
  if shot>23:break
  # Misses pass shoulders/heads; actual native lethal shots begin in the reveal.
  miss=shot<10.5 or (k%3!=2)
  aims.append(aim(shot-.33,shot+.12,target,height=44,offset_z=85 if miss else 0))
  buttons += [[shot-.18,shot+.12,ADS],[shot,shot+.085,ATTACK],[shot+.14,shot+.75,SPRINT]]
  if k%2==0:buttons.append([shot+.6,shot+.73,JUMP])
 weapon='usp_mp' if i in (9,10,12) else None
 if weapon:
  # Visible shots use the native pistol animation; plasma travel/damage is separate.
  aims=[aim(0,24,target,offset_z=75)]
 actors.append(actor(i,('Spartan ' if i>=8 else 'MW2 ')+str(i),route,aims,buttons,weapon,yaw=90 if i<8 else -90))
# The landing group keeps fighting as the rocket Spartan drops from the tower.
for a in actors:
 if a['id'] in (3,4,5):
  dx={3:-55,4:0,5:55}[a['id']]
  a['route']=[r for r in a['route'] if r[0]<11]+[[11.5,-50+dx,480,-240],[12.6,20+dx,480,-240],[13.8,-50+dx,450,-240],[15,-15+dx,500,-240],[24,-15+dx,500,-240]]
actors.append(actor(13,'Air Chief',[[0,750,1090,530],[11.4,750,1090,530],[12.1,720,990,530],[12.65,670,850,350],[13.7,590,660,-200],[16,710,500,-230],[24,700,550,-230]],
 [dict(start=0,end=11.4,point=[300,600,-190]),dict(start=11.4,end=24,point=[280,595,-215])],[[11.85,12.03,JUMP],[11.5,12.05,SPRINT]],weapon='rpg_mp',yaw=-90))
actors.append(actor(15,'Chief Uber',[[0,1950,-1000,-240],[24,1950,-1000,-240]],[],[],yaw=90))
battle=[dict(at=2.36,kind='near_miss',actor=2,target=0,offset=[0,0,26]),dict(at=4.7,kind='engine'),dict(at=6.6,kind='engine',volume=.4),dict(at=8.6,kind='engine',volume=.25)]
for i,target in [(9,6),(10,7),(12,4)]:
 for k in range(28):
  t=.2+(i%3)*.19+k*.78
  if t<23:battle.append(dict(at=round(t,3),kind='plasma',actor=i,target=target,offset=[35 if k%3 else -25,0,55 if t<10 else 12]))
for t,i,target in [(6.7,12,4),(9.1,10,7),(17.3,9,6),(20.1,12,5)]:battle.append(dict(at=t,kind='grenade',actor=i,target=target,flight=.95,fuse=2.))
battle.append(dict(at=12.55,kind='rocket',actor=13,point=[-30,480,-222],flight=.65,fuse=3))
# The Warthog stays on the ramp and brakes in the open yard at its foot.
vehicle=dict(start=4.55,draw_start=4.35,radius=92,route=[[0,513,845,113],[4.55,513,845,113],[5.05,513,645,67],[5.6,513,410,-72],[6.1,550,220,-205],[6.65,730,100,-240],[7.3,960,90,-240],[8.0,1080,90,-240],[24,1080,90,-240]])
by_id={a['id']:a for a in actors}
player=by_id[0]
player['buttons']=[[0,1.14,SPRINT],[1.11,1.37,ADS|BREATH],[1.30,1.37,ATTACK],[1.37,2.86,SPRINT],[2.83,3.13,ADS|BREATH],[3.05,3.12,ATTACK],[3.13,3.58,SPRINT],[3.55,4.40,ADS|BREATH]]
player['aim']=[aim(.84,1.37,1,height=40,turn_speed=540,response=26),aim(2.48,3.13,2,height=35,turn_speed=680,response=32),aim(3.43,4.4,8,height=55),dict(start=4.43,end=24,point=[513,840,160],turn_speed=580)]
player['route']=[[0,470,40,-210],[.55,510,180,-220],[1.3,513,285,-155],[2.3,513,480,-40],[3.1,513,500,-30],[3.55,513,620,43],[4.4,513,650,70],[24,513,650,70]]
# Put the plasma duel and grenade throw in the open western lane, in shot.
for i,x,y,target in [(9,1370,70,7),(10,-320,710,4),(12,-310,510,4),(15,-300,240,6)]:
 a=by_id[i]
 a['route']=[[0,x,y,-230]]+[[t,x+(-1 if k%2 else 1)*65,y+((k%3)-1)*45,-230] for k,t in enumerate([1.,2.2,3.5,5.,6.3,7.6,9.,10.5,12.,13.5,14.5,24])]
 a['aim']=[aim(0,24,target,height=44,offset_z=65)]
 a['weapon']='usp_mp' if i in (9,10,12) else 'wa2000_mp'
# Background rifles miss during the opening; the triple-kill group stays alive until the rocket.
for i in [8,11,14,15]:
 a=by_id[i]
 for cue in a['aim']:
  if cue['start']>=5.5 or i!=8:cue['offset_z']=90
by_id[5]['route']=[r if r[0]>=11 else [r[0],r[1]-60,r[2]-340,r[3]] for r in by_id[5]['route']]
# Deliberate jump off the west edge of the tower, firing during the fall.
by_id[13]['route']=[[0,750,1090,275],[11.4,750,1090,275],[12.,670,1030,275],[12.6,510,850,170],[13.8,300,680,-240],[16,100,570,-235],[24,90,600,-235]]
by_id[13]['aim']=[dict(start=0,end=24,point=[-30,480,-222])]
by_id[13]['buttons']=[[11.5,12.05,SPRINT],[11.87,12.03,JUMP]]
# A fresh native corpse is the ending's punchline. Four live Spartans walk up,
# face the body and repeatedly crouch with staggered cadences.
victim=by_id[6]
victim['route']=[[0,900,140,-240],[4,1100,100,-240],[7,820,110,-240],[10,470,100,-235],[12,100,170,-235],[14,-130,220,-240],[24,-130,220,-240]]
victim['buttons']=[b for b in victim['buttons'] if b[1]<13]
victim['aim']=[aim(0,14.5,9,offset_z=85),aim(14.5,24,11)]
for i,xy,phase in [(11,(-166,248),0.),(12,(-92,248),.16),(14,(-166,190),.31),(15,(-92,190),.43)]:
 a=by_id[i];a['route']=[r for r in a['route'] if r[0]<13]+[[14.5,xy[0]-60,xy[1]+90,-240],[16.4,*xy,-240],[24,*xy,-240]]
 a['aim']=[c for c in a['aim'] if c['start']<13]
 for cue in a['aim']:cue['end']=min(cue['end'],14.)
 a['aim'] += [aim(14.,15.6,6,height=38),dict(start=15.6,end=24,point=[-130,220,-236])]
 a['buttons']=[b for b in a['buttons'] if b[1]<13]
 for k in range(11):
  t=16.6+phase+k*.64
  if t<24:a['buttons'].append([t,t+.34,512])
 if i==11:a['buttons'] += [[14.95,15.35,ADS],[15.21,15.32,ATTACK]]
battle=[dict(at=2.36,kind='near_miss',actor=2,target=0,offset=[0,0,24]),dict(at=4.05,kind='engine',volume=.8)]
for i,target in [(9,7),(10,4),(12,3)]:
 for k in range(30):
  t=.15+(i%3)*.19+k*.74
  if t<23 and not(i==12 and t>13):battle.append(dict(at=round(t,3),kind='plasma',actor=i,target=target,offset=[30 if k%3 else -25,0,65 if t<15 else 16]))
for t,i,point in [(6.65,12,[-90,850,-224]),(8.6,10,[100,150,-224]),(18.1,9,[1350,450,-224])]:battle.append(dict(at=t,kind='grenade',actor=i,point=point,flight=.95,fuse=2.))
battle.append(dict(at=12.55,kind='rocket',actor=13,point=[-30,480,-222],flight=.65,fuse=3))
# Loud, comic downhill charge; decelerate before the broad yard turn.
vehicle=dict(start=4.58,draw_start=4.54,radius=92,stop=6.75,route=[
 [0,513,940,148],[4.58,513,940,148],[4.8,513,685,90],
 [5.08,513,370,-90],[5.25,532,210,-207],[5.5,660,100,-240],
 [5.9,865,80,-240],[6.3,1030,80,-240],[6.75,1080,80,-240],[24,1080,80,-240]])
# The western yard has room for the opening's opponents and the final gag.
by_id[5]['route']=[[0,45,385,-236],[4,100,405,-236],[8,25,430,-236],[11,70,485,-236],[12.5,35,475,-236],[14,10,500,-236],[24,10,500,-236]]
by_id[6]['route']=[[0,-130,220,-232],[4,-75,230,-232],[8,-165,205,-232],[11,-90,235,-232],[14,-130,220,-232],[24,-130,220,-232]]
by_id[6]['buttons']=[b for b in by_id[6]['buttons'] if b[0]<10 and b[2]&SPRINT==0 and b[2]&JUMP==0]
by_id[12]['route']=[[0,55,790,-236],[4,110,750,-236],[7,40,790,-236],[10,100,810,-236],[12,75,720,-236],[13.5,20,470,-236],[15,-92,248,-232],[24,-92,248,-232]]
# Avoid the second quickscope's line during the opening; move into the yard later.
by_id[10]['route']=[[0,10,800,-236],[3.5,20,820,-236],[5.5,-140,740,-236],[8,-50,640,-236],[11,-175,700,-236],[14,-90,620,-236],[18,-210,660,-236],[24,-90,700,-236]]
by_id[9]['route']=[[0,1120,120,-235],[4,1200,130,-235],[8,1100,200,-235],[12,1220,190,-235],[16,1100,130,-235],[20,1210,190,-235],[24,1110,210,-235]]
# Jump earlier so the rocket is launched while actually airborne, off the west edge.
by_id[13]['route']=[[0,750,1090,275],[11.2,750,1090,275],[11.65,650,1000,275],[12.05,480,880,150],[12.7,350,760,-70],[13.5,180,610,-240],[24,180,610,-240]]
by_id[13]['buttons']=[[11.2,12.,SPRINT],[11.48,11.62,JUMP]]
# Search glances between flicks, then a short recognition beat on Chief.
player['aim']=[aim(.84,1.37,1,height=40,turn_speed=540,response=26),
 dict(start=1.60,end=1.88,point=[780,1100,100],turn_speed=390,response=23),
 dict(start=1.94,end=2.18,point=[290,1100,100],turn_speed=430,response=24),
 aim(2.48,3.13,2,height=35,turn_speed=680,response=32),
 dict(start=3.32,end=3.57,point=[1020,1110,10],turn_speed=460,response=25),
 dict(start=3.57,end=3.86,point=[1530,1080,-170],turn_speed=430,response=25),
 aim(3.86,4.88,8,height=55,turn_speed=440,response=25),
 dict(start=4.91,end=24,point=[513,940,185],turn_speed=580)]
player['buttons']=[[0,1.14,SPRINT],[1.11,1.37,ADS|BREATH],[1.30,1.37,ATTACK],
 [1.37,2.86,SPRINT],[2.83,3.13,ADS|BREATH],[3.05,3.12,ATTACK],
 [3.13,3.68,SPRINT],[4.13,4.88,ADS|BREATH]]
# Give the reveal its recognition beat, without slowing the vehicle itself.
for r in vehicle['route']:
 if 0<r[0]<24:r[0]+=.55
vehicle['start']+=.55;vehicle['draw_start']+=.55;vehicle['stop']+=.55
# Earlier, real native jump: follow the presented body, then return to the lockoff.
for r in by_id[13]['route']:
 if 0<r[0]<24:r[0]-=2.6
by_id[13]['buttons']=[[8.6,9.4,SPRINT],[8.88,9.02,JUMP]]
for i in (3,4,5):
 a=by_id[i]
 a['route']=[r for r in a['route'] if r[0]<7]+[[8.,-60+(i-3)*55,485,-236],[9.6,-75+(i-3)*55,465,-236],[10.5,-55+(i-3)*55,475,-236],[24,-55+(i-3)*55,475,-236]]
 a['damage_from']=[13]
# Keep all four actors close enough to reach the final corpse without crossing
# the central buildings. All approach continuously through native movement.
for i,x,y in [(11,-180,320),(12,-60,390),(14,20,210),(15,-280,240)]:
 a=by_id[i];tail=[r for r in a['route'] if r[0]>=14.5]
 a['route']=[[0,x,y,-236],[3,x+40,y+20,-236],[6,x-35,y+30,-236],[9,x+25,y-20,-236],[12,x,y,-236]]+tail
 a['buttons']=[b for b in a['buttons'] if not(b[0]<13 and b[2]&(SPRINT|JUMP))]
 a['damage_from']=[]
by_id[6]['damage_from']=[11]
for i in (9,10,13):by_id[i]['damage_from']=[]
# Foreground plasma and grenade volleys, without drowning out the punchline.
battle=[dict(at=2.36,kind='near_miss',actor=2,target=0,offset=[0,0,24]),dict(at=4.30,kind='engine',volume=1.5)]
for i,target in [(9,7),(10,4),(12,3)]:
 for k in range(160):
  t=.18+(i%5)*.085+k*.148
  if t<23 and not(i==12 and t>13):battle.append(dict(at=round(t,3),kind='plasma',actor=i,target=target,offset=[25 if k%3 else -25,0,70 if t<14 else 45]))
for k in range(24):
 t=6.05+k*.69;i=12 if k%2==0 and t<13 else 10
 point=[-30+(k%4)*65,80+(k%3)*65,-235]
 battle.append(dict(at=round(t,3),kind='grenade',actor=i,point=point,flight=1.1+(k%3)*.08,fuse=1.8))
battle.append(dict(at=9.52,kind='rocket',actor=13,point=[-20,480,-222],flight=.55,fuse=3))
overview=dict(eye=[-430,-30,150],focus=[170,550,-95],fov=73)
cuts=[dict(at=0,**overview),dict(at=8.6,eye=[-210,-260,100],focus=[0,0,35],fov=68,follow_actor=13),dict(at=9.98,**overview)]
# RPG attack drives the native firing animation/muzzle event. IW4L's current
# native missile owns flight and damage; the scene cue adds CE audio only.
by_id[13]['buttons']=[[8.6,9.17,SPRINT],[8.88,9.02,JUMP],[9.25,9.8,ADS],[9.50,9.72,ATTACK]]
for cue in battle:
 if cue['kind']=='rocket':cue['at']=9.50;cue['kind']='native_rocket'
cuts[-1]['at']=10.08
# Fresh combatants enter from the edges after their prior life has died. No
# living actors are repositioned at the cut or at reinforcement cues.
reinforcements=[]
for who,at,entry,goal,target in [
 (1,6.15,[-430,790,-236],[-90,670,-236],10),
 (2,6.65,[1480,360,-240],[1280,240,-240],9),
 (3,13.0,[-450,830,-235],[-100,610,-236],10),
 (4,13.5,[1500,420,-240],[1250,330,-240],8),
 (5,14.0,[-430,570,-235],[-120,390,-236],13)]:
 a=by_id[who]
 a['route']=[r for r in a['route'] if r[0]<at-.1]+[[at,*entry],[at+1.4,*goal]]
 for k in range(1,9):
  t=at+1.4+k*1.0
  if t<24:a['route'].append([t,goal[0]+(-1 if k%2 else 1)*75,goal[1]+(-1 if (k//2)%2 else 1)*65,goal[2]])
 a['route'].append([24,*goal])
 a['aim']=[c for c in a['aim'] if c['start']<at]
 a['aim'].append(aim(at,24,target,height=42,offset_x=24,offset_z=3))
 # Re-entry body remains available for visible crossfire through the final shot.
 if who in (1,2):a['damage_from']=[0]
 reinforcements += [dict(at=at,respawn_actor=who,origin=entry,yaw=30 if who in(1,3,5) else 180),dict(at=at+.15,command=f'bot give {who} cheytac_mp &')]
# Paired combat targets. Keep muzzles trained near opponents, not far overhead.
for who,target in [(3,11),(4,12),(5,14),(6,15),(7,9),(8,7),(9,2),(10,1),(11,3),(12,4),(14,5),(15,6)]:
 a=by_id[who]
 if who in (8,9,10):stop=24
 elif who in (11,12,14,15):stop=14
 else:stop=12.5 if who in(3,4,5) else 14.5
 begin=5.55
 a['aim']=[c for c in a['aim'] if c['start']<begin or c['start']>=stop]
 for c in a['aim']:
  if c['start']<begin:c['end']=min(c['end'],begin)
 a['aim'].append(aim(begin,stop,target,height=42,offset_x=24 if who%2 else -26,offset_z=3))
by_id[7]['damage_from']=[]
# Quick attacking bursts occupy most of the take instead of slow waypoint walks.
for a in actors:
 who=a['id']
 if who in (0,13):continue
 start=5.55 if who not in(1,2) else (6.35 if who==1 else 6.85)
 stop=14.0 if who in(11,12,14,15) else (14.4 if who==6 else 23.7)
 a['buttons']=[b for b in a['buttons'] if b[0]<start or b[0]>=stop]
 for k in range(13):
  t=start+(who%4)*.12+k*1.45
  if t+.95>=stop:break
  a['buttons'] += [[t,t+.74,SPRINT],[t+.7,t+1.03,ADS],[t+.86,t+.98,ATTACK],[t+1.04,min(t+1.4,stop),SPRINT]]
  if k%2==0:a['buttons'].append([t+.52,t+.65,JUMP])
  elif k%3==1:a['buttons'].append([t+.73,t+.87,512])
# Plasma sources strafe and hop in clear ground; their volleys already run at 5x.
for who,x,y in [(10,-90,660),(12,-60,390)]:
 a=by_id[who];tail=[r for r in a['route'] if r[0]>=14.5] if who==12 else []
 a['route']=[r for r in a['route'] if r[0]<5.5]+[[t,x+(-1 if k%2 else 1)*65,y+(-1 if (k//2)%2 else 1)*55,-236] for k,t in enumerate([5.5,6.7,7.9,9.1,10.3,11.5,12.7])]+tail
 if who==10:a['route'] += [[14,-20,650,-236],[16,-155,620,-236],[18,-15,740,-236],[20,-170,690,-236],[22,-45,580,-236],[24,-110,660,-236]]
by_id[8]['route']=[[0,1360,560,-242],[5.55,1360,560,-242],[7,1310,430,-242],[9,1200,310,-242],[11,1040,160,-236],[13,830,160,-236],[15,710,200,-236],[17,550,220,-236],[19,370,250,-236],[21,230,370,-236],[24,390,420,-236]]
# Continue exchanging shots with the returned soldiers after the rocket triple.
by_id[13]['aim'].append(aim(11.2,24,5,height=42,offset_x=25))
by_id[13]['buttons'] += [[t,t+.18,ADS] for t in [12.,14.,16.,18.,20.,22.]]+[[t+.13,t+.23,ATTACK] for t in [12.,14.,16.,18.,20.,22.]]
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify',action='store_true');args=p.parse_args()
scene=dict(version=2,title='Rust: wrong franchise — Warthog delivery',duration=24,health=30,actors=sorted(actors,key=lambda a:a['id']),battle=sorted(battle,key=lambda e:e['at']),vehicle=vehicle,cut_delay=.22,camera_cuts=cuts,
 events=sorted(reinforcements+[dict(at=t,command='screenshot battlefield-v7-'+str(t).replace('.','-')) for t in ([1.45,3.06,4.05,4.5,5.23,5.7,6.6,8.7,9.15,9.6,10.3,11.2,14.,17.5,22] if args.verify else [])],key=lambda e:e['at']))
from stage_foreground_duel import stage
scene=stage(scene)
scene['map']='mp_rust'
for actor in scene['actors']:
 actor['buttons']=[cue for cue in actor['buttons'] if cue[0]<cue[1]]
if args.verify:
 scene['ground_probes']=[[x,y] for x in [300,500,700,900,1100] for y in [800,1000,1200,1400]]
 scene['sightline_probes']=[[[513,600,98],[x,y,-190]] for x in [-150,-50,50,1100,1250,1400,1550] for y in [400,500,600,700,800,950]]
out=ROOT/'local-assets/scenes/worlds-collide-native.json';tmp=out.with_suffix('.tmp');tmp.write_text(json.dumps(scene,indent=2)+'\n');tmp.replace(out);print(out)
