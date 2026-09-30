import * as THREE from 'three';

// Draw into the WebGL output so scope/death cues are included in recordings.
export class CinematicHud {
  constructor() {
    this.canvas=document.createElement('canvas');this.canvas.width=1280;this.canvas.height=720;
    this.ctx=this.canvas.getContext('2d');this.texture=new THREE.CanvasTexture(this.canvas);
    this.scene=new THREE.Scene();this.camera=new THREE.OrthographicCamera(-1,1,1,-1,0,1);
    const material=new THREE.MeshBasicMaterial({map:this.texture,transparent:true,depthTest:false,depthWrite:false,toneMapped:false});
    this.scene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2),material));
  }
  draw(renderer,director) {
    const state=director.state, c=this.ctx,w=1280,h=720,view=state.camera;
    c.clearRect(0,0,w,h);
    if(view.pov) {
      c.strokeStyle='rgba(255,255,255,.8)';c.lineWidth=1;
      if(view.scope) {
        c.fillStyle='#050505';c.beginPath();c.rect(0,0,w,h);c.arc(w/2,h/2,h*.475,0,Math.PI*2,true);c.fill('evenodd');
        c.strokeStyle='rgba(0,0,0,.85)';c.lineWidth=1.5;c.beginPath();c.moveTo(w/2,20);c.lineTo(w/2,h-20);c.moveTo(w/2-h*.475,h/2);c.lineTo(w/2+h*.475,h/2);c.stroke();
        for(let i=-4;i<=4;i++)if(i){c.fillStyle='#000';c.beginPath();c.arc(w/2+i*28,h/2,2,0,Math.PI*2);c.fill();}
      } else {
        c.beginPath();for(const [x,y,xx,yy] of [[-13,0,-5,0],[5,0,13,0],[0,-13,0,-5],[0,5,0,13]]){c.moveTo(w/2+x,h/2+y);c.lineTo(w/2+xx,h/2+yy);}c.stroke();
      }
      c.fillStyle='#eee';c.font='600 19px sans-serif';c.textAlign='right';c.fillText('INTERVENTION',1210,653);c.font='28px monospace';c.fillText('5 | 15',1210,684);
      c.textAlign='left';c.font='600 16px sans-serif';c.fillText('RUST',65,62);c.font='14px monospace';c.fillStyle='#cad2ab';c.fillText('FREE-FOR-ALL',65,84);
      const actor=state.actors.find(a=>a.id===view.pov);
      if(actor && !actor.alive){
        const age=state.time-actor.diedAt;c.fillStyle=`rgba(135,8,3,${Math.max(.12,.55-age*.35)})`;c.fillRect(0,0,w,h);
        c.fillStyle='#fff';c.textAlign='center';c.font='600 23px sans-serif';c.fillText('KILLED BY MASTER CHIEF',w/2,580);
      }
    }
    if(view.caption){c.fillStyle='rgba(0,0,0,.5)';c.fillRect(0,h-66,w,66);c.fillStyle='#eee';c.textAlign='center';c.font='600 20px sans-serif';c.fillText(view.caption,w/2,h-27);}
    this.texture.needsUpdate=true;renderer.clearDepth();renderer.render(this.scene,this.camera);
  }
}
