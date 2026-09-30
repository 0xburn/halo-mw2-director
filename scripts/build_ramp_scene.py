#!/usr/bin/env python3
"""Native controller choreography, in IW inches/Z-up. No frame teleports or forced kills."""
import argparse
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'local-assets/scenes/worlds-collide-native.json'
ATTACK,SPRINT,CROUCH,JUMP,ADS,BREATH=1,2,512,1024,2048,8192

def actor(i,name,route,aim=(),buttons=(),yaw=90):
 return dict(id=i,name=name,weapon='wa2000_mp' if i>=8 else 'cheytac_mp',yaw=yaw,route=route,aim=list(aim),buttons=list(buttons))
def aim(start,end,id,**kw):return dict(start=start,end=end,actor=id,**kw)
actors=[actor(0,'xX RampGod Xx',[
 [0,470,40,-210],[.6,480,100,-220],[1.2,510,160,-215],[1.8,513,218,-206],
 [3.0,513,280,-160],[4.0,513,390,-82],[5.5,513,490,-30],[6.5,513,540,0],
 [8.6,513,680,92],[24,513,680,92]],
 [aim(2.05,2.98,1,height=34),aim(5.02,6.05,2),aim(8.45,24,8,height=50)],
 [[0,1.0,SPRINT],[.8,.91,JUMP],[2.35,2.82,ADS|BREATH],[2.65,2.75,ATTACK],
  [3.1,3.23,CROUCH],[5.38,5.88,ADS|BREATH],[5.68,5.78,ATTACK],
  [8.75,10.8,ADS|BREATH]]),
 actor(1,'iTz Scopez',[ [0,840,250,-242],[.55,775,260,-242],[1.15,860,300,-242],[1.85,770,290,-242],[2.2,795,292,-242],[2.8,845,330,-242],[3.1,850,310,-242],[24,850,310,-242]],
 [aim(0,1.55,0),aim(1.55,2.15,0,offset_z=140),aim(2.15,24,0)],[[.5,.62,JUMP],[1.75,2.1,ADS],[1.95,2.04,ATTACK],[2.25,2.4,CROUCH]],yaw=180),
 actor(2,'FaZe-ish',[ [0,513,710,114],[1,513,710,114],[3,513,650,70],[4,513,690,102],[5,513,645,65],[5.7,513,685,94],[24,513,700,104]],
 [aim(0,4.1,0),aim(4.1,4.85,0,offset_z=140),aim(4.85,24,0)],[[3.5,3.61,JUMP],[4.4,4.7,ADS],[4.6,4.69,ATTACK],[5.0,5.15,CROUCH]],yaw=-90),
 actor(8,'Master Chief',[[0,1360,560,-210],[24,1360,560,-210]],
 [aim(0,24,0,height=48)],[[10.35,10.5,ATTACK]],yaw=180)]
# The wider battlefield remains in the reveal. These players use the same native controller.
for i in list(range(3,8))+list(range(9,16)):
 side=0 if i<8 else 1;k=(i-3 if i<8 else i-9)
 x=80+side*1080;y=850+k*105
 route=[[0,x,y,-229],[11,x,y,-229],[13,x+80,y+65,-229],[15,x-40,y,-229],[18,x+100,y+90,-229],[21,x,y,-229],[24,x+50,y+40,-229]]
 target=9+(k%7) if i<8 else 3+(k%5)
 actors.append(actor(i,('MW2 ' if i<8 else 'Spartan ')+str(k+1),route,[aim(11,24,target)],[[12+k*.17,12.8+k*.17,ADS],[12.55+k*.17,12.64+k*.17,ATTACK],[16+k*.17,16.8+k*.17,ADS],[16.55+k*.17,16.64+k*.17,ATTACK],[11.3+k*.15,11.41+k*.15,JUMP]],yaw=0 if i<8 else 180))
# Compress the opening; travel inputs are full native sprint, not slow analog walk.
for a in actors:
 if a['id'] in (0,1,2,8):
  for r in a['route']: r[0]*=.72
  for cue in a['aim']: cue['start']*=.72;cue['end']*=.72
  for b in a['buttons']: b[0]*=.72;b[1]*=.72
