#!/usr/bin/env python3
"""Import the optional IW4L cinema-source export into the local viewer."""
import json,sys,shutil
from pathlib import Path
from io import BytesIO
import numpy as np
from PIL import Image
from export_halo import Glb

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'vendor-src/iw4L/iw4l-artifacts/cinema-sources'
OUTPUT=ROOT/'web/assets/cinema'
OUTPUT.mkdir(exist_ok=True)
catalog=json.loads((SOURCE/'catalog.json').read_text())
models={m['name']:m for m in catalog['models']}
materials={m['name']:m for m in catalog['materials']}
images={i['index']:i for i in catalog['images']}

def matrix(b):
 x,y,z,w=b['rotation'];n=np.linalg.norm([x,y,z,w]);x,y,z,w=np.array([x,y,z,w])/n if n else [0,0,0,1]
 M=np.eye(4);M[:3,:3]=[[1-2*(y*y+z*z),2*(x*y-z*w),2*(x*z+y*w)],[2*(x*y+z*w),1-2*(x*x+z*z),2*(y*z-x*w)],[2*(x*z-y*w),2*(y*z+x*w),1-2*(x*x+y*y)]]
 M[:3,3]=np.array(b['translation'])*.0254
 return M

def material(g,name):
 m=materials[name];out={'name':name,'doubleSided':True,'pbrMetallicRoughness':{'metallicFactor':.12,'roughnessFactor':.7}}
 binding=next((t for t in m['textures'] if t['semantic']==2),None)
 if binding and binding['image'] in images:
  im=Image.open(SOURCE/images[binding['image']]['paths'][0]).convert('RGBA');im.putalpha(255)
  b=BytesIO();im.save(b,format='PNG');out['pbrMetallicRoughness']['baseColorTexture']={'index':g.image(b.getvalue())}
 index=len(g.doc['materials']);g.doc['materials'].append(out);return index

def convert(name,filename,head=None):
 model=models[name];g=Glb();world=[matrix(b) for b in model['bones']]
 positions=np.array(model['positions'])*.0254;normals=np.array(model['normals']);uv=model['uvs'];joints=model['joints'];weights=model['weights']
 surfaces=[]
 for i in range(*model['lod0']):
  start,count=model['surfaces'][i];mat=model['materials'][i]
  if name=='weapon_cheytac' and any(s in mat for s in ['acog','laser','suppressor','heartbeat','reflex']):continue
  surfaces.append((mat,model['indices'][start:start+count]))
 if head:
  h=models[head];bone_names=[b['name'] for b in model['bones']];attach=world[bone_names.index('j_spine4')];offset=len(positions)
  hp=np.array(h['positions'])*.0254;hp=(np.c_[hp,np.ones(len(hp))]@attach.T)[:,:3]
  positions=np.r_[positions,hp];normals=np.r_[normals,np.array(h['normals'])@attach[:3,:3].T];uv+=h['uvs']
  remap=[bone_names.index(b['name']) if b['name'] in bone_names else bone_names.index('j_head') for b in h['bones']]
  joints += [[remap[b] for b in row] for row in h['joints']];weights+=h['weights']
  for i in range(*h['lod0']):
   start,count=h['surfaces'][i];surfaces.append((h['materials'][i],[idx+offset for idx in h['indices'][start:start+count]]))
 attributes={'POSITION':g.accessor(positions,'VEC3',bounds=True),'NORMAL':g.accessor(normals,'VEC3'),'TEXCOORD_0':g.accessor(uv,'VEC2'),'JOINTS_0':g.accessor(joints,'VEC4',5123),'WEIGHTS_0':g.accessor(weights,'VEC4')}
 primitives=[{'attributes':attributes,'indices':g.accessor(idx,'SCALAR',5125),'material':material(g,mat)} for mat,idx in surfaces]
 g.doc['meshes']=[{'name':filename,'primitives':primitives}]
 for i,b in enumerate(model['bones']):
  parent=b['parent'];local=np.linalg.inv(world[parent])@world[i] if parent is not None else world[i]
  node={'name':b['name'],'matrix':local.T.reshape(16).tolist()};children=[j for j,b in enumerate(model['bones']) if b['parent']==i]
  if children:node['children']=children
  g.doc['nodes'].append(node)
 g.doc['skins']=[{'joints':list(range(len(world))),'inverseBindMatrices':g.accessor([np.linalg.inv(M).T.reshape(16) for M in world],'MAT4')}]
 mesh=len(world);g.doc['nodes'].append({'name':filename,'mesh':0,'skin':0});root=len(g.doc['nodes'])
 g.doc['nodes'].append({'name':'IW_basis','matrix':[0,0,-1,0,-1,0,0,0,0,1,0,0,0,0,0,1],'children':[mesh]+[i for i,b in enumerate(model['bones']) if b['parent'] is None]})
 g.doc['scenes']=[{'nodes':[root]}];g.doc['scene']=0;g.save(OUTPUT/(filename+'.glb'));print(filename,len(positions),'vertices')

convert('mp_body_desert_tf141_assault_a','soldier','head_tf141_desert_a')
convert('weapon_cheytac','intervention')
# Rust's actual sky texture, resolved from the map's material catalog.
sky=next(m for m in catalog['materials'] if m['name']=='wc/sky_af_chase')
source=images[sky['textures'][0]['image']]
for i,path in enumerate(source['paths']):shutil.copy2(SOURCE/path,OUTPUT/f'sky-{i}.png')
# Retain technique hints for alpha-cutout materials which P1a exports as opaque.
world=ROOT/'web/assets/rust-cokzoejc/scene.gltf';doc=json.loads(world.read_text())
for m in doc['materials']:
 source=materials.get(m['name'],{});tech=source.get('technique','')
 if 'alphatest' in tech or 'alpha_test' in tech or 'foliage' in m['name']:
  m['alphaMode']='MASK';m['alphaCutoff']=.45;m['doubleSided']=True
world.write_text(json.dumps(doc,separators=(',',':')))
configpath=ROOT/'web/config.json';config=json.loads(configpath.read_text())
config['soldier']={'url':'assets/cinema/soldier.glb','rotation':[0,0,0]}
config['models']['intervention']={'url':'assets/cinema/intervention.glb','length':1.45,'rotation':[0,0,0]}
config['sky']=[f'assets/cinema/sky-{i}.png' for i in range(6)]
configpath.write_text(json.dumps(config,indent=2)+'\n')
