#!/usr/bin/env python3
"""Retarget the locally extracted CE mesh onto the native MW2 soldier bind rig."""
import json,struct,sys
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'local-assets/halo/native';OUT.mkdir(exist_ok=True)
blob=(ROOT/'web/assets/chief.glb').read_bytes();jl=struct.unpack_from('<I',blob,12)[0];g=json.loads(blob[20:20+jl]);data=blob[28+jl:]
def acc(i):
 a=g['accessors'][i];v=g['bufferViews'][a['bufferView']];size={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4,'MAT4':16}[a['type']];dt={5126:'<f4',5123:'<u2',5125:'<u4'}[a['componentType']]
 return np.frombuffer(data,dt,count=a['count']*size,offset=v.get('byteOffset',0)+a.get('byteOffset',0)).reshape(a['count'],size).copy()
def mat(q,t):
 x,y,z,w=np.array(q)/np.linalg.norm(q);M=np.eye(4);M[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]];M[:3,3]=t;return M
c=json.loads((ROOT/'vendor-src/iw4L/iw4l-artifacts/cinema-sources/catalog.json').read_text())
template=next(m for m in c['models'] if m['name']=='mp_body_desert_tf141_assault_a')
mapnames=['pelvis','j_hip_le','j_hip_ri','j_spinelower','j_knee_le','j_knee_ri','j_spineupper','j_clavicle_le','j_ankle_le','j_neck','j_clavicle_ri','j_ankle_ri','j_head','j_shoulder_le','j_shoulder_ri','j_elbow_le','j_elbow_ri','j_wrist_le','j_wrist_ri']
names=[b['name'] for b in template['bones']];mapping=[names.index(n) for n in mapnames]
oldinv=acc(g['skins'][0]['inverseBindMatrices']).reshape(-1,4,4).transpose(0,2,1)
# Bone coordinate frames differ between engines, especially mirrored limbs.
# Fit the anatomical segment directions in world space rather than equating
# local axes (which turns CE's right thigh and upper arm upside down).
source_bind=np.linalg.inv(oldinv)
source_points=source_bind[:,:3,3]
target_points=np.array([template['bones'][b]['translation'] for b in mapping])*.0254
segments={0:3,1:4,2:5,3:6,4:8,5:11,6:9,7:13,9:12,10:14,13:15,14:16,15:17,16:18}
def align(a,b):
 a=a/np.linalg.norm(a);b=b/np.linalg.norm(b)
 v=np.cross(a,b);c=float(np.dot(a,b));s=float(np.linalg.norm(v))
 if s<1e-7:
  if c>0:return np.eye(3)
  axis=np.cross(a,[1,0,0] if abs(a[0])<.9 else [0,1,0]);axis/=np.linalg.norm(axis)
  return 2*np.outer(axis,axis)-np.eye(3)
 k=np.array([[0,-v[2],v[1]],[v[2],0,-v[0]],[-v[1],v[0],0]])
 return np.eye(3)+k+k@k*((1-c)/(s*s))
transforms=[]
for i in range(len(mapping)):
 rotation=align(source_points[segments[i]]-source_points[i],target_points[segments[i]]-target_points[i]) if i in segments else np.eye(3)
 m=np.eye(4);m[:3,:3]=rotation*.88;m[:3,3]=target_points[i]-m[:3,:3]@source_points[i];transforms.append(m)
attributes=g['meshes'][0]['primitives'][0]['attributes'];p=acc(attributes['POSITION']);n=acc(attributes['NORMAL']);uv=acc(attributes['TEXCOORD_0']);j=acc(attributes['JOINTS_0']);w=acc(attributes['WEIGHTS_0']);posed=np.zeros_like(p);normal=np.zeros_like(n)
for i in range(len(p)):
 for b,weight in zip(j[i],w[i]):
  if weight:
   posed[i]+=(transforms[b]@np.r_[p[i],1])[:3]*weight
   normal[i]+=(transforms[b][:3,:3]@n[i])*weight
normal/=np.maximum(np.linalg.norm(normal,axis=1)[:,None],1e-8);posed/=.0254
result={'template':template['name'],'positions':[],'normals':[],'uvs':[],'joints':[],'weights':[],'indices':[],'ranges':[],'materials':[]};packed=bytearray()
def unit(v):return bytes([int(np.clip(round(float(x)*127+127),0,255)) for x in v]+[63])
for number,primitive in enumerate(g['meshes'][0]['primitives']):
 idx=acc(primitive['indices']).ravel();used=sorted(set(int(v) for v in idx));remap={v:i+len(result['positions']) for i,v in enumerate(used)};start=len(result['indices']);base=len(result['positions'])
 for i in used:
  result['positions'].append(posed[i].tolist());result['normals'].append(normal[i].tolist());result['uvs'].append(uv[i].tolist());result['joints'].append([mapping[b] for b in j[i]]);result['weights'].append(w[i].tolist())
  tangent=np.cross([0,0,1],normal[i]);tangent/=max(np.linalg.norm(tangent),1e-6)
  packed+=struct.pack('<3ff4BH',*posed[i],1,255,255,255,255,struct.unpack('<H',struct.pack('<e',float(uv[i,1])))[0])+struct.pack('<e',float(uv[i,0]))+unit(normal[i])+unit(tangent)
 # Native IW uses clockwise triangles, the reverse of the Halo glTF surface.
 for tri in idx.reshape(-1,3):result['indices'] += [remap[int(tri[0])],remap[int(tri[2])],remap[int(tri[1])]]
 result['ranges'].append([base,len(used),start,len(idx)])
 material=g['materials'][primitive['material']];pbr=material['pbrMetallicRoughness'];tex=pbr.get('baseColorTexture')
 if tex:
  im=g['images'][g['textures'][tex['index']]['source']];v=g['bufferViews'][im['bufferView']];image=Image.open(BytesIO(data[v['byteOffset']:v['byteOffset']+v['byteLength']])).convert('RGBA')
 else:image=Image.new('RGBA',(4,4),tuple(int(v*255) for v in pbr.get('baseColorFactor',[.3,.5,.2,1])))
 image.putalpha(255);filename=f'material-{number}.rgba';(OUT/filename).write_bytes(image.tobytes());result['materials'].append({'name':'halo_ce_'+material['name'],'file':filename,'width':image.width,'height':image.height})
(OUT/'vertices.bin').write_bytes(packed);(OUT/'chief.json').write_text(json.dumps(result,separators=(',',':')))
print('Native Chief pack:',len(result['positions']),'vertices',len(result['indices'])//3,'triangles',len(result['materials']),'materials')