player=next(a for a in actors if a['id']==0)
player['buttons']=[[0,.95,SPRINT],[1.52,2.14,ADS|BREATH],[1.96,2.08,ATTACK],
 [2.3,3.16,SPRINT],[3.68,4.3,ADS|BREATH],[4.10,4.22,ATTACK],[4.46,5.05,SPRINT],[6.3,7.8,ADS|BREATH]]
player['route']=[[0,470,40,-210],[.55,508,170,-220],[1.0,513,245,-185],[1.95,513,292,-155],
 [2.3,513,310,-145],[3.2,513,520,-23],[4.25,513,545,-8],[5.2,513,695,105],[24,513,695,105]]
player['aim']=[aim(1.48,2.18,1,height=40),aim(3.59,4.34,2,height=42),aim(6.05,24,8,height=55)]
first=next(a for a in actors if a['id']==1)
# Lateral to the player's sightline: visible zigzags, not radial shuffling.
first['route']=[[0,815,190,-242],[.55,825,290,-242],[1.05,807,220,-242],
 [1.5,820,325,-242],[2.15,820,345,-242],[2.65,805,240,-242],[3.2,830,345,-242],[24,830,345,-242]]
first['buttons']=[[.48,.6,JUMP],[1.13,1.5,ADS],[1.40,1.49,ATTACK]]
second=next(a for a in actors if a['id']==2)
second['route']=[[0,513,710,110],[.6,505,665,81],[1.15,521,730,114],
 [1.9,505,640,64],[2.6,521,715,110],[3.2,505,645,67],[3.85,520,700,104],[4.5,512,735,114],[24,512,735,114]]
second['buttons']=[[1.0,1.13,JUMP],[2.99,3.42,ADS],[3.32,3.4,ATTACK],[3.42,3.56,JUMP]]
# Scope pulls cancel a still-held sprint; shots flow straight into the next dash.
landmarks=[(0.,0.),(1.52,.85),(1.96,1.30),(2.06,1.36),(3.68,2.50),(4.10,2.93),(4.34,3.00),(6.3,3.65),(7.45,4.30),(24.,24.)]
def retime(t):
 for (x,y),(xx,yy) in zip(landmarks,landmarks[1:]):
  if t<=xx:return y+(t-x)/(xx-x)*(yy-y)
 return t
for a in actors:
 if a['id'] in (0,1,2,8):
  for r in a['route']:r[0]=retime(r[0])
  for cue in a['aim']:cue['start']=retime(cue['start']);cue['end']=retime(cue['end'])
  for b in a['buttons']:b[0]=retime(b[0]);b[1]=retime(b[1])
 else:
  for r in a['route']:
   if r[0]>=11:r[0]=6+(r[0]-11)*18/13
  for cue in a['aim']:
   cue['start']=6+(cue['start']-11)*18/13;cue['end']=24
  for b in a['buttons']:
   b[0]=6+(b[0]-11)*18/13;b[1]=6+(b[1]-11)*18/13
player['buttons']=[[0,1.03,SPRINT],[1.00,1.37,ADS|BREATH],[1.30,1.36,ATTACK],
 [1.37,2.67,SPRINT],[2.64,3.00,ADS|BREATH],[2.93,2.99,ATTACK],
 [3.00,3.70,SPRINT],[3.65,5.05,ADS|BREATH]]
player['aim']=[aim(.92,1.37,1,height=40,turn_speed=580,response=27),aim(2.46,3.0,2,height=42),aim(3.59,24,8,height=55)]
chief=next(a for a in actors if a['id']==8)
chief['buttons']=[[4.80,4.92,ATTACK]]
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--verify',action='store_true',help='Capture checkpoints (may add frame-time overhead).')
args=parser.parse_args()
scene=dict(version=2,title='Rust: wrong franchise',duration=24,health=30,actors=sorted(actors,key=lambda a:a['id']),events=[dict(at=t,command='screenshot ramp-v8-'+str(t).replace('.','-')) for t in ([1.42,3.05,4.6,6.5] if args.verify else [])])
if OUT.exists():
 old=json.loads(OUT.read_text())
 if old.get('version')==1:(OUT.parent/'worlds-collide-native-v1.json').write_text(json.dumps(old))
temporary=OUT.with_suffix('.tmp')
temporary.write_text(json.dumps(scene,indent=2)+'\n')
temporary.replace(OUT)
print(OUT)
