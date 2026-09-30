#!/usr/bin/env python3
"""Package the extracted CE sniper for the opt-in native WA2000 visual slot."""
import json,struct
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'local-assets/halo/native';OUT.mkdir(exist_ok=True)
b=(ROOT/'web/assets/sniper.glb').read_bytes();jl=struct.unpack_from('<I',b,12)[0];g=json.loads(b[20:20+jl]);data=b[28+jl:]
def acc(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];dt={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']]
 return np.frombuffer(data,dt,count=a['count']*size,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],size).copy()
a=g['meshes'][0]['primitives'][0]['attributes'];p=acc(a['POSITION'])/.0254*.84;n=acc(a['NORMAL']);uv=acc(a['TEXCOORD_0'])
r={'template':'weapon_wa2000','positions':[],'normals':[],'uvs':[],'joints':[],'weights':[],'indices':[],'ranges':[],'materials':[]};packed=bytearray()
def unit(v):return bytes([int(np.clip(round(float(x)*127+127),0,255)) for x in v]+[63])
for k,prim in enumerate(g['meshes'][0]['primitives']):
 idx=acc(prim['indices']).ravel();used=sorted(set(int(v) for v in idx));base=len(r['positions']);remap={v:i+base for i,v in enumerate(used)};start=len(r['indices'])
 for i in used:
  r['positions'].append(p[i].tolist());r['normals'].append(n[i].tolist());r['uvs'].append(uv[i].tolist());r['joints'].append([0,0,0,0]);r['weights'].append([1,0,0,0])
  tangent=np.cross([0,0,1],n[i]);tangent/=max(np.linalg.norm(tangent),1e-6)
  packed+=struct.pack('<3ff4B',*p[i],1,255,255,255,255)+struct.pack('<ee',float(uv[i,1]),float(uv[i,0]))+unit(n[i])+unit(tangent)
 for tri in idx.reshape(-1,3):r['indices'] += [remap[int(tri[0])],remap[int(tri[2])],remap[int(tri[1])]]
 r['ranges'].append([base,len(used),start,len(idx)])
 m=g['materials'][prim['material']];tex=m['pbrMetallicRoughness'].get('baseColorTexture')
 if tex:
  im=g['images'][g['textures'][tex['index']]['source']];v=g['bufferViews'][im['bufferView']];image=Image.open(BytesIO(data[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGBA')
 else:image=Image.new('RGBA',(4,4),(50,55,60,255))
 image.putalpha(255);name=f'sniper-material-{k}.rgba';(OUT/name).write_bytes(image.tobytes());r['materials'].append({'name':'halo_ce_sniper_'+m['name'],'file':name,'width':image.width,'height':image.height})
(OUT/'sniper-vertices.bin').write_bytes(packed);(OUT/'sniper.json').write_text(json.dumps(r,separators=(',',':')));print('Native CE sniper:',len(r['positions']),'vertices')
