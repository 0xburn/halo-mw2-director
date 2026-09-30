import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { Octree } from 'three/addons/math/Octree.js';
import { Capsule } from 'three/addons/math/Capsule.js';
import { clone as cloneSkeleton } from 'three/addons/utils/SkeletonUtils.js';
import { BurstWeapon } from './weapon.js';
import { trainingYard, armorProxy, weaponProxy, box } from './proxies.js';

import { CinematicHud } from './cinematic-hud.js';
import { SceneDirector } from './director.js';
import { WEAPONS } from './scene-script.js';

const $ = id => document.getElementById(id);
const canvas = $('game');
const scene = new THREE.Scene();
scene.background = new THREE.Color(0xb7b6a1);
scene.fog = new THREE.Fog(0xb7b6a1, 35, 135);
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
renderer.setSize(innerWidth, innerHeight);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;
renderer.autoClear = false;
const camera = new THREE.PerspectiveCamera(78, innerWidth / innerHeight, 0.05, 1000);
camera.rotation.order = 'YXZ';
const viewScene = new THREE.Scene();
const viewCamera = new THREE.PerspectiveCamera(65, camera.aspect, 0.01, 10);
viewScene.add(new THREE.HemisphereLight(0xe9f4ef, 0x776c4f, 2.4));
const viewLight = new THREE.DirectionalLight(0xffedc9, 2);
viewLight.position.set(-1, 3, 2);
viewScene.add(viewLight);
scene.add(new THREE.HemisphereLight(0xcbd5dd, 0x635039, 1.25));
const sun = new THREE.DirectionalLight(0xffedca, 3);
sun.position.set(-20, 35, 14); sun.castShadow = true;
sun.shadow.mapSize.set(4096, 4096);
sun.shadow.normalBias = .025;
Object.assign(sun.shadow.camera, { left:-38, right:38, top:38, bottom:-38, near:1, far:130 });
sun.shadow.bias = -0.0003;
scene.add(sun, sun.target);

let director, chiefTemplate, soldierTemplate, chiefClips = [], selectedWeapon = 'pistol';
const weaponAssets = new Map(), cinematicHud=new CinematicHud();
let config, world, octree, avatar, heldRifle, rifle, bodyAnimation, weaponAnimation, weapon;
let importedWorld = false, importedChief = false, importedRifle = false;
let yaw = 0, pitch = 0, thirdPerson = false, flying = false, grounded = false, zoom = false, ready = false;
let hitTime = 0, kick = 0, time = 0, kills = 0, hits = 0, toastEnd = 0, spawnIndex = 0, discardMouseMotion = true;
let spawns = [], last = performance.now(), running = false;
const keys = new Set(), velocity = new THREE.Vector3();
const capsule = new Capsule(new THREE.Vector3(), new THREE.Vector3(), 0.35);
const eye = new THREE.Vector3(), forward = new THREE.Vector3(), right = new THREE.Vector3();
const raycaster = new THREE.Raycaster(), effects = [], targets = [], loaders = new GLTFLoader();
const muzzle = new THREE.PointLight(0xffb146, 0, 3);
const flash = new THREE.Mesh(new THREE.OctahedronGeometry(.05), new THREE.MeshBasicMaterial({color:0xffe7a0}));
flash.position.set(.30,-.22,-1.16); flash.visible = false; viewScene.add(flash);
muzzle.position.copy(flash.position); viewScene.add(muzzle);

