import * as THREE from 'three';

const mat = (color, roughness = 0.85, metalness = 0.1) => new THREE.MeshStandardMaterial({ color, roughness, metalness });
export function box(group, size, at, material) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(...size), material);
  mesh.position.set(...at); mesh.castShadow = true; mesh.receiveShadow = true; group.add(mesh); return mesh;
}

export function trainingYard() {
  const root = new THREE.Group();
  const sand = mat(0xb7a17b), rust = mat(0x8b6348), steel = mat(0x515a51), pale = mat(0xc3bdaa), dark = mat(0x343b36);
  box(root, [58, 1, 58], [0, -0.5, 0], sand);
  for (const [x, z, w, d] of [[0,-28,58,1],[0,28,58,1],[-28,0,1,58],[28,0,1,58]]) box(root,[w,3.6,d],[x,1.8,z],pale);
  for (const x of [-3, 3]) for (const z of [-6, 0]) box(root,[.32,12,.32],[x,6,z],rust);
  for (const y of [3.2,6.4,9.6]) {
    box(root,[7,.22,7],[0,y,-3],steel);
    for (const x of [-3.4,3.4]) box(root,[.1,.9,7],[x,y+.55,-3],rust);
    box(root,[7,.9,.12],[0,y+.55,-6.4],rust);
  }
  const tank=new THREE.Mesh(new THREE.CylinderGeometry(1.8,1.8,4,16),pale); tank.position.set(0,11,-3);tank.castShadow=true;root.add(tank);
  for (const z of [-16,12]) {
    box(root,[3.4,3.2,9],[-15,1.6,z],steel);
    for(let i=0;i<14;i++)box(root,[.1,3.3,.14],[-13.25,1.65,z-4.2+i*.63],dark);
  }
  for(let i=0;i<8;i++)box(root,[3,.35,1],[5,0.175+i*.35,-2-i],rust);
  for (const [x,z] of [[11,-10],[-7,-13],[12,6],[-5,17],[19,-18],[-20,-4]]) {
    box(root,[2,1.5,2],[x,.75,z],rust);
    box(root,[2.1,.12,2.1],[x,1.52,z],pale);
    for(const dy of [.2,1.25])box(root,[2.12,.1,2.12],[x,dy,z],steel);
  }
  for(let i=0;i<4;i++) {
    const pipe=new THREE.Mesh(new THREE.CylinderGeometry(.45,.45,16,12),rust);
    pipe.rotation.z=Math.PI/2;pipe.position.set(10,.55+i*.85,-21);pipe.castShadow=true;root.add(pipe);
  }
  root.name='Procedural training yard';
  return root;
}

export function armorProxy() {
  const g=new THREE.Group();
  const armor=mat(0x52683c,.55,.35), joints=mat(0x242d27), visor=mat(0xe8b34f,.2,.7);
  box(g,[.64,.68,.34],[0,1.36,0],armor);
  box(g,[.44,.27,.3],[0,.9,0],joints);
  box(g,[.39,.38,.38],[0,1.91,0],armor);
  box(g,[.34,.15,.08],[0,1.93,-.21],visor);
  for(const s of [-1,1]) {
    box(g,[.25,.44,.32],[s*.47,1.42,0],armor);
    box(g,[.18,.43,.21],[s*.47,1.02,-.10],armor);
    box(g,[.24,.43,.28],[s*.18,.62,0],armor);
    box(g,[.23,.44,.25],[s*.18,.2,0],armor);
    box(g,[.25,.16,.4],[s*.18,.04,-.06],joints);
  }
  return g;
}

export function rifleProxy() {
  const g=new THREE.Group(), dark=mat(0x252d2b,.45,.6), grey=mat(0x5d696b,.38,.7), olive=mat(0x6f7954,.55,.35);
  box(g,[.12,.17,.62],[0,0,0],grey);
  box(g,[.15,.22,.23],[0,-.005,.28],olive);
  box(g,[.09,.19,.10],[0,-.17,.14],dark);
  box(g,[.095,.23,.12],[0,-.15,.29],grey);
  box(g,[.08,.07,.28],[0,.055,-.42],dark);
  box(g,[.07,.10,.28],[0,.19,-.05],dark);
  box(g,[.07,.17,.05],[0,.14,.10],grey);
  box(g,[.06,.17,.05],[0,.14,-.2],grey);
  const scope=new THREE.Mesh(new THREE.CylinderGeometry(.045,.045,.24,12),grey);scope.rotation.x=Math.PI/2;scope.position.set(0,.28,-.03);g.add(scope);
  const lens=new THREE.Mesh(new THREE.CircleGeometry(.035,12),mat(0x97dad4,.1,.6));lens.position.set(0,.28,.093);g.add(lens);
  return g;
}

export function weaponProxy(kind = 'pistol') {
  if (kind === 'rifle') return rifleProxy();
  const g = new THREE.Group(), steel = mat(0x737e7c, .4, .55), dark = mat(0x242d29), olive = mat(0x596342);
  if (kind === 'pistol') {
    box(g, [.13, .15, .38], [0, 0, -.04], steel);
    box(g, [.11, .22, .13], [0, -.15, .08], dark);
    box(g, [.06, .05, .12], [0, .11, -.08], dark);
  } else if (kind === 'sniper') {
    box(g, [.13, .18, .64], [0, 0, 0], steel);
    box(g, [.06, .07, .8], [0, .02, -.65], dark);
    box(g, [.15, .23, .28], [0, -.03, .42], olive);
    box(g, [.08, .13, .34], [0, .18, -.02], dark);
    box(g, [.1, .23, .14], [0, -.18, .16], dark);
  } else {
    for (const x of [-.12, .12]) {
      const tube = new THREE.Mesh(new THREE.CylinderGeometry(.14, .14, 1.15, 16), olive);
      tube.rotation.x = Math.PI / 2; tube.position.x = x; g.add(tube);
    }
    box(g, [.14, .23, .13], [0, -.22, .2], dark);
    box(g, [.09, .13, .18], [0, .2, -.02], steel);
  }
  return g;
}
