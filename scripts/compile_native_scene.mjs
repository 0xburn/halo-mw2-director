import fs from 'node:fs';
import {compileScene,sampleScene} from '../web/scene-script.js';
const root=new URL('../',import.meta.url);
const scene=compileScene(JSON.parse(fs.readFileSync(new URL('web/scenes/worlds-collide.json',root))));
const xyz=([x,y,z])=>[x/.0254,-z/.0254,y/.0254];
const initial=sampleScene(scene,0);const ids=new Map(initial.actors.map((a,i)=>[a.id,i]));
function placement(a){const p=xyz(a.position);return `${p.join(' ')} ${(-a.yaw*180/Math.PI-90).toFixed(3)} 0`;}
let setup=[];
for(const [id,a] of initial.actors.entries()){
 if(id)setup.push(`bot give ${id} ${id>=8?'wa2000_mp':'cheytac_mp'} &`,`bot tp ${id} ${placement(a)} &`);
 else setup.push(`tp ${placement(a)} &`);
}
let events=[{at:1.7,command:'hold +speed_throw'},{at:2.2,command:'press +attack'},{at:2.6,command:'release +speed_throw'},
 {at:4,command:'look 0 0'},{at:5.4,command:'bot fire 12'},{at:5.43,command:'kill'},
 {at:7.5,command:`bot tp 12 ${placement(sampleScene(scene,7.6).actors[12])} &`}];
for(const e of scene.events){if(e.at>=7.5)events.push({at:e.at,command:`bot fire ${ids.get(e.actor)}`});}
for(const at of [12.5,17.5,22.5])for(let i=1;i<16;i++)events.push({at,command:`bot give ${i} ${i>=8?'wa2000_mp':'cheytac_mp'} &`});
if(process.argv.includes('--verify')) {
 for(const at of [1,3,10,14,23])events.push({at,command:`screenshot native-fixed-${at}`});
}
const camera=[],motion=[];
for(let f=0;f<=scene.spec.duration*60;f++){
 const s=sampleScene(scene,f/60);
 camera.push([...xyz(s.camera.position),...xyz(s.camera.target),s.camera.fov,s.camera.roll]);
 if(f%6===0)motion.push(s.actors.map(a=>xyz(a.position)));
}
const out={version:1,duration:scene.spec.duration,setup:setup.join('; '),events:events.sort((a,b)=>a.at-b.at),camera,motion};
fs.mkdirSync(new URL('local-assets/scenes/',root),{recursive:true});
fs.writeFileSync(new URL('local-assets/scenes/worlds-collide-native.json',root),JSON.stringify(out));
console.log(`Native take compiled: ${initial.actors.length} actors, ${camera.length} camera samples, ${events.length} cues.`);