function toast(message, duration = 2.5) { $('toast').textContent = message; toastEnd = time + duration; }
function isPlaying() { return !director?.active && running && document.pointerLockElement === canvas; }
function shadowMeshes(root) { root.traverse(o => { if(o.isMesh) {o.castShadow=true; o.receiveShadow=true;} }); }
function orientTriangles(root) {
  const seen=new Set(),a=new THREE.Vector3(),b=new THREE.Vector3(),c=new THREE.Vector3(),n=new THREE.Vector3();
  root.traverse(o=>{
    if(!o.isMesh || seen.has(o.geometry))return;
    const g=o.geometry;seen.add(g);
    const p=g.attributes.position,normal=g.attributes.normal,index=g.index;
    if(!index || !normal)return;
    for(let i=0;i<index.count;i+=3) {
      const ia=index.getX(i),ib=index.getX(i+1),ic=index.getX(i+2);
      a.fromBufferAttribute(p,ia);b.fromBufferAttribute(p,ib).sub(a);c.fromBufferAttribute(p,ic).sub(a);
      n.fromBufferAttribute(normal,ia);
      if(b.cross(c).dot(n)<0){index.setX(i+1,ic);index.setX(i+2,ib);}
    }
    index.needsUpdate=true;
  });
}
function normalizedAsset(asset, rotation, size, height) {
  const group = new THREE.Group();
  asset.rotation.fromArray([...rotation, 'XYZ']); group.add(asset); group.updateMatrixWorld(true);
  let bounds = new THREE.Box3().setFromObject(group), extent = bounds.getSize(new THREE.Vector3());
  const denominator = height ? extent.y : Math.max(extent.x,extent.y,extent.z);
  if(!Number.isFinite(denominator) || denominator < 0.0001) throw new Error('Model has no usable mesh bounds');
  group.scale.setScalar(size / denominator); group.updateMatrixWorld(true);
  bounds = new THREE.Box3().setFromObject(group);
  const center = bounds.getCenter(new THREE.Vector3()), offset = new THREE.Group();
  group.position.set(-center.x, height ? -bounds.min.y : -center.y, -center.z);
  offset.add(group); shadowMeshes(offset); return offset;
}
function animationDriver(gltf, spec, kind) {
  const mixer = new THREE.AnimationMixer(gltf.scene), actions = new Map();
  for(const clip of gltf.animations) actions.set(clip.name, mixer.clipAction(clip));
  let current = null;
  function action(key) {
    const requested = spec[key];
    const pattern = {idle:/idle/i,walk:/walk|run/i,fire:/fire|shoot/i,reload:/reload/i}[key];
    return actions.get(requested) || [...actions].find(([name])=>pattern.test(name))?.[1];
  }
  return {
    update(dt, moving) {
      if(kind === 'body') {
        const next=action(moving?'walk':'idle') || action('idle');
        if(next && next !== current) { current?.fadeOut(.15); next.reset().fadeIn(.15).play(); current=next; }
      }
      mixer.update(dt);
    },
    play(key) {
      const next=action(key); if(!next) return;
      mixer.stopAllAction(); next.reset().setLoop(THREE.LoopOnce,1).play();
      next.clampWhenFinished=false;
    }
  };
}
function spawnAt(index) {
  const spawn=spawns[index % spawns.length];
  const p=new THREE.Vector3(...spawn.position);
  capsule.start.copy(p).add(new THREE.Vector3(0,.35,0));
  capsule.end.copy(p).add(new THREE.Vector3(0,1.65,0));
  velocity.set(0,0,0); yaw=spawn.yaw || 0; pitch=0; grounded=false;
  sun.position.copy(p).add(new THREE.Vector3(-20,35,14));sun.target.position.copy(p);
}
function addTargets(origin) {
  if(targets.length) return;
  const offsets=importedWorld ? [[-4,0,-8],[4,0,-10],[0,0,-15]] : [[0,0,5],[8,0,-4],[-8,0,-7],[15,0,-13],[-14,0,-20]];
  for(const xyz of offsets) {
    const group=new THREE.Group();
    let p=new THREE.Vector3(...xyz);
    if(importedWorld) p.add(origin);
    raycaster.set(new THREE.Vector3(p.x,p.y+6,p.z),new THREE.Vector3(0,-1,0));
    const floor=raycaster.intersectObject(world,true).find(h=>h.face?.normal && h.point.y < p.y+3);
    if(floor) p.y=floor.point.y;
    const material=new THREE.MeshStandardMaterial({color:0xb95835,roughness:.65});
    box(group,[.64,.85,.28],[0,1.20,0],material);
    const head=new THREE.Mesh(new THREE.SphereGeometry(.2,12,10),material);head.position.set(0,1.88,0);group.add(head);
    box(group,[.12,.8,.12],[0,.4,0],new THREE.MeshStandardMaterial({color:0x454d44}));
    group.position.copy(p);
    const target={group,material,hp:100,respawn:0};
    group.traverse(o=>o.userData.target=target);
    targets.push(target); scene.add(group);
  }
}
function resize() {
  camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();
  viewCamera.aspect=camera.aspect;viewCamera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight);
}
function move(dt) {
  forward.set(-Math.sin(yaw),0,-Math.cos(yaw)); right.set(Math.cos(yaw),0,-Math.sin(yaw));
  const wish=new THREE.Vector3();
  if(keys.has('KeyW'))wish.add(forward);
  if(keys.has('KeyS'))wish.sub(forward);
  if(keys.has('KeyD'))wish.add(right);
  if(keys.has('KeyA'))wish.sub(right);
  if(flying) {
    if(keys.has('Space'))wish.y++;
    if(keys.has('ControlLeft') || keys.has('KeyC'))wish.y--;
  }
  wish.normalize();
  const speed=(keys.has('ShiftLeft')?9:6)*(zoom?.6:1);
  const blend=1-Math.exp(-14*dt);
  velocity.x=THREE.MathUtils.lerp(velocity.x,wish.x*speed,blend);
  velocity.z=THREE.MathUtils.lerp(velocity.z,wish.z*speed,blend);
  if(flying)velocity.y=wish.y*speed;
  else velocity.y-=24*dt;
  capsule.translate(velocity.clone().multiplyScalar(dt));
  grounded=false;
  if(!flying) {
    for(let i=0;i<3;i++) {
      const result=octree.capsuleIntersect(capsule);
      if(!result)break;
      grounded ||= result.normal.y>.5;
      const into=velocity.dot(result.normal);
      if(into<0)velocity.addScaledVector(result.normal,-into);
      capsule.translate(result.normal.multiplyScalar(result.depth+0.00001));
    }
  }
  if(capsule.start.y < -100) { spawnAt(spawnIndex);toast('Respawned. Press F to fly if the export has missing collision.'); }
}
function updateView(dt) {
  eye.copy(capsule.end).add(new THREE.Vector3(0,.20,0));
  camera.rotation.set(pitch,yaw,0);
  camera.position.copy(eye);
  if(thirdPerson) {
    const boom=new THREE.Vector3(.55,.2,3.6).applyEuler(camera.rotation);
    raycaster.set(eye,boom.clone().normalize());raycaster.far=boom.length();
    const obstruction=raycaster.intersectObject(world,true)[0];
    if(obstruction)boom.setLength(Math.max(.1,obstruction.distance-.2));
    camera.position.add(boom);raycaster.far=Infinity;
  }
  camera.fov=THREE.MathUtils.lerp(camera.fov,zoom?45:78,1-Math.exp(-15*dt));camera.updateProjectionMatrix();
  avatar.position.set(capsule.start.x,capsule.start.y-.35,capsule.start.z);
  avatar.rotation.y=yaw;avatar.visible=thirdPerson;
  kick=Math.max(0,kick-dt*4);
  const moving=Math.hypot(velocity.x,velocity.z)>.3;
  const bob=moving && grounded ? Math.sin(time*12)*.008 : 0;
  rifle.position.set(zoom?.08:.30,-.30+bob-kick*.025,-.64+kick*.06);
  rifle.rotation.x=kick*.11+(weapon.reloadEnd!==null?-.5:0);
  rifle.rotation.z=weapon.reloadEnd!==null?-.3:0;
  bodyAnimation?.update(dt,moving);weaponAnimation?.update(dt,moving);
  camera.updateMatrixWorld();
}
let audioContext;
function soundShot() {
  if(!audioContext)return;
  const t=audioContext.currentTime,osc=audioContext.createOscillator(),gain=audioContext.createGain();
  osc.type='triangle';osc.frequency.setValueAtTime(140,t);osc.frequency.exponentialRampToValueAtTime(42,t+.1);
  gain.gain.setValueAtTime(.14,t);gain.gain.exponentialRampToValueAtTime(.001,t+.12);
  osc.connect(gain).connect(audioContext.destination);osc.start();osc.stop(t+.12);
}
function shoot() {
  kick=1;hitTime=Math.max(0,hitTime);weaponAnimation?.play('fire');soundShot();
  flash.visible=true;muzzle.intensity=2.5;flash.userData.until=time+.04;
  raycaster.setFromCamera(new THREE.Vector2(),camera);
  const meshes=[world,...targets.filter(t=>t.hp>0).map(t=>t.group)];
  const hit=raycaster.intersectObjects(meshes,true)[0];
  const end=hit?.point || raycaster.ray.at(150,new THREE.Vector3());
  const start=thirdPerson ? eye.clone().add(new THREE.Vector3(.35,-.3,0).applyAxisAngle(new THREE.Vector3(0,1,0),yaw))
    : new THREE.Vector3(.30,-.25,-1).applyMatrix4(camera.matrixWorld);
  const trace=new THREE.Line(new THREE.BufferGeometry().setFromPoints([start,end]),new THREE.LineBasicMaterial({color:0xffeab2,transparent:true,opacity:.65}));
  scene.add(trace);effects.push({mesh:trace,end:time+.055});
  const target=hit?.object.userData.target;
  if(target && target.hp>0) {
    hits++;hitTime=.15;target.hp-=34;target.material.emissive.setHex(0x5c2510);
    if(target.hp<=0) {kills++;target.group.visible=false;target.respawn=time+2.5;}
  }
}
function render() {
  renderer.clear();renderer.render(scene,camera);
  if(director?.active) {
    const view=director.state.camera;
    if(view.pov && !view.scope && director.state.actors.find(a=>a.id===view.pov)?.alive) {
      if(selectedWeapon!=='intervention')selectWeapon('intervention');
      rifle.position.set(.28,-.24,-.68);rifle.rotation.set(0,0,0);
      renderer.clearDepth();renderer.render(viewScene,viewCamera);
    }
    cinematicHud.draw(renderer,director);
  } else if(!thirdPerson){renderer.clearDepth();renderer.render(viewScene,viewCamera);}
}
function frame(now) {
  const elapsed=Math.max(0,(now-last)/1000), dt=Math.min(elapsed,.05);last=now;
  director?.tick(elapsed);
  if(ready && isPlaying()) {
    time+=dt;
    for(let i=0;i<5;i++)move(dt/5);
    updateView(dt);
    const shots=weapon.update(dt);for(let i=0;i<shots;i++)shoot();
    for(const target of targets) {
      target.material.emissive.multiplyScalar(Math.exp(-15*dt));
      if(target.hp<=0 && time>=target.respawn){target.hp=100;target.group.visible=true;}
    }
    for(let i=effects.length-1;i>=0;i--)if(time>=effects[i].end){const e=effects.splice(i,1)[0];scene.remove(e.mesh);e.mesh.geometry.dispose();e.mesh.material.dispose();}
    if(time>flash.userData.until){flash.visible=false;muzzle.intensity=0;}
    hitTime=Math.max(0,hitTime-dt);$('hitmarker').style.opacity=hitTime>0?'1':'0';
    if(time>toastEnd)$('toast').textContent='';
  }
  if(ready) {
    $('ammo').textContent=weapon.ammo;$('reserve').textContent=' / '+weapon.reserve;
    $('weapon-state').textContent=weapon.reloadEnd!==null?'RELOADING':weapon.ammo?(WEAPONS[selectedWeapon].burst===3?'3 ROUND BURST':'SEMI AUTO'):'PRESS R TO RELOAD';
    $('kills').textContent=kills;$('hits').textContent=hits;
    $('position').textContent=(flying?'FLY · ':'')+[capsule.start.x,capsule.start.y-.35,capsule.start.z].map(v=>v.toFixed(1)).join(' / ');
    render();
  }
  requestAnimationFrame(frame);
}


