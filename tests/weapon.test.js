import test from 'node:test';
import assert from 'node:assert/strict';
import { BurstWeapon } from '../web/weapon.js';

test('one click completes exactly three shots without another trigger',()=>{
  const w=new BurstWeapon();assert.equal(w.trigger(),true);
  assert.equal(w.update(0),1);assert.equal(w.update(.074),0);
  assert.equal(w.update(.001),1);assert.equal(w.update(.075),1);
  assert.equal(w.update(10),0);assert.equal(w.ammo,33);
});
test('frame stalls do not drop queued shots or add shots',()=>{
  const w=new BurstWeapon();w.trigger();assert.equal(w.update(.2),3);
  assert.equal(w.update(1),0);assert.equal(w.totalShots,3);
});
test('click spam cannot bypass burst or cooldown',()=>{
  const w=new BurstWeapon();w.trigger();
  for(let i=0;i<20;i++)assert.equal(w.trigger(),false);
  w.update(.3);assert.equal(w.trigger(),false);
  w.update(.15);assert.equal(w.trigger(),true);
});
test('last magazine rounds do not underflow',()=>{
  const w=new BurstWeapon();w.ammo=2;w.trigger();
  assert.equal(w.update(1),2);assert.equal(w.ammo,0);assert.equal(w.trigger(),false);
});
test('reload waits for burst and conserves remaining ammunition',()=>{
  const w=new BurstWeapon();w.trigger();assert.equal(w.reload(),false);w.update(.2);
  assert.equal(w.reload(),true);assert.equal(w.trigger(),false);
  w.update(2.19);assert.equal(w.ammo,33);w.update(.02);
  assert.equal(w.ammo,36);assert.equal(w.reserve,105);
  w.ammo=0;w.reserve=2;w.reload();w.update(3);
  assert.equal(w.ammo,2);assert.equal(w.reserve,0);
});
