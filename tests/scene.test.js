import test from 'node:test';
import assert from 'node:assert/strict';
import { compileScene, sampleScene, makeDemo } from '../web/scene-script.js';

test('team counts expand to stable IDs and preserve spacing during group moves', () => {
  const scene = compileScene(makeDemo(8, 5));
  assert.equal(scene.actors.length, 13);
  const state = sampleScene(scene, 2.5);
  assert.deepEqual(state.actors[0].position, [-5, 0, 8]);
  assert.deepEqual(state.actors[1].position, [-5, 0, 10.2]);
  assert.equal(state.actors.at(-1).id, 'blue-5');
});
test('seeking backwards reconstructs death, respawn and jump without accumulated state', () => {
  const scene = compileScene(makeDemo());
  const actor = t => sampleScene(scene, t).actors.find(a => a.id === 'blue-1');
  const before = sampleScene(scene, 4.2);
  assert.equal(actor(9).alive, false);
  assert.equal(actor(12).alive, true);
  assert.deepEqual(actor(12).position, [6, 0, 8]);
  assert.ok(Math.abs(sampleScene(scene, 10.6).actors[0].position[1] - 2) < 1e-8);
  assert.deepEqual(sampleScene(scene, 4.2), before);
});
test('camera edits do not alter actor choreography or shot times', () => {
  const script = makeDemo(), original = compileScene(script);
  script.camera = [{ at: 0, position: [30, 12, 0], target: 'red-1' }];
  const retake = compileScene(script);
  for (const t of [0, 2.5, 4, 8.6, 12, 16]) assert.deepEqual(sampleScene(original, t).actors, sampleScene(retake, t).actors);
  assert.deepEqual(original.events, retake.events);
  assert.deepEqual(sampleScene(retake, 2.5).camera.target, [-5, 1.4, 8]);
});
test('camera cut holds previous shot, then switches exactly at keyframe', () => {
  const scene = compileScene(makeDemo());
  assert.deepEqual(sampleScene(scene, 7.999).camera.position, [-9, 3, 16]);
  assert.deepEqual(sampleScene(scene, 8).camera.position, [9, 2.4, 14]);
});
test('zero-sized teams and all CE weapons work; invalid scenes fail before replacement', () => {
  for (const weapon of ['pistol', 'sniper', 'rocket']) assert.equal(compileScene(makeDemo(0, 2, weapon)).actors.length, 2);
  for (const change of [
    s => { s.teams[0].count = 65; }, s => { s.teams[1].id = 'red'; },
    s => { s.teams[0].weapon = 'unknown'; }, s => { s.actions[0].actor = 'missing'; },
    s => { s.actions[1].target = 'red-100'; }, s => { s.actions[0].duration = 999; },
    s => { s.camera[1].at = 0; }, s => { s.camera[0].fov = 0; },
    s => { s.actions.push({ at: 2, actor: 'red', type: 'move', by: [1,0,0], duration: 1 }); }
  ]) { const script = makeDemo(); change(script); assert.throws(() => compileScene(script)); }
});
test('scene sampler clamps to timeline and does not mutate input', () => {
  const script = makeDemo(), saved = structuredClone(script), scene = compileScene(script);
  sampleScene(scene, 6); assert.deepEqual(script, saved);
  assert.equal(sampleScene(scene, -1).time, 0); assert.equal(sampleScene(scene, 99).time, 16);
});