function selectWeapon(kind) {
  if(!weaponAssets.has(kind))kind='pistol';
  selectedWeapon=kind;
  const asset=weaponAssets.get(kind);
  if(rifle)viewScene.remove(rifle);
  if(heldRifle)avatar.remove(heldRifle);
  rifle=cloneSkeleton(asset.model); viewScene.add(rifle);
  heldRifle=cloneSkeleton(asset.model);heldRifle.position.set(.3,1.15,-.36);avatar.add(heldRifle);
  weaponAnimation=animationDriver({scene:rifle,animations:asset.animations},asset.spec,'weapon');
  importedRifle=asset.imported;
  weapon=new BurstWeapon({...WEAPONS[kind],reserve:WEAPONS[kind].magazine*3});
  $('weapon-name').textContent=WEAPONS[kind].label.toUpperCase()+(asset.imported?' · IMPORT':' · PROXY');
  $('asset-status').textContent=(importedChief?'Chief imported':'Armor proxy')+' · '+(asset.imported?'Weapon imported':'Weapon proxy');
}
function makeActor(spec) {
  if(spec.model==='soldier' && !soldierTemplate)throw new Error('MW2 soldier asset is not imported yet');
  const root=new THREE.Group(), pivot=new THREE.Group();root.add(pivot);
  const body=cloneSkeleton(spec.model==='soldier'?soldierTemplate:chiefTemplate);
  const prop=cloneSkeleton(weaponAssets.get(spec.weapon).model);pivot.add(body,prop);
  const owned=[];
  body.traverse(o=>{if(o.isMesh && /armor/i.test(o.material.name)) {
    o.material=o.material.clone();owned.push(o.material);
    const tint=new THREE.Color(spec.color);o.material.color.setRGB(tint.r*2.6,tint.g*1.9,tint.b*4.4);
  }});
  const hand=body.getObjectByName('marker_right_hand') || body.getObjectByName('bip01_r_hand') || body.getObjectByName('tag_weapon_right');
  const mixer=new THREE.AnimationMixer(body);
  const prefix=spec.weapon==='pistol'?'':spec.weapon==='rocket'?'rocket_':'rifle_';
  const idle=chiefClips.find(c=>c.name===prefix+'idle'), walk=chiefClips.find(c=>c.name===prefix+'walk');
  const idleAction=spec.model!=='soldier' && idle?mixer.clipAction(idle).play():null;
  const walkAction=spec.model!=='soldier' && walk?mixer.clipAction(walk).play():null;
  const grip=new THREE.Vector3();
  return {root,animate(time,moving,state){
    idleAction?.setEffectiveWeight(moving && walkAction?0:1);walkAction?.setEffectiveWeight(moving?1:0);
    mixer.setTime(time);pivot.rotation.set(0,0,0);pivot.position.y=0;
    body.updateMatrixWorld(true);
    if(hand){hand.getWorldPosition(grip);pivot.worldToLocal(grip);prop.position.copy(grip).add(new THREE.Vector3(0,.01,spec.weapon==='pistol'?-.1:-.28));}
    else prop.position.set(.25,1.42,-.4);
    if(state && !state.alive) {
      const u=THREE.MathUtils.clamp((time-state.diedAt)/.6,0,1);pivot.rotation.x=-u*Math.PI/2;pivot.position.y=.25*u;
    }
  },dispose(){mixer.stopAllAction();mixer.uncacheRoot(body);owned.forEach(m=>m.dispose());}};
}

