#!/usr/bin/env python3
"""Extract the local CE vehicle, weapons and audio, then package native meshes."""
import json,struct,shutil,wave
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
from export_halo import Converter,MODELS,transform
from reclaimer.animation.animation_decompilation import extract_animation
from reclaimer.sounds.sound_decompilation import extract_h1_sounds
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'local-assets/halo/native';SRC=ROOT/'local-assets/halo/expanded'
MODELS.update(warthog=r'vehicles\warthog\warthog',plasma_pistol=r'weapons\plasma pistol\plasma pistol',plasma_grenade=r'weapons\plasma grenade\plasma grenade',rocket_projectile=r'weapons\rocket launcher\projectile\projectile')
c=Converter(ROOT/'local-assets/halo/maps/bloodgulch.map',SRC,'blue')
for k in ['warthog','plasma_pistol','plasma_grenade','rocket_projectile','rocket']:
 if not (SRC/(k+'.glb')).exists():c.convert(k)
class Model:
 def __init__(self,p):
  b=p.read_bytes();jl=struct.unpack_from('<I',b,12)[0];self.g=json.loads(b[20:20+jl]);self.data=b[28+jl:]
 def acc(self,i):
  a=self.g['accessors'][i];v=self.g['bufferViews'][a['bufferView']];size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']]
  return np.frombuffer(self.data,{5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']],count=a['count']*size,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],size).copy()
 def image(self,m):
  pbr=m['pbrMetallicRoughness'];tex=pbr.get('baseColorTexture')
  if tex:
   v=self.g['bufferViews'][self.g['images'][self.g['textures'][tex['index']]['source']]['bufferView']]
   im=Image.open(BytesIO(self.data[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGBA')
  else:im=Image.new('RGBA',(4,4),tuple(int(v*255) for v in pbr.get('baseColorFactor',[.3,.4,.3,1])))
  im.putalpha(255);return im

def pack(name,parts,template='weapon_wa2000'):
 r=dict(template=template,positions=[],normals=[],uvs=[],joints=[],weights=[],indices=[],ranges=[],materials=[]);raw=bytearray()
 for model,posed,normal in parts:
  a=model.g['meshes'][0]['primitives'][0]['attributes'];p=model.acc(a['POSITION']) if posed is None else posed;n=model.acc(a['NORMAL']) if normal is None else normal;uv=model.acc(a['TEXCOORD_0'])
  for prim in model.g['meshes'][0]['primitives']:
   idx=model.acc(prim['indices']).ravel();used=sorted(set(map(int,idx)));base=len(r['positions']);start=len(r['indices']);remap={v:i+base for i,v in enumerate(used)}
   for i in used:
    q=p[i]/.0254*.84;nn=n[i]/max(np.linalg.norm(n[i]),1e-7);t=np.cross([0,0,1],nn);t/=max(np.linalg.norm(t),1e-7)
    unit=lambda v:bytes([int(np.clip(round(float(x)*127+127),0,255)) for x in v]+[63])
    r['positions'].append(q.tolist());r['normals'].append(nn.tolist());r['uvs'].append(uv[i].tolist());r['joints'].append([0]*4);r['weights'].append([1,0,0,0])
    raw+=struct.pack('<3ff4B',*q,1,255,255,255,255)+struct.pack('<ee',float(uv[i,1]),float(uv[i,0]))+unit(nn)+unit(t)
   for tri in idx.reshape(-1,3):r['indices'] += [remap[int(tri[0])],remap[int(tri[2])],remap[int(tri[1])]]
   r['ranges'].append([base,len(used),start,len(idx)])
   m=model.g['materials'][prim['material']];im=model.image(m);k=len(r['materials']);fn=f'{name}-material-{k}.rgba';(OUT/fn).write_bytes(im.tobytes());r['materials'].append(dict(name='halo_ce_'+name+'_'+str(k),file=fn,width=im.width,height=im.height))
 (OUT/(name+'.json')).write_text(json.dumps(r,separators=(',',':')));(OUT/(name+'-vertices.bin')).write_bytes(raw)
 print(name,len(r['positions']),'vertices',len(r['indices'])//3,'triangles')

# Pose Chief using the actual CE Warthog-driver animation, attached to its seat marker.
hog=Model(SRC/'warthog.glb');chief=Model(ROOT/'web/assets/chief.glb')
m=c.meta(c.find(MODELS['chief'],{'model_animations'}),True)
i=next(i for i,a in enumerate(m.animations.STEPTREE) if a.name=='W-driver unarmed idle')
a=extract_animation(i,m,write_jma=False);a.apply_root_node_info_to_states(undo=True)
parents={child:i for i,node in enumerate(chief.g["nodes"][:len(a.nodes)]) for child in node.get("children",[]) if child<len(a.nodes)}
world={}
def bone_world(i):
 if i not in world:
  local=transform(a.frames[0][i])[2];parent=parents.get(i,-1)
  world[i]=bone_world(parent)@local if parent>=0 else local
 return world[i]
for i in range(len(a.nodes)):bone_world(i)
inv=chief.acc(chief.g['skins'][0]['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
attrs=chief.g['meshes'][0]['primitives'][0]['attributes'];p=chief.acc(attrs['POSITION']);n=chief.acc(attrs['NORMAL']);j=chief.acc(attrs['JOINTS_0']);w=chief.acc(attrs['WEIGHTS_0']);posed=np.zeros_like(p);normal=np.zeros_like(n)
seat=np.array([-.0725257,.5052117,1.28016-.089153])
for i in range(len(p)):
 for bone,weight in zip(j[i],w[i]):
  if weight:
   xf=world[bone]@inv[bone];posed[i]+=(xf@np.r_[p[i],1])[:3]*weight;normal[i]+=(xf[:3,:3]@n[i])*weight
posed+=seat
pack('warthog',[(hog,None,None),(chief,posed,normal)])
for k,template in [('plasma_pistol','weapon_usp'),('rocket','weapon_rpg7'),('plasma_grenade','weapon_wa2000'),('rocket_projectile','weapon_wa2000')]:pack(k,[(Model(SRC/(k+'.glb')),None,None)],template)
for index,name in [(207,'halo-splat'),(236,'chief-death'),(731,'halo-vehicle-impact'),(1647,'triple-kill'),(652,'warthog-engine'),(709,'warthog-impact'),(1169,'rocket-fire'),(1274,'plasma-explosion'),(911,'plasma-fire'),(1405,'plasma-fuse')]:
 d=ROOT/'local-assets/halo/audio'/name
 extract_h1_sounds(c.meta(index,True),name,out_dir=d.parent,decode_adpcm=True)
 wav=d/'death_violent_1.wav' if name=='chief-death' else sorted(d.rglob('*.wav'))[0]
 # Reclaimer emits a 20-byte PCM fmt chunk and undersized RIFF length. Normalize
 # the container only; retain all original decoded samples and the sample rate.
 with wave.open(str(wav),'rb') as src: params=src.getparams(); samples=src.readframes(params.nframes)
 with wave.open(str(OUT/(name+'.wav')),'wb') as dst: dst.setparams(params); dst.writeframes(samples)
 print(name,wav.name)

from mix_native_impact import mix_impact
mix_impact(OUT)
