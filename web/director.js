import * as THREE from 'three';
import { compileScene, sampleScene, makeDemo } from './scene-script.js';

const $ = id => document.getElementById(id);
export class SceneDirector {
  constructor({ scene, camera, canvas, makeActor, onMode, origin }) {
    Object.assign(this, { scene, camera, canvas, makeActor, onMode, origin });
    this.active = false; this.playing = false; this.time = 0; this.cast = new Map(); this.traces = [];
    this.group = new THREE.Group(); this.group.visible = false; scene.add(this.group);
    this.traceMaterial = new THREE.LineBasicMaterial({ color: 0xffe1a0 });
    this.rocketMaterial = new THREE.MeshBasicMaterial({ color: 0xffa64b });
    this.rocketGeometry = new THREE.SphereGeometry(.09, 8, 6);
    this.editor = $('scene-json');
    $('director-open').onclick = () => this.enter();
    $('director-close').onclick = () => this.leave();
    $('scene-build').onclick = () => this.guard(() => {
      this.setEditor(makeDemo(Number($('red-count').value), Number($('blue-count').value), $('cast-weapon').value, this.origin));
      this.loadEditor();
    });
    $('scene-apply').onclick = () => this.guard(() => this.loadEditor());
    $('scene-play').onclick = () => this.guard(async () => {
      if (this.recorder) { this.stopRecording(); return; }
      await this.audio();
      if (this.time >= this.compiled.spec.duration) this.seek(0);
      this.playing = !this.playing; this.status();
    });
    $('scene-restart').onclick = () => this.guard(() => { this.stopRecording(); this.seek(0); this.playing = true; this.status(); });
    $('scene-scrub').oninput = e => { this.playing = false; this.seek(Number(e.target.value)); this.status(); };
    $('scene-save').onclick = () => this.guard(() => {
      const script = JSON.parse(this.editor.value); compileScene(script);
      this.download(new Blob([JSON.stringify(script, null, 2)], { type: 'application/json' }), 'scene.json');
    });
    $('scene-file').onchange = e => this.guard(async () => {
      const file = e.target.files[0]; if (!file) return;
      const script = JSON.parse(await file.text()); compileScene(script);
      this.setEditor(script); this.loadEditor(); e.target.value = '';
    });
    $('scene-record').onclick = () => this.guard(() => this.recorder ? this.stopRecording() : this.record());
    $('scene-bookmark').onclick = () => this.guard(() => {
      const script = JSON.parse(this.editor.value);
      const position = this.camera.position.toArray().map(v => +v.toFixed(3));
      const target = this.camera.getWorldDirection(new THREE.Vector3()).multiplyScalar(10).add(this.camera.position).toArray().map(v => +v.toFixed(3));
      const at = +this.time.toFixed(2), frame = { at, position, target, fov: Math.round(this.camera.fov) };
      script.camera = [...script.camera.filter(f => f.at !== at), frame].sort((a, b) => a.at - b.at);
      this.setEditor(script); this.message('Camera keyframe added. Apply JSON to use it.');
    });
    $('scene-collapse').onclick = () => $('director').classList.toggle('compact');
    document.addEventListener('visibilitychange', () => {
      if (document.hidden && this.active) { this.playing = false; this.stopRecording(); this.status(); }
    });
    this.setEditor(makeDemo(3, 3, 'pistol', origin));
    this.loadEditor();
  }
  async guard(fn) { try { await fn(); } catch (error) { this.message(error.message, true); console.error(error); } }
  message(text, error = false) { $('scene-message').textContent = text; $('scene-message').classList.toggle('error', error); }
  setEditor(script) { this.editor.value = JSON.stringify(script, null, 2); }
  loadEditor() { this.load(JSON.parse(this.editor.value)); }
  load(script) {
    const compiled = compileScene(script);
    this.stopRecording(); this.playing = false;
    for (const actor of this.cast.values()) { this.group.remove(actor.root); actor.dispose?.(); }
    this.cast.clear(); this.compiled = compiled;
    for (const actor of compiled.actors) {
      const visual = this.makeActor(actor);
      this.cast.set(actor.id, visual); this.group.add(visual.root);
    }
    $('scene-scrub').max = compiled.spec.duration;
    this.seek(0); this.status(); this.message(`${compiled.actors.length} actors · ${compiled.events.length} shots · ${compiled.spec.duration}s. Ready.`);
  }
  enter() {
    this.active = true; this.group.visible = true; this.onMode(true);
    document.exitPointerLock?.(); $('director').hidden = false;
    this.seek(this.time); this.status();
  }
  leave() {
    this.stopRecording(); this.active = false; this.playing = false; this.group.visible = false;
    $('director').hidden = true; this.onMode(false);
  }
  seek(time) {
    this.time = Math.max(0, Math.min(this.compiled.spec.duration, time));
    this.state = sampleScene(this.compiled, this.time);
    for (const actor of this.state.actors) {
      const visual = this.cast.get(actor.id);
      visual.root.position.fromArray(actor.position); visual.root.rotation.y = actor.yaw;
      visual.root.visible = actor.id !== this.state.camera.pov; visual.animate?.(this.time, actor.moving, actor);
    }
    if (this.active) {
      this.camera.position.fromArray(this.state.camera.position); this.camera.lookAt(...this.state.camera.target);
      this.camera.rotateZ(this.state.camera.roll);
      this.camera.fov = this.state.camera.fov; this.camera.updateProjectionMatrix(); this.camera.updateMatrixWorld();
    }
    this.drawShots();
    $('scene-scrub').value = this.time; $('scene-time').textContent = `${this.time.toFixed(2)} / ${this.compiled.spec.duration.toFixed(2)}s`;
  }
  drawShots() {
    for (const trace of this.traces) { this.group.remove(trace); if (trace.isLine) trace.geometry.dispose(); }
    this.traces.length = 0;
    for (const event of this.compiled.events) {
      const age = this.time - event.at, duration = event.weapon === 'rocket' ? .7 : .09;
      if (age < 0 || age > duration) continue;
      const at = sampleScene(this.compiled, event.at);
      const actor = at.actors.find(a => a.id === event.actor); if (!actor.alive) continue;
      const source = new THREE.Vector3(...actor.position).add(new THREE.Vector3(.35, 1.3, -.6).applyAxisAngle(new THREE.Vector3(0, 1, 0), actor.yaw));
      const destination = typeof event.target === 'string'
        ? new THREE.Vector3(...at.actors.find(a => a.id === event.target).position).add(new THREE.Vector3(0, 1.4, 0))
        : new THREE.Vector3(...event.target);
      let visual;
      if (event.weapon === 'rocket') {
        visual = new THREE.Mesh(this.rocketGeometry, this.rocketMaterial); visual.position.copy(source).lerp(destination, age / duration);
      } else visual = new THREE.Line(new THREE.BufferGeometry().setFromPoints([source, destination]), this.traceMaterial);
      this.group.add(visual); this.traces.push(visual);
    }
  }
  tick(dt) {
    if (!this.active || !this.playing) return;
    const before = this.time; this.seek(this.time + dt);
    for (const event of this.compiled.events) if ((event.at > before || (before === 0 && event.at === 0)) && event.at <= this.time && this.time - event.at < .15) {
      if (sampleScene(this.compiled, event.at).actors.find(a => a.id === event.actor).alive) this.shotSound(event.weapon);
    }
    if (this.time >= this.compiled.spec.duration) { this.playing = false; this.stopRecording(); this.status(); }
  }
  status() {
    $('scene-play').textContent = this.playing ? 'Pause' : 'Play';
    $('scene-record').textContent = this.recorder ? 'Stop & save' : 'Record from start';
    for (const id of ['scene-scrub', 'scene-build', 'scene-apply', 'scene-file', 'scene-restart']) $(id).disabled = !!this.recorder;
    $('scene-play').disabled = !!this.recorder;
  }
  async audio() {
    if (!this.audioContext) {
      this.audioContext = new AudioContext(); this.audioOut = this.audioContext.createMediaStreamDestination();
    }
    await this.audioContext.resume();
  }
  shotSound(weapon) {
    if (!this.audioContext) return;
    const ctx = this.audioContext, start = ctx.currentTime, osc = ctx.createOscillator(), gain = ctx.createGain();
    osc.type = 'triangle'; osc.frequency.setValueAtTime(weapon === 'rocket' ? 70 : weapon === 'sniper' ? 220 : 160, start);
    osc.frequency.exponentialRampToValueAtTime(30, start + .16);
    gain.gain.setValueAtTime(.04, start); gain.gain.exponentialRampToValueAtTime(.001, start + .18);
    osc.connect(gain); gain.connect(ctx.destination); gain.connect(this.audioOut); osc.start(); osc.stop(start + .2);
  }
  async record() {
    if (!this.canvas.captureStream || !window.MediaRecorder) throw new Error('Video recording needs a browser with canvas capture and MediaRecorder. Try Chrome.');
    await this.audio(); this.loadEditor(); this.enter(); this.seek(0);
    const stream = this.canvas.captureStream(30);
    stream.addTrack(this.audioOut.stream.getAudioTracks()[0].clone());
    const mimeType = ['video/webm;codecs=vp9,opus', 'video/webm;codecs=vp8,opus', 'video/mp4', 'video/webm'].find(t => MediaRecorder.isTypeSupported(t));
    if (!mimeType) { stream.getTracks().forEach(t => t.stop()); throw new Error('This browser has no supported recording format'); }
    const chunks = []; let recorder;
    try { recorder = new MediaRecorder(stream, { mimeType, videoBitsPerSecond: 10000000 }); }
    catch (error) { stream.getTracks().forEach(t => t.stop()); throw error; }
    const filename = `${(this.compiled.spec.name || 'scene').replace(/[^a-z0-9_-]/gi, '-').slice(0, 60)}.${mimeType.includes('mp4') ? 'mp4' : 'webm'}`;
    recorder.ondataavailable = e => { if (e.data.size) chunks.push(e.data); };
    recorder.onstop = () => {
      stream.getTracks().forEach(t => t.stop());
      if (chunks.length) { this.download(new Blob(chunks, { type: mimeType }), filename); this.message('Video saved. Record again with another camera path for a matching take.'); }
    };
    recorder.onerror = e => { this.message(`Recording failed: ${e.error?.message || 'encoder error'}`, true); this.stopRecording(); };
    try { recorder.start(250); } catch (error) { stream.getTracks().forEach(t => t.stop()); throw error; }
    this.recorder = recorder; this.playing = true; this.status();
    this.message('Recording 30 fps with generated shot audio. Keep this tab visible.');
  }
  stopRecording() {
    if (this.recorder) { if (this.recorder.state !== 'inactive') this.recorder.stop(); this.recorder = null; this.playing = false; this.status(); }
  }
  download(blob, name) {
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name; a.click();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  }
}