async function start() {
  const response=await fetch('config.json');if(!response.ok)throw new Error('Could not load config.json');
  config=await response.json();weapon=new BurstWeapon(config.weapon);
  if(config.sky) {
    const sky=await new THREE.CubeTextureLoader().loadAsync(config.sky);
    sky.colorSpace=THREE.SRGBColorSpace;scene.backgroundRotation.set(Math.PI/2,0,0);scene.environmentRotation.copy(scene.backgroundRotation);scene.background=sky;scene.environment=sky;scene.environmentIntensity=.35;
    scene.fog=new THREE.Fog(0xb4a787,65,240);
  }
  const statuses=[];
  $('play').textContent='Loading map…';
  if(config.world) {
    const gltf=await loaders.loadAsync(config.world);world=gltf.scene;importedWorld=true;
    statuses.push(['MAP','Imported map geometry']);
  } else {world=trainingYard();statuses.push(['MAP','Procedural training yard']);}
  orientTriangles(world);
  world.traverse(o=>{if(o.isMesh)for(const m of (Array.isArray(o.material)?o.material:[o.material])) {
    if(m.map)m.map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
  }});
  console.info('Map geometry loaded');
  if(importedWorld)for(const prop of world.getObjectByName('StaticModels')?.children || []) {
    if(Math.hypot(prop.position.x-15,prop.position.z+20)>110)prop.visible=false;
  }
  shadowMeshes(world);scene.add(world);world.updateMatrixWorld(true);
  $('play').textContent='Building map collision…';
  const collisionRoot=new THREE.Group();
  if(importedWorld) {
    // Far scenery and foliage have no useful walking collision in this bridge.
    // Keep the structural world and nearby solid props in the triangle octree.
    for(const node of [world.getObjectByName('World'),...(world.getObjectByName('StaticModels')?.children || [])].filter(Boolean)) {
      const p=node.position;
      if(node.name==='World' || (!/foliage|shrub|tree|grass/i.test(node.name) && p.x>-25 && p.x<55 && p.z>-60 && p.z<20))collisionRoot.add(node.clone(true));
    }
  }
  octree=new Octree();octree.maxLevel=8;octree.trianglesPerLeaf=24;
  octree.fromGraphNode(importedWorld?collisionRoot:world);
  console.info('Map collision ready');
  $('play').textContent='Loading Chief…';
  if(config.chief.url) {
    const gltf=await loaders.loadAsync(config.chief.url);
    avatar=normalizedAsset(gltf.scene,config.chief.rotation,config.chief.height,true);
    bodyAnimation=config.chief.animate===false?null:animationDriver(gltf,config.chief,'body');chiefClips=config.chief.animate===false?[]:gltf.animations;importedChief=true;
    statuses.push(['CHIEF','Imported model']);
  } else {avatar=armorProxy();statuses.push(['CHIEF','Procedural armor proxy']);}
  scene.add(avatar);
  chiefTemplate=cloneSkeleton(avatar);
  for(const kind of Object.keys(WEAPONS)) {
    const spec=kind==='rifle'?config.rifle:config.models?.[kind];
    let model, animations=[];
    if(spec?.url) {
      const gltf=await loaders.loadAsync(spec.url);
      if(kind==='intervention')orientTriangles(gltf.scene);
      model=normalizedAsset(gltf.scene,spec.rotation || [0,0,0],spec.length || .8,false);
      animations=gltf.animations;
    } else model=weaponProxy(kind);
    weaponAssets.set(kind,{model,animations,imported:!!spec?.url,spec:spec || {}});
  }
  if(config.soldier?.url) {
    const gltf=await loaders.loadAsync(config.soldier.url);
    orientTriangles(gltf.scene);
    soldierTemplate=normalizedAsset(gltf.scene,config.soldier.rotation || [0,0,0],1.8,true);
  }
  selectWeapon(config.selectedWeapon || 'pistol');
  statuses.push(['WEAPON',WEAPONS[selectedWeapon].label+(importedRifle?' · imported':' · proxy')]);
  if(config.spawns) {
    const response=await fetch(config.spawns);if(!response.ok)throw new Error('Could not load spawn metadata');
    spawns=await response.json();
    spawns=spawns.filter(s=>Array.isArray(s.position) && s.position.length===3 && s.position.every(Number.isFinite));
  }
  if(!spawns.length)spawns=[{position:config.spawn,yaw:config.yaw}];
  spawnAt(0);addTargets(new THREE.Vector3(...spawns[0].position));
  $('asset-list').replaceChildren(...statuses.map(([key,value])=>{
    const row=document.createElement('div');row.className='asset-row';
    const a=document.createElement('span'),b=document.createElement('span');a.textContent=key;b.textContent=value;row.append(a,b);return row;
  }));
  $('location').textContent=importedWorld?'Imported Rust map':'Training yard';
  $('mode').textContent=importedWorld?'MAP IMPORT / PROTOTYPE':'PROXY SANDBOX';
  $('asset-status').textContent=(importedChief?'Chief imported':'Armor proxy')+' · '+(importedRifle?'Rifle imported':'Rifle proxy');
  $('weapon-name').textContent=WEAPONS[selectedWeapon].label.toUpperCase()+(importedRifle?' · IMPORT':' · PROXY');
  $('summary').textContent=importedWorld?'Explore the imported map and test the burst rifle. Press V to inspect your character.':'The mechanics are playable now. Rust, Chief, and the battle rifle can be imported from local assets.';
  $('notice').textContent=importedWorld?'Movement, collision, targets, and weapon timing are prototype implementations. This is a browser asset bridge, not the IW4L game simulation.':'This is a procedural test yard, not the actual Rust map. The included character and rifle are placeholders.';
  director=new SceneDirector({scene,camera,canvas,makeActor,origin:config.sceneOrigin || (importedWorld?spawns[0].position:[0,0,0]),onMode(active){
    document.body.classList.toggle('directing',active);
    avatar.visible=false;for(const target of targets)target.group.visible=!active && target.hp>0;
    for(const effect of effects)effect.mesh.visible=!active;
    if(!active){updateView(0);$('menu').classList.remove('hidden');}
  }});
  if(config.scene) {
    const response=await fetch(config.scene);if(!response.ok)throw new Error('Could not load default scene');
    const script=await response.json();director.setEditor(script);director.load(script);
  }
  window.sceneDirector=director;
  $('director-open').disabled=false;
  ready=true;updateView(0);$('play').disabled=false;$('play').textContent='Enter prototype ↗';
  const params=new URLSearchParams(location.search);
  if(params.has('director'))director.enter();
  if(params.has('play')) {
    director.enter();director.seek(0);director.playing=true;director.status();
    $('director').classList.add('compact');
  }
}
$('play').addEventListener('click',async()=>{
  try {
    await canvas.requestPointerLock();
    const Audio=window.AudioContext || window.webkitAudioContext;
    if(Audio){audioContext ||= new Audio();await audioContext.resume();}
  } catch(error) { $('notice').textContent='Mouse capture failed. Click Enter again, or try a current desktop browser. '+error.message; }
});
document.addEventListener('pointerlockchange',()=>{
  running=document.pointerLockElement===canvas;
  discardMouseMotion=true;
  $('menu').classList.toggle('hidden',running);keys.clear();zoom=false;
  if(!running){velocity.set(0,0,0);$('play').firstChild.textContent='Resume prototype ';}
});
document.addEventListener('mousemove',event=>{
  if(!isPlaying())return;
  if(discardMouseMotion){discardMouseMotion=false;return;}
  const sensitivity=zoom?.0011:.002;
  yaw-=event.movementX*sensitivity;pitch=THREE.MathUtils.clamp(pitch-event.movementY*sensitivity,-1.45,1.45);
});
document.addEventListener('mousedown',event=>{
  if(!isPlaying())return;
  if(event.button===0){if(!weapon.trigger() && weapon.ammo===0)toast('Press R to reload');}
  if(event.button===2)zoom=true;
});
document.addEventListener('mouseup',event=>{if(event.button===2)zoom=false;});
document.addEventListener('contextmenu',event=>event.preventDefault());
document.addEventListener('keydown',event=>{
  if(!isPlaying())return;
  if(event.code==='Escape'){document.exitPointerLock();return;}
  keys.add(event.code);
  if(['Space','Tab'].includes(event.code))event.preventDefault();
  if(event.repeat)return;
  if(event.code==='Space' && grounded && !flying){velocity.y=8;grounded=false;}
  if(['Digit1','Digit2','Digit3'].includes(event.code))selectWeapon(['pistol','sniper','rocket'][Number(event.code.slice(-1))-1]);
  if(event.code==='KeyR' && weapon.reload())weaponAnimation?.play('reload');
  if(event.code==='KeyV'){thirdPerson=!thirdPerson;toast(thirdPerson?'Third person':'First person');}
  if(event.code==='KeyF'){flying=!flying;velocity.set(0,0,0);toast(flying?'Fly: Space up · C down':'Walking');}
  if(event.code==='KeyG'){spawnIndex=(spawnIndex+1)%spawns.length;spawnAt(spawnIndex);toast('Spawn '+(spawnIndex+1)+' / '+spawns.length);}
});
document.addEventListener('keyup',event=>keys.delete(event.code));
window.addEventListener('blur',()=>{keys.clear();zoom=false;document.exitPointerLock?.();});
window.addEventListener('resize',resize);
start().catch(error=>{
  console.error(error);$('play').textContent='Asset load failed';$('notice').textContent=error.message+' — Check asset paths and use uncompressed glTF 2.0 / GLB models. See README.md.';
});
requestAnimationFrame(frame);
